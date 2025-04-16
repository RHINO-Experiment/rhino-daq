#!/usr/bin/env python3


import SoapySDR
from SoapySDR import * #SOAPY_SDR_ constants
import numpy as np
import argparse
import h5py
import matplotlib.pyplot as plt
import sys, time

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("observation_duration", help='Time of Observation [s]', type=float)
    parser.add_argument("averaging_time", help="Averaging Time per spectra [s]", type=float)
    parser.add_argument("-cf", "--centre_freq", help="Centre Frequency to set LO to [Hz]", type=float)
    parser.add_argument("-fl", "--fft_length", help="Length of Fourier Transform. Ensure 2^N for efficiency", type=int)
    parser.add_argument("-fw", "--fft_window", help="FFT window (Rectangular, Blackman, )", type=str, choices=['Rectangular, Blackman'])
    parser.add_argument("-g", "--sdr_gain", help='Gain of SDR [dB]', type=int)
    parser.add_argument("-sr", "--sample_rate", help="Set samplerate/bandwidth of SDR [Hz]", type=float, choices=[10e6, 8e6, 6e6, 4e6,2e6])
    args = parser.parse_args()

    if args.centre_freq == None:
        centre_freq = 70e6
    else:
        centre_freq = args.centre_freq

    if args.fft_length == None:
        fft_length = 16384
    else:
        fft_length = args.fft_length

    if args.fft_window == None:
        fft_window = 'Rectangular'
    else:
        fft_window = args.fft_window

    if args.sdr_gain == None:
        gain = 36
    else:
        gain = args.sdr_gain

    if args.sample_rate == None:
        sample_rate = 8e6
    else:
        sample_rate = args.sample_rate
    
    observation_duration = float(args.observation_duration)
    averaging_time = float(args.averaging_time)


    nthin = 1
    nsamp = int(averaging_time * sample_rate / fft_length)
    rx_chan = 0 # only 1 channel on RSP1A
    sdr = SoapySDR.Device(dict(driver="sdrplay"))
    sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, sample_rate)
    sdr.setFrequency(SOAPY_SDR_RX, rx_chan, centre_freq)
    sdr.setBandwidth(SOAPY_SDR_RX, rx_chan, int(sample_rate))
    #sdr.setGainMode(SOAPY_SDR_RX, rx_chan, True) # turn ON AGC

    sdr.setGainMode(SOAPY_SDR_RX, rx_chan, False) # turn ON AGC
    sdr.setGain(SOAPY_SDR_RX, rx_chan, gain)
    rxStream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [rx_chan])

    print("hardware info", sdr.getHardwareInfo())

    status = sdr.activateStream(rxStream) #start streaming
    print("Stream MTU:", sdr.getStreamMTU(rxStream))
    print("Activate status:", status)
    print("Current gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan))
    print("")

    sdr.writeSetting("rfnotch_ctrl", "true")
    sdr.writeSetting("dabnotch_ctrl", "true")

    print("RF gain idx:", sdr.readSetting("rfgain_sel"))

    final_gain = 0 # FIXME
    sdr.deactivateStream(rxStream) #stop streaming

    if sdr.getStreamMTU(rxStream) < fft_length:
        fft_length = sdr.getStreamMTU(rxStream)

    #print("Setting:", sdr.readSetting("rfnotch_ctrl"))

    #print("Time:", SOAPY_SDR_HAS_TIME)
    #print("Ref. clock rate:", sdr.getReferenceClockRate())
    #sys.exit(0)
    nblocks = int(observation_duration / averaging_time)
    spectras = []
    gains = []
    times = []
    status = sdr.activateStream(rxStream) # start streaming
    for n in range(nblocks):
        #status = sdr.activateStream(rxStream) #start streaming
        #num_samps = int(sdr.getStreamMTU(rxStream)) + 0
        buff = np.zeros((fft_length,), np.complex64)
        buffs = []


        t_all_start = time.time()
        for i in range(nsamp):
            if i % 100 == 0:
                print("    Recv. sample %d" % i)

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
    
        gains.append(sdr.getGain(SOAPY_SDR_RX, rx_chan))

        t_all_end = time.time()

    # Get gain info
    #final_gain = sdr.getGain(SOAPY_SDR_RX, rx_chan)
    #rfgain = sdr.readSetting("rfgain_sel")
    #print("Gains:", final_gain, rfgain)
    #sdr.deactivateStream(rxStream) #stop streaming

        # Save output
        tt0 = time.time()
        print("    Saving PSD")
        spectra = []
        for i in range(len(buffs)):
            d = buffs[i]
            PSD = np.abs(np.fft.fftshift(np.fft.fft(d)))**2
            spectra.append(PSD)
        spectra = np.array(spectra)
        spectra = np.mean(spectra, axis=0)
        spectras.append(spectra)
        times.append(time.time())
    
    

    # Close the stream
    sdr.deactivateStream(rxStream) #stop streaming
    sdr.closeStream(rxStream)

    

    spectras = np.array(spectras)
    gains = np.array(gains)
    times = np.array(times)
    freq_channels_mhz =  np.linspace(-sample_rate/2/1e6 + centre_freq/1e6, sample_rate/2/1e6 + centre_freq/1e6, fft_length)

    t_save = time.time()

    with h5py.File("data_%d.hd5f" % t_save, mode='a') as file:
        file.create_dataset('psd', data=spectras, dtype=spectras.dtype)
        file.create_dataset('times', data=times, dtype=times.dtype)
        file.create_dataset('gains', data=gains, dtype=gains.dtype)
        file.create_dataset('channel_freqs', data=freq_channels_mhz, dtype=freq_channels_mhz.dtype)

    print("    Saving PSD took %5.2f sec" % (time.time() - tt0))

#print(dir(sdr))
    print(sdr.listGains(SOAPY_SDR_RX, rx_chan))
    print(sdr.getBandwidth(SOAPY_SDR_RX, rx_chan))
    print(sdr.listAntennas(SOAPY_SDR_RX, rx_chan))
    print("        done...")
