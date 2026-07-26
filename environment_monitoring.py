from datetime import datetime
import time
import requests

# Astropy imports
from astropy import units as u
from astropy.coordinates import (
    AltAz,
    EarthLocation,
    Galactic,
    SkyCoord,
    get_body,
    get_sun,
)
from astropy.time import Time
import json


class AirspaceRecorder:
    def __init__(self, latitude, longitude, n2yo_api_key=None, bounding_delta=0.2):
        """Initializes the recorder with a target location and optional API key."""
        self.lat = latitude
        self.lon = longitude
        self.n2yo_api_key = n2yo_api_key

        self.bounding_box = {
            "lamin": latitude - bounding_delta,
            "lamax": latitude + bounding_delta,
            "lomin": longitude - bounding_delta,
            "lomax": longitude + bounding_delta,
        }

        self.earth_location = EarthLocation(
            lat=latitude * u.deg, lon=longitude * u.deg, height=0 * u.m
        )

        self.data_store = {
            "weather": [],
            "flights": [],
            "satellites": [],
            "celestial": [],
        }

    def fetch_flights(self):
        """Queries OpenSky API for aircraft state vectors."""
        url = "https://opensky-network.org/api/states/all"
        try:
            response = requests.get(url, params=self.bounding_box, timeout=10)
            if response.status_code == 200:
                return response.json().get("states", [])
        except Exception as e:
            print(f"Flight API error: {e}")
        return None

    def fetch_weather(self):
        """Queries Open-Meteo API for current weather conditions."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "current": "temperature_2m,wind_speed_10m,wind_direction_10m,weather_code",
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get("current", {})
        except Exception as e:
            print(f"Weather API error: {e}")
        return None

    def fetch_satellites(self):
        """Queries N2YO API for overhead satellites (requires API key)."""
        if not self.n2yo_api_key:
            return None

        search_radius = 89  # 60 #45 # search close to horizon
        category_id = 0
        url = (
            f"https://api.n2yo.com/rest/v1/satellite/above/"
            f"{self.lat}/{self.lon}/0/{search_radius}/{category_id}"
            f"&apiKey={self.n2yo_api_key}"
        )
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get("above", [])
        except Exception as e:
            print(f"Satellite API error: {e}")
        return None

    def fetch_celestial_bodies(self, current_time):
        """Calculates Altitude and Azimuth for Sun, Moon, and Galactic Centre."""
        obs_time = Time(current_time)
        altaz_frame = AltAz(obstime=obs_time, location=self.earth_location)

        sun_coord = get_sun(obs_time).transform_to(altaz_frame)
        moon_coord = get_body("moon", obs_time).transform_to(altaz_frame)
        galactic_centre = SkyCoord(
            l=0.0 * u.deg, b=0.0 * u.deg, frame="galactic"
        ).transform_to(altaz_frame)

        return [
            {
                "name": "Sun",
                "azimuth_deg": sun_coord.az.deg,
                "elevation_deg": sun_coord.alt.deg,
            },
            {
                "name": "Moon",
                "azimuth_deg": moon_coord.az.deg,
                "elevation_deg": moon_coord.alt.deg,
            },
            {
                "name": "Galactic Centre",
                "azimuth_deg": galactic_centre.az.deg,
                "elevation_deg": galactic_centre.alt.deg,
            },
        ]

    def calculate_flight_azel(self, flight_record, current_time):
        """Converts a flight record's lat/lon/altitude into local Azimuth and Elevation."""
        try:
            f_lat = flight_record["latitude"]
            f_lon = flight_record["longitude"]
            f_alt = flight_record["altitude_m"]

            if f_lat is None or f_lon is None or f_alt is None:
                return None, None

            aircraft_location = EarthLocation(
                lat=f_lat * u.deg, lon=f_lon * u.deg, height=f_alt * u.m
            )
            obs_time = Time(current_time)
            altaz_frame = AltAz(obstime=obs_time, location=self.earth_location)

            coord = aircraft_location.get_itrs(obstime=obs_time).transform_to(
                altaz_frame
            )
            return coord.az.deg, coord.alt.deg
        except Exception:
            raise
            return None, None

    def calculate_satellite_azel(self, sat_record, current_time):
        """Converts a satellite record's lat/lon/altitude into local Azimuth and Elevation."""
        try:
            f_lat = sat_record["latitude"]
            f_lon = sat_record["longitude"]
            f_alt = sat_record["altitude_km"] * 1e3  # convert to metres

            if f_lat is None or f_lon is None or f_alt is None:
                return None, None

            sat_location = EarthLocation(
                lat=f_lat * u.deg, lon=f_lon * u.deg, height=f_alt * u.m
            )
            obs_time = Time(current_time)
            altaz_frame = AltAz(obstime=obs_time, location=self.earth_location)

            coord = sat_location.get_itrs(obstime=obs_time).transform_to(altaz_frame)
            return coord.az.deg, coord.alt.deg
        except Exception:
            raise
            return None, None

    def poll_once(self):
        """Executes a single data collection cycle and appends to dictionaries."""
        timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Celestial Bodies
        celestial_results = self.fetch_celestial_bodies(timestamp_str)
        for body in celestial_results:
            self.data_store["celestial"].append(
                {
                    "timestamp": timestamp_str,
                    "body_name": body["name"],
                    "azimuth_deg": body["azimuth_deg"],
                    "elevation_deg": body["elevation_deg"],
                }
            )

        # 2. Weather
        weather = self.fetch_weather()
        if weather:
            self.data_store["weather"].append(
                {
                    "timestamp": timestamp_str,
                    "temperature_c": weather.get("temperature_2m"),
                    "wind_speed_kmh": weather.get("wind_speed_10m"),
                    "wind_direction_deg": weather.get("wind_direction_10m"),
                    "weather_code": weather.get("weather_code"),
                }
            )

        # 3. Flights (with Az/El calculation)
        states = self.fetch_flights()
        if states:
            flight_count = 0
            for s in states:
                flight_record = {
                    "timestamp": timestamp_str,
                    "icao24": s[0],
                    "callsign": s[1].strip() if s[1] else "N/A",
                    "origin_country": s[2],
                    "longitude": s[5],
                    "latitude": s[6],
                    "altitude_m": s[7],
                    "velocity_ms": s[9],
                    "heading": s[10],
                }

                # Calculate local Az/El for this flight
                az, el = self.calculate_flight_azel(flight_record, timestamp_str)
                flight_record["azimuth_deg"] = az
                flight_record["elevation_deg"] = el

                self.data_store["flights"].append(flight_record)
                flight_count += 1
            print(
                f"[{timestamp_str}] Logged {flight_count} flights (with Az/El"
                " computed)."
            )
        else:
            print(f"[{timestamp_str}] No flights recorded.")

        # 4. Satellites
        satellites = self.fetch_satellites()

        if satellites:
            sat_count = 0
            for sat in satellites:
                sat_record = {
                    "timestamp": timestamp_str,
                    "norad_id": sat.get("satid"),
                    "satellite_name": sat.get("satname"),
                    "latitude": sat.get("satlat"),
                    "longitude": sat.get("satlng"),
                    "altitude_km": sat.get("satalt"),
                }

                # Calculate local Az/El for this satellite
                az, el = self.calculate_satellite_azel(sat_record, timestamp_str)
                sat_record["azimuth_deg"] = az  # sat.get("azimuth"),
                sat_record["elevation_deg"] = el  # sat.get("elevation"),

                self.data_store["satellites"].append(sat_record)
                sat_count += 1
            print(f"[{timestamp_str}] Logged {sat_count} satellites.")

    def run(self, interval_seconds=60, max_iter=None, verbose=False):
        """Starts the continuous polling loop."""
        print(
            f"Starting AirspaceRecorder for ({self.lat}, {self.lon}). Press"
            " Ctrl+C to stop."
        )
        try:
            i = 0
            while True:
                self.poll_once()
                i += 1
                if verbose:
                    print(json.dumps(self.data_store, indent=4))
                print("-" * 40)

                # Test if maximum no. of iterations has been reached
                if max_iter is not None:
                    if i >= max_iter:
                        break

                # Wait for next iteration
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print(
                "\nRecorder stopped by user. Data is available in `recorder.data_store`."
            )


if __name__ == "__main__":
    with open("n2yo_api_key.apikey", "r") as f:
        n2yo_api_key = f.readline()[:-1]  # trim trailing newline

    # Run for a single iteration
    asrec = AirspaceRecorder(
        latitude=53.234551,
        longitude=-2.3047266,
        bounding_delta=0.3,
        n2yo_api_key=n2yo_api_key,
    )
    asrec.run(max_iter=1, verbose=False)
    print("Ready to plot")

    import pylab as plt

    plt.subplot(111)

    # Satellite
    for record in asrec.data_store["satellites"]:
        try:
            plt.plot(record["azimuth_deg"], record["elevation_deg"], "r.", alpha=0.2)
        except:
            pass

    # Aircraft
    for record in asrec.data_store["flights"]:
        try:
            plt.plot(record["azimuth_deg"], record["elevation_deg"], "vx", ms=20)
        except:
            pass

    # Celestial
    for record in asrec.data_store["celestial"]:
        try:
            plt.plot(
                record["azimuth_deg"], record["elevation_deg"], "go", alpha=0.3, ms=20
            )
        except:
            pass

    plt.show()
