from datetime import datetime, timezone
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


class SituationAwarenessRecorder:
    def __init__(self, latitude, longitude, n2yo_api_key=None, 
                 flight_bounding_delta=0.2, sat_search_radius=30):
        """
        Use public web APIs to monitor the local environment, including 
        reported weather, flights, satellites, and ionosphere.
        
        Parameters:
            latitude (float):
                Latitude of the site, in decimal degrees.
            longitude (float):
                Latitude of the site, in decimal degrees.
            n2yo_api_key (str):
                API key generated for a registered user on the `n2yo` service. 
            flight_bounding_delta (float):
                Width of the (square) bounding box around the site, in decimal degrees. Used to define the  sat_search_radius=30
        """
        self.lat = latitude
        self.lon = longitude
        self.n2yo_api_key = n2yo_api_key
        self.sat_search_radius = sat_search_radius

        self.flight_bounding_box = {
            "lamin": latitude - flight_bounding_delta,
            "lamax": latitude + flight_bounding_delta,
            "lomin": longitude - flight_bounding_delta,
            "lomax": longitude + flight_bounding_delta,
        }
        
        # Set current location
        self.earth_location = EarthLocation(
            lat=latitude * u.deg, lon=longitude * u.deg, height=0 * u.m
        )
        
        # Initialise data stores
        # List of dict objects with rich data
        self.data_store = {
            "weather":      [],
            "flights":      [],
            "satellites":   [],
            "celestial":    [],
            "ionosphere":   []
        }
        
        # Create empty journal for tabular data
        self.reset_journal()
        
    
    def reset_journal(self):
        """
        Create empty journal for tabular data.
        """
        # Empty table with object az/el, name, and timestamp
        self.journal = {
            'object':    [],
            'az':        [],
            'el':        [],
            'timestamp': [],
        }
    
    def fetch_flights(self):
        """
        Query the OpenSky API for aircraft state vectors.
        """
        url = "https://opensky-network.org/api/states/all"
        try:
            response = requests.get(url, 
                                    params=self.flight_bounding_box, 
                                    timeout=10)
            if response.status_code == 200:
                return response.json().get("states", [])
        except Exception as e:
            print(f"Flight API error: {e}")
        return None

    def fetch_weather(self):
        """
        Query the Open-Meteo API for current weather conditions.
        """
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
        """
        Query the N2YO API for overhead satellites (requires API key).
        """
        if not self.n2yo_api_key:
            return None

        search_radius = self.sat_search_radius # 60 #45 # search close to horizon
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
        """
        Calculate the altitude and azimuth for the Sun, Moon, and Galactic 
        Centre.
        """
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
    
    def fetch_ionosphere(self):
        """
        Fetches near-real-time Total Electron Content (TEC) data 
        for the recorder's coordinates. 
        """
        # NOAA SWPC provides global GPS-TEC ASCII/JSON text feeds and maps.
        # Alternatively, you can query regional services (like ESA's SWE network).
        # Example endpoint structure pointing to current solar-geophysical data:
        #url = "https://services.swpc.noaa.gov/json/geospace/geospace_tec_latest.json"
        url = "https://services.swpc.noaa.gov/json/geospace/geospace_dst_1_hour.json"
        
        try:
          response = requests.get(url, timeout=10)
          if response.status_code == 200:
            data = response.json()
            
            # If querying a gridded product, find the grid point closest to 
            # self.lat, self.lon (this block parses typical JSON grid 
            # structures mapping lat/lon to TECU)
            for entry in data:
              if "lat" in entry and "lon" in entry:
                # Match closest coordinate cell (assuming 1-degree or 5-degree 
                # resolution grids)
                if abs(entry["lat"] - self.lat) < 1.0 \
                    and abs(entry["lon"] - self.lon) < 1.0:
                  return {
                      "tec_units": entry.get("tec", entry.get("value")),
                      "quality": entry.get("quality", "N/A")
                  }
                  
            # Fallback if specific point match isn't structured in a flat list:
            return {"tec_units": "Grid point out of direct JSON range, check IONEX stream"}
            
        except Exception as e:
          print(f"Ionosphere API error: {e}")
          
        return None
    
    
    def calculate_azel(self, object_lat, object_lon, object_alt_m, current_time):
        """
        Convert a flight or sateliite record's lat/lon/altitude into local 
        Azimuth and Elevation.
        """
        try:
            f_lat = object_lat
            f_lon = object_lon
            f_alt = object_alt_m

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
    
    def store_journal_record(self, objname, az, el, timestamp):
        """
        Store one row in the journal of object locations.
        """
        self.journal['az'].append(az)
        self.journal['el'].append(el)
        self.journal['object'].append(objname)
        self.journal['timestamp'].append(timestamp)
        
    def poll_once(self):
        """
        Executes a single data collection cycle and appends to dictionaries.
        """
        # Get current time as string and integer
        current_time = datetime.now(timezone.utc)
        timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")    
        timestamp_int = current_time.strftime("%Y%m%d%H%M%S")

        # (1) Celestial Bodies
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
            self.store_journal_record(objname=body["name"], 
                                      timestamp=timestamp_int,
                                      az=body["azimuth_deg"], 
                                      el=body["elevation_deg"] 
                                      )

        # (2) Weather
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

        # (3) Flights (with Az/El calculation)
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
                az, el = self.calculate_azel(
                                object_lat=flight_record['latitude'], 
                                object_lon=flight_record['longitude'], 
                                object_alt_m=flight_record['altitude_m'], 
                                current_time=timestamp_str
                            )
                flight_record["azimuth_deg"] = az
                flight_record["elevation_deg"] = el
                
                # Store in structured dict and journal
                self.data_store["flights"].append(flight_record)
                self.store_journal_record(objname=flight_record['callsign'], 
                                          timestamp=timestamp_int,
                                          az=az, 
                                          el=el 
                                          )
                
                flight_count += 1
            print(
                f"[{timestamp_str}] Logged {flight_count} flights (with Az/El"
                " computed)."
            )
        else:
            print(f"[{timestamp_str}] No flights recorded.")

        # (4) Satellites
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
                az, el = self.calculate_azel(
                                object_lat=sat_record['latitude'], 
                                object_lon=sat_record['longitude'], 
                                object_alt_m=sat_record['altitude_km'] * 1e3, 
                                current_time=timestamp_str
                            )
                sat_record["azimuth_deg"] = az
                sat_record["elevation_deg"] = el

                self.data_store["satellites"].append(sat_record)
                self.store_journal_record(objname=sat_record['satellite_name'], 
                                          timestamp=timestamp_int,
                                          az=az, 
                                          el=el 
                                          )
                sat_count += 1
            print(f"[{timestamp_str}] Logged {sat_count} satellites.")
        
        # (5) Ionosphere
        # FIXME: Needs fixing
        #ionosphere = self.fetch_ionosphere()
        #self.data_store["ionosphere"].append(ionosphere)
        

    def start_monitoring(self, interval_seconds=60, max_iter=None, verbose=False):
        """
        Starts the continuous polling loop.
        """
        print(
            f"Starting AirspaceRecorder for ({self.lat}, {self.lon}). Press"
            " Ctrl+C to stop."
        )
        try:
            i = 0
            while True:
                # Fetch data
                self.poll_once()
                i += 1
                
                # Print data to screen if requested
                if verbose:
                    print(json.dumps(self.data_store, indent=4))
                print("-" * 40)
                
                # Output journal record and then reset
                with open("journal.csv", 'a') as f:
                    for i in range(len(self.journal['timestamp'])):
                    
                self.reset_journal()

                # Test if maximum no. of iterations has been reached
                if max_iter is not None:
                    if i >= max_iter:
                        break

                # Wait for next iteration
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\nRecorder stopped by user.")


if __name__ == "__main__":
    
    # Read n2yo API key from file
    with open("n2yo_api_key.apikey", "r") as f:
        n2yo_api_key = f.readline()[:-1]  # trim trailing newline

    # Run for a single iteration
    sa = SituationAwarenessRecorder(
        latitude=53.234551,
        longitude=-2.3047266,
        flight_bounding_delta=0.3,
        n2yo_api_key=n2yo_api_key,
    )
    
    # Start monitoring
    sa.start_monitoring(max_iter=None, interval_seconds=60, verbose=False)
    
