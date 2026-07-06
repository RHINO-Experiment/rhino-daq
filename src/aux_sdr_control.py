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
import prerun_config
import config

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

    print("auxSDR:","hardware info", sdr.getHardwareInfo())

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
    max_adc = []
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
        max_adc_i = np.max(np.abs(np.array(buffs)))
        max_adc.append(max_adc_i)
        print(t)
        print(f"Max Aux ADC: {max_adc_i}")
        print(f'Remaining Aux: {t_f - t} s')
        pass

    sdr.deactivateStream(rxStream) #stop streaming
    sdr.closeStream(rxStream)

    print('SDRPlay Stream Deactivated')
    waterfall_spectra = np.array(waterfall_spectra)
    times = np.array(times)
    freqs = np.linspace(-bandwidth/2/1e6 + centre_frequency/1e6, 
                                              bandwidth/2/1e6 + centre_frequency/1e6,
                                              nChannels)
    max_adc = np.array(max_adc)
    return waterfall_spectra, times, freqs, max_adc


def main():
    parser = argparse.ArgumentParser(description="Dual SDR Observation (RTLSDR + SDRplay)")

    # Add more arguments for lone-running
    parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    
    parser.add_argument('--prerun',
                        action='store_true',
                        help='Runs the Script in Prerun Mode')

    args = parser.parse_args()

    yaml_path = args.yaml
    pre_run_status = args.prerun

    if pre_run_status:
        params = prerun_config.return_aux_sdr_params(yaml_path)
    else:
        params = config.return_aux_sdr_params(yaml_path)

    runLength = params['runLength']
    obsCachePath = params['obsCachePath']
    active = params['active']
    centreFrequency = params['centreFrequency']
    bandwidth = params['bandwidth']
    nChannels = params['nChannels']
    sdrDriver = params['sdrDriver']
    sdrLabel = params['sdrLabel']
    sdrId = params['sdrId']
    sampleIntegrationTime = params['sampleIntegrationTime']
    spectrometerMode = params['spectrometerMode']
    sdrGain = params['sdrGain']
    sdrRFGR = params['sdrRFGR']
    sdrIFGR = params['sdrIFGR']
    delay = params['delay']
    nTaps = params['nTaps']
    appliedWindow = params['appliedWindow']
    if not active: # returns from main if the program is not active
        return
    # add delay , runLength = runLength - delay
    runLength = runLength - delay

    time.sleep(delay)

    waterfall_spectra, times, freqs, max_i_adc, max_q_adc = measure_spectra(sampleIntegrationTime = sampleIntegrationTime,
                                                      runLength = runLength,
                                                      centre_frequency = centreFrequency,
                                                      bandwidth = bandwidth,
                                                      nChannels = nChannels,
                                                      sdrDriver = sdrDriver,
                                                      sdrId = sdrId,
                                                      sdrGain = sdrGain,
                                                      sdrRFGR=sdrRFGR,
                                                      sdrIFGR=sdrIFGR,
                                                      sdrLabel = sdrLabel,
                                                      spectrometerMode = spectrometerMode,
                                                      nTaps = nTaps,
                                                      appliedWindow = appliedWindow)

    np.save(f'{obsCachePath}/aux_sdr_waterfall.npy', arr=waterfall_spectra)
    np.save(f'{obsCachePath}/aux_sdr_times.npy', arr=times)
    np.save(f'{obsCachePath}/aux_sdr_freqs.npy', arr=freqs)
    np.save(f'{obsCachePath}/aux_max_i_adc.npy', arr=max_i_adc)
    np.save(f'{obsCachePath}/aux_max_q_adc.npy', arr=max_q_adc)

    np.save(f'{obsCachePath}/new_data_bool.npy', True)
    print('Data Cached')
    pass

if __name__ == "__main__":
    main()