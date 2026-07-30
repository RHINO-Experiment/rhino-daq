import time
import numpy as np
import os
import SoapySDR
from SoapySDR import * #SOAPY_SDR_ constants
from scipy.signal import windows
import argparse
import yaml
import spectrum
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
                    sdrIFGR,
                    sdrRFGR,
                    sdrLabel,
                    spectrometerMode,
                    nTaps,
                    appliedWindow,
                    verbose=True):
    """
    Acquire IQ samples from SoapySDR and transform to chanelised and time-
    averaged power spectra.
    
    Parameters:
        sampleIntegrationTime (float):
            Integration time for each time sample, in sec. This will not be an 
            exact value, as an integer number of frames will be used, i.e. 
            `n_frames = int(sampleIntegrationTime * bandwidth / nChannels)`.
        runLength (float):
            How long to run the data acquisition for, in seconds.
        centre_frequency (float):
            The centre frequency of the SDR observation, in Hz.
        bandwidth (float):
            Bandwidth of the SDR observation, in Hz. Should be one of the 
            supported bandwidth values for the SDR.
        nChannels (int):
            Number of frequency channels to divide the bandwidth into.
        sdrDriver (str):
            Name of the SoapySDR SDR driver, e.g. `sdrplay'. 
        sdrId (int):
            ID number of the SDR. Will normally be `0` unless there are 
            multiple SDRs connected.
        sdrGain (int):
            WHich gain level to use in the SDR. Note that this may not 
            correspond directly to a gain in dB, and could even correspond to 
            and attenuation level.
        sdrIFGR (int):
            Gain level integer for the intermediate frequency LNA stage.
        sdrRFGR (int):
            Gain level integer for the RF LNA stage.
        sdrLabel (str):
            Name to give the SDR, for identification purposes.
        spectrometerMode (str):
            Whether to use `fft` or `pfb` channelisation.
        nTaps (int):
            Number of taps to use for the polyphase filter bank (PFB) if that 
            channelisation mode is selected.
        appliedWindow (str):
            Name of the window function to apply when channelising. 
            See `spectrum.window_dict` for options.
        verbose (bool):
            Whether to print diagonostic messages.
    
    Returns:
        waterfall_spectra (array_like):
            Array of measured PSD values, of shape `(Ntimes, Nchannels)`.
        times (array_like):
            Timestamps for each time sample, in seconds since the UNIX epoch.
        freqs (array_like):
            Array of frequency channel centre values in MHz.
        max_i_adc, max_q_adc (array_like):
            Arrays of maximum ADC values for the I and Q channels, for each 
            time sample.
    """
    # Set up channelisation mode
    if spectrometerMode == 'fft':
        # Number of frames for each fft
        n_frames = int(sampleIntegrationTime * bandwidth / nChannels)
        
        # Set spectrometer function and sampling parameters
        spectrometer_func = spectrum.buffer_to_psd_fft
        win_coeffs = spectrum.window_dict[appliedWindow](nChannels)
        n_spec_points = nChannels
        nTaps = None
    else:
        # 
        win_coeffs = spectrum.create_window(appliedWindow, nChannels, nTaps)
        
        # Set spectrometer function and sampling parameters
        spectrometer_func = spectrum.buffer_to_psd_pfb
        n_spec_points = nChannels * nTaps # no. 
        n_frames = int(sampleIntegrationTime * bandwidth / (nChannels*nTaps))
    
    # Set-up SDR sampling parameters
    if verbose:
        print('n_frames', n_frames)
    rx_chan = 0 # only 1 channel on RSP1A
    sdr = SoapySDR.Device(dict(driver=sdrDriver, label=sdrLabel))
    sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, bandwidth)
    sdr.setFrequency(SOAPY_SDR_RX, rx_chan, centre_frequency)
    sdr.setBandwidth(SOAPY_SDR_RX, rx_chan, int(bandwidth))
    
    # Set notch filters if available (some may be ignored; depends on SDR)
    # FIXME: Commented out the first two
    #sdr.writeSetting("rfnotch_ctrl", "true")
    #sdr.writeSetting("dabnotch_ctrl", "true")
    #sdr.writeSetting("biasT_ctrl", "false")
    sdr.writeSetting(SOAPY_SDR_RX, rx_chan, "rfnotch_ctrl", "true")
    sdr.writeSetting(SOAPY_SDR_RX, rx_chan, "dabnotch_ctrl", "true")
    sdr.writeSetting(SOAPY_SDR_RX, rx_chan, "fmmnotch_ctrl", "true")
    
    # Set gain mode and settings manually, rather than using AGC
    sdr.setGainMode(SOAPY_SDR_RX, rx_chan, False) # turn OFF AGC
    sdr.setGain(SOAPY_SDR_RX, rx_chan, "RFGR", sdrRFGR) # set RF gain
    sdr.setGain(SOAPY_SDR_RX, rx_chan, "IFGR", sdrIFGR) # set IF gain
    if verbose:
        print("Current RF Gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan, "RFGR"))
        print("Current IF Gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan, "IFGR"))
    
    # Set gain
    if sdrGain is not None:
        sdr.setGain(SOAPY_SDR_RX, rx_chan, sdrGain)
    rxStream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [rx_chan])
    
    # Test-start the stream
    status = sdr.activateStream(rxStream) # start streaming
    if verbose:
        # Output hardware info, stream data stats, and gain info
        print("  Hardware info", sdr.getHardwareInfo())
        print("  Stream MTU:", sdr.getStreamMTU(rxStream))
        print("  Activate status:", status)
        print("  Current gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan))
        print("  RF gain idx:", sdr.readSetting("rfgain_sel"))
        print("  Current Gain Mode, AGC:", sdr.getGainMode(SOAPY_SDR_RX, rx_chan))
        print("")
    
    sdr.deactivateStream(rxStream) # stop streaming after test
    
    # Check that requested data frame size fits within the MTU (max. transmission unit)
    if sdr.getStreamMTU(rxStream) < n_spec_points:
        raise NotImplementedError("The SoapySDR MTU is smaller than the requested spectrum length, n_spec_points. Code to stitch togethe`r multiple packets has not yet been implemented.")
    
    # Set total observing time
    t_f = time.time() + runLength
    
    # Prepare data arrays/lists (complex64 == CF32 in Soapy driver)
    buff = np.zeros((n_spec_points,), np.complex64) # buffer for each 
    waterfall_spectra = []
    times = []
    max_i_adc = []
    max_q_adc = []
    
    # Prepare for streaming the data (assumes the previous gain values are OK)
    sdr.activateStream(rxStream)
    
    # Loop for the full duration of the observation
    while t < t_f:
        
        # Current time
        t = time.time()
        
        # Allocate memory for set of frames for one time sample
        frame_set = np.zeros((n_frames, n_spec_points), dtype=np.complex64)
        daq_status = np.zeros(n_frames, dtype=int)
        
        # Loop over individual samples pulled from the ADC 
        # (minimise operations within this inner loop to maintain performance)
        for i in range(n_frames):
            # Read set of samples for a single spectrum and store status 
            sr = sdr.readStream(rxStream, [buff,], len(buff), timeoutUs=int(100e3))
            daq_status[i] = int(sr.ret)
            frame_set[i] = buff
            buff[:] = 0. # zero buffer just in case
        
        # Save output
        spectra = spectrometer_func(frame_set, 
                                    win_coeffs, nChannels, nTaps, daq_status)
        waterfall_spectra.append(spectra)
        times.append(time.time())
        
        # Acquire ADC statistics
        max_adc_i = frame_set.real.max()
        max_adc_q = frame_set.imag.max()
        max_i_adc.append(max_adc_i)
        max_q_adc.append(max_adc_q)
        
        if verbose:
            print(t)
            print(f"Max ADC I: {max_adc_i}")
            print(f'Max ADC Q: {max_adc_q}')
            print(f'Remaining: {t_f - t} s')
    
    # Stop observation and close stream
    sdr.deactivateStream(rxStream)
    sdr.closeStream(rxStream)
    if verbose:
        print('SDRPlay stream deactivated')
    
    # Convert waterfall and metadata into arrays
    waterfall_spectra = np.array(waterfall_spectra)
    times = np.array(times)
    max_i_adc = np.array(max_i_adc)
    max_q_adc = np.array(max_q_adc)
    
    # Calculate frequency channel locations in MHz
    freqs = np.linspace(-bandwidth/2/1e6 + centre_frequency/1e6, 
                         bandwidth/2/1e6 + centre_frequency/1e6,
                         nChannels)
    return waterfall_spectra, times, freqs, max_i_adc, max_q_adc


def main():
    parser = argparse.ArgumentParser(
                        description="Dual SDR Observation (RTLSDR + SDRplay)"
                        )

    # Add arguments for lone-running
    parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    parser.add_argument('--prerun',
                        action='store_true',
                        help='Runs the Script in Prerun Mode')
    
    # Parse arguments
    args = parser.parse_args()
    yaml_path = args.yaml
    pre_run_status = args.prerun

    # Load observation parameters
    if pre_run_status:
        params = prerun_config.return_sdr_params(yaml_path)
    else:
        params = config.return_sdr_params(yaml_path)

    if not params['active']: # returns from main if the program is not active
        return
        
    # Add a delay before starting the observation
    runLength = params['runLength'] - params['delay']
    time.sleep(params['delay'])
    
    # Run the data acquisition
    waterfall_spectra, times, freqs, max_i_adc, max_q_adc = \
            measure_spectra(
                      sampleIntegrationTime=params['sampleIntegrationTime'],
                      runLength = runLength,
                      centre_frequency = params['centreFrequency'],
                      bandwidth = params['bandwidth'],
                      nChannels = params['nChannels'],
                      sdrDriver = params['sdrDriver'],
                      sdrId = params['sdrId'],
                      sdrGain=params['sdrGain'],
                      sdrRFGR=params['sdrRFGR'],
                      sdrIFGR=params['sdrIFGR'],
                      sdrLabel=params['sdrLabel'],
                      spectrometerMode=params['spectrometerMode'],
                      nTaps = params['nTaps'],
                      appliedWindow = params['appliedWindow'])
    
    # Save the results to files
    obsCachePath = params['obsCachePath']
    np.save(f'{obsCachePath}/sdr_waterfall.npy', arr=waterfall_spectra)
    np.save(f'{obsCachePath}/sdr_times.npy', arr=times)
    np.save(f'{obsCachePath}/sdr_freqs.npy', arr=freqs)
    np.save(f'{obsCachePath}/max_i_adc.npy', arr=max_i_adc)
    np.save(f'{obsCachePath}/max_q_adc.npy', arr=max_q_adc)
    np.save(f'{obsCachePath}/new_data_bool.npy', True)
    
    print('SDR Data Cached')

if __name__ == "__main__":
    main()
