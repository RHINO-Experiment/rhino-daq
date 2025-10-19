import time
import numpy as np
import os
import SoapySDR
from SoapySDR import * #SOAPY_SDR_ constants
from scipy.signal import windows
import argparse
import yaml
import fft_funcs
import pfb_funcs

def measure_spectra(sampleIntegrationTime,
                    runLength,
                    centre_frequency,
                    bandwidth,
                    nChannels,
                    sdrDriver, 
                    sdrId,
                    sdrGain,
                    sdrLabel,
                    spectrometerMode,
                    nTaps,
                    appliedWindow):
    
    if spectrometerMode == 'fft':
        win_coeffs = fft_funcs.window_dict[appliedWindow](nChannels) # get fft window
        nsamp = int(sampleIntegrationTime * bandwidth / nChannels) # fft_case number of frames for each fft
        spectrometer_func = fft_funcs.buffs_to_powers
        nStream = nChannels
        nTaps = None
    else:
        win_coeffs = pfb_funcs.create_window(appliedWindow, nChannels, nTaps)
        nsamp = int(sampleIntegrationTime * bandwidth / (nChannels*nTaps)) # pfb number of frames for each pfb
        spectrometer_func = pfb_funcs.buffs_to_powers
        nStream = nChannels * nTaps

    nthin = 1
    print('nsamp', nsamp)
    rx_chan = 0 # only 1 channel on RSP1A
    sdr = SoapySDR.Device(dict(driver=sdrDriver, label=sdrLabel))
    sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, bandwidth)
    sdr.setFrequency(SOAPY_SDR_RX, rx_chan, centre_frequency)
    sdr.setBandwidth(SOAPY_SDR_RX, rx_chan, int(bandwidth)) # intialises the SDR with settings

    sdr.setGainMode(SOAPY_SDR_RX, rx_chan, False) # turn ON AGC
    sdr.setGain(SOAPY_SDR_RX, rx_chan, sdrGain)
    rxStream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [rx_chan])

    print("hardware info", sdr.getHardwareInfo())

    status = sdr.activateStream(rxStream) #start streaming
    print("Stream MTU:", sdr.getStreamMTU(rxStream))
    print("Activate status:", status)
    print("Current gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan))
    print("Current Gain Mode, AGC:", sdr.getGainMode(SOAPY_SDR_RX, rx_chan)) # check if AGC is on
    print("")

    sdr.writeSetting("rfnotch_ctrl", "true") # set notches
    sdr.writeSetting("dabnotch_ctrl", "true")

    print("RF gain idx:", sdr.readSetting("rfgain_sel"))

    #final_gain = 0 # FIXME
    sdr.deactivateStream(rxStream) #stop streaming

    if sdr.getStreamMTU(rxStream) < nStream:
        nStream = sdr.getStreamMTU(rxStream)

    sdr.activateStream(rxStream)

    buff = np.zeros((nStream,), np.complex64)

    t_f = time.time() + runLength

    waterfall_spectra = []
    times = []
    t = time.time()
    while t < t_f:
        buffs = []
        for i in range(nsamp):
            # Receive some samples
            t0 = time.perf_counter_ns()
            sr = sdr.readStream(rxStream, [buff], len(buff), timeoutUs=int(100e3))
            tend = time.perf_counter_ns()

            if int(sr.ret) < 0:
                print("Error status encountered: %d (%d)" % (sr.ret, i))

            if i % 500 == 0:
                print("Time diff (ms):", (tend - t0)/1e6)
                print("Samples received:", sr.ret, np.sum(buff)) # number of samples read or the error code

            buffs.append(buff[::nthin].copy())
            buff[:] = 0.

            # Save output
        spectra = spectrometer_func(buffs, win_coeffs, nChannels, nTaps)
        waterfall_spectra.append(spectra)
        times.append(time.time())
        t = time.time()
        print(t)
        pass

    sdr.deactivateStream(rxStream) #stop streaming
    sdr.closeStream(rxStream)

    print('SDRPlay Stream Deactivated')
    waterfall_spectra = np.array(waterfall_spectra)
    times = np.array(times)
    freqs = np.linspace(-bandwidth/2/1e6 + centre_frequency/1e6, 
                                              bandwidth/2/1e6 + centre_frequency/1e6,
                                              nChannels)
    return waterfall_spectra, times, freqs


def main():
    parser = argparse.ArgumentParser(description="Dual SDR Observation (RTLSDR + SDRplay)")

    # Add more arguments for lone-running
    parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    
    args = parser.parse_args()

    yaml_path = args.yaml

    sdr_config_path = 'sdr'

    with open(yaml_path,'r') as f:
        obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
        pass
    # Observation Parameters

    runLength = obs_config['observationParams']['runLength']
    obsCachePath = obs_config['observationParams']['obsCachePath']

    sdr_config = obs_config[sdr_config_path]
    active = sdr_config['active']
    if not active: # returns from main if the program is not active
        return
    centreFrequency = sdr_config['centreFrequency']
    bandwidth = sdr_config['bandwidth']
    nChannels = sdr_config['nChannels']
    sdrDriver = sdr_config['sdrDriver']
    sdrLabel = sdr_config['sdrLabel']
    sdrId = sdr_config['sdrId']
    sampleIntegrationTime = sdr_config['sampleIntegrationTime']
    spectrometerMode = sdr_config['spectrometerMode']
    sdrGain = sdr_config['sdrGain']

    if spectrometerMode == 'pfb':
        nTaps = sdr_config['pfbParams']['nTaps']
        appliedWindow = sdr_config['pfbParams']['appliedWindow']
    else:
        nTaps = None
        appliedWindow = sdr_config['fftParams']['appliedWindow']

    waterfall_spectra, times, freqs = measure_spectra(sampleIntegrationTime = sampleIntegrationTime,
                                                      runLength = runLength,
                                                      centre_frequency = centreFrequency,
                                                      bandwidth = bandwidth,
                                                      nChannels = nChannels,
                                                      sdrDriver = sdrDriver, 
                                                      sdrId = sdrId,
                                                      sdrGain = sdrGain,
                                                      sdrLabel = sdrLabel,
                                                      spectrometerMode = spectrometerMode,
                                                      nTaps = nTaps,
                                                      appliedWindow = appliedWindow)

    np.save(f'{obsCachePath}/sdr_waterfall.npy', arr=waterfall_spectra)
    np.save(f'{obsCachePath}/sdr_times.npy', arr=times)
    np.save(f'{obsCachePath}/sdr_freqs.npy', arr=freqs)

    np.save(f'{obsCachePath}/new_data_bool.npy', True)
    print('Data Cached')
    pass

if __name__ == "__main__":
    main()