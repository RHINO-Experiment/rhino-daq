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

AVAILABLE_SDR_FLAGS = ['biasT_ctrl', 
                       'rfnotch_ctrl', 
                       'dabnotch_ctrl', 
                       'hdr_ctrl', 
                       'iqcorr_ctrl'
                       ]

def time_format(t):
    """
    Format a time in seconds into a duration in h/m/s.
    """
    h = int(t // 3600)
    m = int((t - h*3600) // 60)
    s = int(t - h*3600 - m*60)
    return f"{h}h {m:02d}m {s:02d}s"

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
                    sdrFlags='rfnotch_ctrl,dabnotch_ctrl',
                    obsCachePath=None,
                    partial_save_block=None,
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
        sdrFlags (list of str):
            SDR settings to enable, via the Soapy interface. This should be 
            passed as a string of comma-separated values. Settings that are 
            present in the string are enabled (set to True). Others are 
            explicitly set to False. For the SDRPlay driver, the following 
            settings are available (case sensitive!):
            `biasT_ctrl, rfnotch_ctrl, dabnotch_ctrl, hdr_ctrl, iqcorr_ctrl`.
        obsCachePath (str):
            Directory to store the data files in if partial saves are enabled. 
            Will use the filename `sdr_data_nnnnnnnn.npz` within this directory.
        partial_save_block (int):
            Save a partial data file every `partial_save_block` time samples. 
            If set to None, do not perform partial saves.
        verbose (bool):
            Whether to print diagnostic messages.
    
    Returns:
        waterfall_spectra (array_like):
            Array of measured PSD values, of shape `(Ntimes, Nchannels)`.
        times (array_like):
            Timestamps for each time sample, in seconds since the UNIX epoch.
        freqs (array_like):
            Array of frequency channel centre values in MHz.
        adc_stats (list of tuple):
            List of tuples with the ADC statistics for each time sample, in the 
            order: `(I_min, I_max, Q_min, Q_max)`.
    """
    # Set up channelisation mode
    if spectrometerMode == 'fft':
        # Number of frames for each time sample
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
        n_spec_points = nChannels * nTaps # no. sample points needed to form spectrum
        n_frames = int(sampleIntegrationTime * bandwidth / (nChannels * nTaps))
    
    # Set-up SDR sampling parameters
    rx_chan = 0 # only 1 channel on RSP1A
    sdr = SoapySDR.Device(dict(driver=sdrDriver, label=sdrLabel))
    sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, bandwidth)
    sdr.setFrequency(SOAPY_SDR_RX, rx_chan, centre_frequency)
    sdr.setBandwidth(SOAPY_SDR_RX, rx_chan, int(bandwidth))
    
    # Calculate frequency channel locations in MHz
    freqs = np.linspace(-bandwidth/2/1e6 + centre_frequency/1e6, 
                         bandwidth/2/1e6 + centre_frequency/1e6,
                         nChannels)
    
    # Set settings, e.g. notch filters (some may be ignored; depends on SDR)
    sdr_flags = sdrFlags.strip().replace(" ", "").split(",")
    for flag in sdr_flags:
        if flag not in AVAILABLE_SDR_FLAGS:
            raise ValueError(f"SDR flag '{flag}' not found in AVAILABLE_SDR_FLAGS")
    for flag in AVAILABLE_SDR_FLAGS:
        if flag in sdr_flags:
            sdr.writeSetting(SOAPY_SDR_RX, rx_chan, flag, "true")
            if verbose:
                print(f"  SDR setting: {flag}=true")
        else:
            sdr.writeSetting(SOAPY_SDR_RX, rx_chan, flag, "false")
            if verbose:
                print(f"  SDR setting: {flag}=false")
    
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
        print("  Hardware info:     ", sdr.getHardwareInfo())
        print("  Stream MTU:        ", sdr.getStreamMTU(rxStream))
        print("  Frames per sample: ", n_frames)
        print("  Sample pts/frame:  ", n_spec_points)
        print("  Activate status:   ", status)
        print("  Sample rate:        %6.4f MSPS" \
                % (sdr.getSampleRate(SOAPY_SDR_RX, rx_chan) / 1e6))
        print("  Frequency:          %6.4f MHz" \
                % (sdr.getFrequency(SOAPY_SDR_RX, rx_chan) / 1e6))
        print("  Bandwidth:          %6.4f MHz" \
                % (sdr.getBandwidth(SOAPY_SDR_RX, rx_chan) / 1e6))
        print("  Current gain:      ", sdr.getGain(SOAPY_SDR_RX, rx_chan))
        print("  RF gain idx:       ", sdr.readSetting("rfgain_sel"))
        print("  Gain mode (AGC):   ", sdr.getGainMode(SOAPY_SDR_RX, rx_chan))
        print("")
    
    sdr.deactivateStream(rxStream) # stop streaming after test
    
    # Get the MTU (max. transmission unit)
    sdr_mtu = sdr.getStreamMTU(rxStream)
    
    # Set total observing time
    t_f = time.time() + runLength
    
    # Prepare data arrays/lists (complex64 == CF32 in Soapy driver)
    # How many reads are needed to populate a full time sample
    reads_per_sample = int(np.ceil(n_frames * n_spec_points / sdr_mtu))
    
    # Buffers for single read, full set of reads for time sample, and status flags
    single_buffer = np.zeros((sdr_mtu,), dtype=np.complex64) # buffer for single read 
    sample_buffer = np.zeros((reads_per_sample, sdr_mtu), dtype=np.complex64) # full frame
    daq_status = np.zeros(reads_per_sample, dtype=int)
    
    # Reshaped array containing a full set of frames for the time sample
    frame_set = np.zeros((n_frames, n_spec_points), dtype=np.complex64) 
    
    # Lists for storing outputs
    waterfall_spectra = []
    times = []
    adc_stats = []
    
    # Prepare for streaming the data (assumes the previous gain values are OK)
    sdr.activateStream(rxStream)
    
    # Loop for the full duration of the observation
    t = time.time()
    tidx = -1
    tidx_last_save = 0 # time sample index when the data were last saved
    save_block = 0
    while t < t_f:
        # Update time sample index counter
        tidx += 1
        
        # Current time
        t = time.time()
        
        # Loop over individual samples pulled from the ADC 
        # (minimise operations within this inner loop to maintain performance)
        for i in range(reads_per_sample):
            # Read set of samples for a single spectrum and store status 
            result = sdr.readStream(rxStream, 
                                    [single_buffer,], 
                                    len(single_buffer), 
                                    timeoutUs=int(100e3))
            daq_status[i] = int(result.ret)
            sample_buffer[i] = single_buffer[:]
            single_buffer[:] = 0. # zero the buffer just in case
        
        # Reshape sample_buffer (nreads, sdr_mtu) into (n_frames, n_spec_points)
        n = n_frames * n_spec_points
        frame_set[:,:] = sample_buffer.flatten()[:n].reshape((n_frames, n_spec_points))
        
        # Convert streamed data to a single spectrum (i.e. for one time sample)
        spectra = spectrometer_func(frame_set=frame_set, 
                                    win_coeffs=win_coeffs, 
                                    nChannels=nChannels, 
                                    nTaps=nTaps, 
                                    daq_status=daq_status)
        waterfall_spectra.append(spectra)
        times.append(time.time())
        
        # Acquire ADC statistics
        adc_stats.append((frame_set.real.min(), 
                          frame_set.real.max(),
                          frame_set.imag.min(),
                          frame_set.imag.max()))
        
        # Zero the buffer ready for next sample
        sample_buffer[:,:] = 0.
        frame_set[:,:] = 0.
        
        if verbose:
            adc_i_min, adc_i_max, adc_q_min, adc_q_max = adc_stats[-1]
            print(f"\nTime sample {tidx}")
            print(f"\tADC range (I): {adc_i_min:.5f} -- {adc_i_max:.5f}")
            print(f"\tADC range (Q): {adc_q_min:.5f} -- {adc_q_max:.5f}")
            print("\tRemaining: %s" % time_format(t_f - t))
        
        # Do a partial save of a block of time samples if needed
        if partial_save_block is not None:
            if tidx > 0 and tidx % partial_save_block == 0:
                # Save the most recent block to a file
                partial_file_name = f'{obsCachePath}/sdr_data_{save_block:08d}.npz'
                np.savez_compressed(
                        partial_file_name,
                        waterfall=np.array([waterfall_spectra[ii] 
                                            for ii in range(tidx_last_save, tidx)]),
                        times=np.array(times)[tidx_last_save:tidx],
                        freqs=freqs,
                        adc_stats=np.array(adc_stats)[tidx_last_save:tidx]
                        )
                tidx_last_save = tidx
                save_block += 1
                if verbose:
                    print(f"Saved partial data file {partial_file_name}")
    
    # Stop observation and close stream
    sdr.deactivateStream(rxStream)
    sdr.closeStream(rxStream)
    if verbose:
        print('SDR data stream deactivated')
    
    # Convert waterfall and metadata into arrays
    waterfall_spectra = np.array(waterfall_spectra)
    times = np.array(times)
    
    return waterfall_spectra, times, freqs, np.array(adc_stats)


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
    waterfall_spectra, times, freqs, adc_stats = \
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
                      sdrFlags=params['sdrFlags'],
                      spectrometerMode=params['spectrometerMode'],
                      nTaps = params['nTaps'],
                      appliedWindow = params['appliedWindow'],
                      obsCachePath=params['obsCachePath']
                      )
    
    # Save the full set of results to a compressed numpy file
    obsCachePath = params['obsCachePath']
    np.save(f'{obsCachePath}/new_data_bool.npy', True)
    np.savez_compressed(f'{obsCachePath}/sdr_data.npz',
                        waterfall=waterfall_spectra,
                        times=times,
                        freqs=freqs,
                        adc_stats=adc_stats)
    
    print('SDR data stored')

if __name__ == "__main__":
    main()
