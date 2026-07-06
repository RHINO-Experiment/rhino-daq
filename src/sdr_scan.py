import numpy as np
from sdr_control import measure_spectra
import datetime

SAVE_DIR = 'data'

def scan_measure(safe_bandwidth,
                 start_frequency,
                 stop_frequency,
                 sampleIntegrationTime,
                 runLength,
                 bandwidth,
                 sdrDriver,
                 sdrId,
                 sdrGain,
                 nChannels,
                 sdrLabel,
                 spectrometerMode,
                 nTaps=None,
                 appliedWindow=None):

    centre_frequencies = np.arange(start_frequency,
                                   stop_frequency,
                                   safe_bandwidth/2)
    
    spectrometer_powers = []
    spectrometer_freqs = []
    spectrometer_times = []
    adc_max_i = []
    adc_max_q = []


    for centre_frequency in centre_frequencies:
        print(f'Measuring at centre frequency: {centre_frequency/1e6} MHz')

        waterfall_spectra, times, freqs, max_i_adc, max_q_adc = measure_spectra(sampleIntegrationTime = sampleIntegrationTime,
                                                      runLength = runLength,
                                                      centre_frequency = centre_frequency,
                                                      bandwidth = bandwidth,
                                                      nChannels = nChannels,
                                                      sdrDriver = sdrDriver,
                                                      sdrId = sdrId,
                                                      sdrGain = sdrGain,
                                                      sdrLabel = sdrLabel,
                                                      spectrometerMode = spectrometerMode,
                                                      nTaps = nTaps,
                                                      appliedWindow = appliedWindow)
        spectra = np.mean(waterfall_spectra, axis=0)
        time = np.mean(times)
        spectrometer_powers.append(spectra)
        spectrometer_freqs.append(freqs)
        spectrometer_times.append(time)
        adc_max_i.append(np.max(max_i_adc))
        adc_max_q.append(np.max(max_q_adc))
    
    spectrometer_powers = np.array(spectrometer_powers)
    spectrometer_freqs = np.array(spectrometer_freqs)
    spectrometer_times = np.array(spectrometer_times)
    adc_max_i = np.array(adc_max_i)
    adc_max_q = np.array(adc_max_q)

    return_dict = {'spectrometer_powers': spectrometer_powers,
                   'spectrometer_freqs': spectrometer_freqs,
                   'spectrometer_times': spectrometer_times,
                   'adc_max_i': adc_max_i,
                   'adc_max_q': adc_max_q,
                   'centre_frequencies': centre_frequencies}

    return return_dict

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Run an SDR scan observation based on a .yaml config file')
    
    parser.add_argument('--start_frequency', type=float, required=True,
                        help='Start frequency for the scan (Hz)')
    parser.add_argument('--stop_frequency', type=float, required=True,
                        help='Stop frequency for the scan (Hz)')
    parser.add_argument('--safe_bandwidth', type=float, default=6e6,
                        help='Safe bandwidth to use for each measurement (Hz)')
    parser.add_argument('--sampleIntegrationTime', type=float, default=1.0,
                        help='Integration time for each sample (s)')
    parser.add_argument('--nChannels', type=int, default=1024,
                        help='Number of channels to use for the spectrometer')
    parser.add_argument('--runLength', type=float, default=10.0,
                        help='Total run length for each measurement (s)')
    parser.add_argument('--bandwidth', type=float, default=8e6,
                        help='Bandwidth for each measurement (Hz)')
    parser.add_argument('--sdrDriver', type=str, default='sdrplay',
                        help='SDR driver to use (e.g., "sdrplay", "rtlsdr")')
    parser.add_argument('--sdrId', type=int, default=2302031848,
                        help='SDR ID to use for the measurement')
    parser.add_argument('--sdrGain', type=int, default=39,
                        help='Gain setting for the SDR (dB)')
    parser.add_argument('--sdrLabel', type=str, default='SDRplay Dev0 RSPdx 2302031848',
                        help='Label for the SDR being used')
    parser.add_argument('--spectrometerMode', type=str, default='pfb',
                        help='Spectrometer mode to use (e.g., "pfb", "fft")')
    parser.add_argument('--nTaps', type=int, default=4,
                        help='Number of taps to use for PFB spectrometer mode')
    parser.add_argument('--appliedWindow', type=str, default='blackman',
                        help='Window function to apply to the samples (e.g., "blackman", "hann")')
    args = parser.parse_args()

    measure_dict = scan_measure(safe_bandwidth=args.safe_bandwidth,
                                start_frequency=args.start_frequency,
                                stop_frequency=args.stop_frequency,
                                sampleIntegrationTime=args.sampleIntegrationTime,
                                runLength=args.runLength,
                                bandwidth=args.bandwidth,
                                nChannels=args.nChannels,
                                sdrDriver=args.sdrDriver,
                                sdrId=args.sdrId,
                                sdrGain=args.sdrGain,
                                sdrLabel=args.sdrLabel,
                                spectrometerMode=args.spectrometerMode,
                                nTaps=args.nTaps,
                                appliedWindow=args.appliedWindow)
    
    current_time = datetime.datetime.now()

    filename = current_time.strftime("%Y-%m-%d_%H-%M-%S_sdr_scan.npz")

    spectrometer_powers = measure_dict['spectrometer_powers']
    spectrometer_freqs = measure_dict['spectrometer_freqs']
    spectrometer_times = measure_dict['spectrometer_times']
    adc_max_i = measure_dict['adc_max_i']
    adc_max_q = measure_dict['adc_max_q']
    centre_frequencies = measure_dict['centre_frequencies']

    np.savez(f'{SAVE_DIR}/{filename}',
             spectrometer_powers=spectrometer_powers,
             spectrometer_freqs=spectrometer_freqs,
             spectrometer_times=spectrometer_times,
             adc_max_i=adc_max_i,
             adc_max_q=adc_max_q,
             centre_frequencies=centre_frequencies,
             safe_bandwidth=args.safe_bandwidth)
    
    print('Observation complete. Data saved to:', f'{SAVE_DIR}/{filename}')

if __name__ == "__main__":
    main()