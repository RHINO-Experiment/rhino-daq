#!/usr/bin/env python3


import SoapySDR
from SoapySDR import * #SOAPY_SDR_ constants
import numpy as np
import argparse
import h5py
import sys, time
import serial
import nanovna
from scipy.signal import windows

class SDRObserver:
    def __init__(self, sample_rate=8e6, centre_frequency=70e6, integration_time=5, fft_length=2048, window='Blackman', gain=36):
        self.sample_rate = sample_rate
        self.centre_frequency = centre_frequency
        self.integration_time = integration_time
        self.fft_length = fft_length
        self.window = np.ones(shape=(fft_length,))
        self.set_window(window)
        self.gain = gain
        self.freq_channels_mhz =  np.linspace(-sample_rate/2/1e6 + centre_frequency/1e6, 
                                              sample_rate/2/1e6 + centre_frequency/1e6,
                                              fft_length)
        pass

    def set_window(self, window_string='Blackman'):
        window_dict = {'Blackman':np.blackman,
                       'BlackmanHarris':windows.blackmanharris,
                       'Rectangular':np.ones,
                       'Cosine':windows.cosine}
        try:
            self.window = window_dict[window_string](self.fft_length)
        except:
            pass
    
    def initialise(self):
        self.nthin = 1
        self.nsamp = int(self.integration_time * self.sample_rate / self.fft_length)
        rx_chan = 0 # only 1 channel on RSP1A
        self.sdr = SoapySDR.Device(dict(driver="sdrplay"))
        self.sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, self.sample_rate)
        self.sdr.setFrequency(SOAPY_SDR_RX, rx_chan, self.centre_frequency)
        self.sdr.setBandwidth(SOAPY_SDR_RX, rx_chan, int(self.sample_rate)) # intialises the SDR with settings


        self.sdr.setGainMode(SOAPY_SDR_RX, rx_chan, False) # turn ON AGC
        self.sdr.setGain(SOAPY_SDR_RX, rx_chan, self.gain)
        self.rxStream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [rx_chan])

        print("hardware info", self.sdr.getHardwareInfo())

        self.status = self.sdr.activateStream(self.rxStream) #start streaming
        print("Stream MTU:", self.sdr.getStreamMTU(self.rxStream))
        print("Activate status:", status)
        print("Current gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan))
        print("")

        self.sdr.writeSetting("rfnotch_ctrl", "true") # set notches
        self.sdr.writeSetting("dabnotch_ctrl", "true")

        print("RF gain idx:", self.sdr.readSetting("rfgain_sel"))

        #final_gain = 0 # FIXME
        self.sdr.deactivateStream(self.rxStream) #stop streaming

        if sdr.getStreamMTU(self.rxStream) < self.fft_length:
            self.fft_length = sdr.getStreamMTU(self.rxStream)


        self.buff = np.zeros((self.fft_length,), np.complex64)

        
        #print("Setting:", sdr.readSetting("rfnotch_ctrl"))

        #print("Time:", SOAPY_SDR_HAS_TIME)
        #print("Ref. clock rate:", sdr.getReferenceClockRate())
        #sys.exit(0)

    def get_averaged_spectra(self):
        #buff = np.zeros((self.fft_length,), np.complex64) # set up buffer buffs for IQ samples
        buffs = []

        for i in range(self.nsamp):
            # Receive some samples
            t0 = time.perf_counter_ns()
            sr = self.sdr.readStream(self.rxStream, [self.buff], len(self.buff), timeoutUs=int(100e3))
            tend = time.perf_counter_ns()

            if int(sr.ret) < 0:
                print("Error status encountered: %d (%d)" % (sr.ret, i))

            if i % 500 == 0:
                print("Time diff (ms):", (tend - t0)/1e6)
                print("Samples received:", sr.ret, np.sum(self.buff)) # number of samples read or the error code

            buffs.append(self.buff[::self.nthin].copy())
            self.buff[:] = 0.

        # Get gain info
        #final_gain = sdr.getGain(SOAPY_SDR_RX, rx_chan)
        #rfgain = sdr.readSetting("rfgain_sel")
        #print("Gains:", final_gain, rfgain)
        #sdr.deactivateStream(rxStream) #stop streaming

        # Save output
        spectra = [np.abs(np.fft.fft(d*self.window))**2 for d in buffs] # goes through the buffer and ffts
        spectra = np.array(spectra)
        spectra = np.mean(spectra, axis=0) # average along time-axis
        spectra = np.fft.fftshift(spectra)
        return spectra
    
    def deactivate_stream(self):
        self.sdr.deactivateStream(self.rxStream) #stop streaming
        self.sdr.closeStream(self.rxStream)
        print('SDR Stream Deactivated')
        return
    

class Switches:
    def __init__(self, com_port, baud_rate, switch_dictionary, sleep_time):
        self.com_port, self.baud_rate = com_port, baud_rate
        self.switch_dict = switch_dictionary
        self.serial = serial.Serial(self.com_port, self.baud_rate)
        self.sleep_time = sleep_time
        pass

    def open(self):
        if self.serial is None:
            self.serial = serial.Serial(self.com_port, self.baud_rate)
        pass
    
    def set_switch_state(self, switch_cmd):
        self.open()
        cmd = self.switch_dict[switch_cmd]
        self.serial.write(cmd.encode())
        time.sleep(self.sleep_time)
        self.close()
        pass

    def close(self):
        if self.serial:
            self.serial.close()
        self.serial = None


class VNAController:
    def __init__(self, min_freq=55e6, max_freq = 85e6, n_int=10, out_of_band_freq=50e4):
        self.min_freq, self.max_freq = min_freq, max_freq
        self.n_int = n_int
        self.out_of_band_freq=out_of_band_freq
        vna = nanovna.NanoVNA(nanovna.getport())
        vna.open()
        vna.resume()
        vna.set_frequencies(start=self.min_freq, stop=self.max_freq)
        self.frequencies = vna.frequencies
        self.shift_out_of_band(vna)
        vna.pause()
        pass

    def shift_out_of_band(self, vna):
        vna.set_sweep(start=self.out_of_band_freq, stop=self.out_of_band_freq+50e4)
        vna.pause()
        pass

    def measure_s11(self, return_std=False, measure_receiver=False): #FIXME add in functionality for reducing power for receiver measurement
        vna = nanovna.NanoVNA(nanovna.getport())
        vna.open()
        vna.resume()
        vna.set_frequencies(start=self.min_freq, stop=self.max_freq)
        vna.set_sweep(start=self.min_freq, stop=self.max_freq)

        scans = [vna.scan() for i in np.arange(self.n_int)] # get scans
        s11s = [scan[0] for scan in scans] # get s11s

        s11s = np.array(s11s)
        s11_mean = np.mean(s11s, axis=0)
        

        self.shift_out_of_band(vna)
        
        if return_std:
            s11_std = np.std(s11s, axis=0)
            return s11_mean, s11_std
        else:
            return s11_mean

    def measure_SOL_calibrators(self, switches):
        switches.set_switch_state('vna_short') # set to observe short
        S = self.measure_s11()

        switches.set_switch_state('vna_open') # set to observe open
        O = self.measure_s11()

        switches.set_switch_state('vna_open') # set to observe open
        L = self.measure_s11()
        return S,O,L



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("observation_duration", help='Time of Observation [s]', type=float)
    parser.add_argument("averaging_time", help="Averaging Time per spectra [s]", type=float)
    parser.add_argument("-cf", "--centre_freq", help="Centre Frequency to set LO to [Hz]", type=float)
    parser.add_argument("-fl", "--fft_length", help="Length of Fourier Transform. Ensure 2^N for efficiency", type=int)
    parser.add_argument("-fw", "--fft_window", help="FFT window (Rectangular, Blackman, )", type=str, choices=['Rectangular, Blackman, BlackmanHarris'])
    parser.add_argument("-g", "--sdr_gain", help='Gain of SDR [dB]', type=int)
    parser.add_argument("-sr", "--sample_rate", help="Set samplerate/bandwidth of SDR [Hz]", type=float, choices=[10e6, 8e6, 6e6, 4e6,2e6])
    parser.add_argument("-sw", "--switching", help='Boolean for switch operation. True for switching')
    args = parser.parse_args()

    if args.centre_freq == None:
        centre_freq = 70e6
    else:
        centre_freq = args.centre_freq

    if args.fft_length == None:
        fft_length = 16384
    else:
        fft_length = int(args.fft_length)

    # Set up FFT Window
    if args.fft_window == None:
        fft_window = np.ones(shape=(fft_length,))
    elif args.fft_window == 'Blackman':
        fft_window = np.blackman(fft_length)
    elif args.fft_window == 'BlackmanHarris':
        fft_window = signal.windows.blackmanharris(M=fft_length)
    else:
        fft_window = np.ones(shape=(fft_length,))

    # SDR Gain
    if args.sdr_gain == None:
        gain = 36
    else:
        gain = int(args.sdr_gain) #FIXME add in function to check if gains are in list and to round (maybe add full list to the options)

    if args.sample_rate == None: # same for this
        sample_rate = 8e6
    else:
        sample_rate = args.sample_rate
    
    if args.switching == True or args.swiching == 'True': # prepare switching
        switching = True
    else:
        switching = False
    
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

    sdr.writeSetting("rfnotch_ctrl", "true") # set notches
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

    if switching:
        switch_states = []
    
    spectras = []
    gains = []
    times = []

    status = sdr.activateStream(rxStream) # start streaming
    tt0 = time.time()
    t_f = tt0 + observation_duration # define observing end time

    while tt0 < t_f:
        #status = sdr.activateStream(rxStream) #start streaming
        #num_samps = int(sdr.getStreamMTU(rxStream)) + 0
        buff = np.zeros((fft_length,), np.complex64) # set up buffer buffs for IQ samples
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
        print(f"    Saving PSD: Time Remaining:  {t_f-tt0}")
        spectra = []
        for i in range(len(buffs)):
            d = buffs[i]
            PSD = np.abs(np.fft.fftshift(np.fft.fft(d)))**2
            spectra.append(PSD)
        spectra = np.array(spectra)
        spectra = np.mean(spectra, axis=0)
        spectras.append(spectra)
        tt0 = time.time()
        times.append(tt0)
    
    

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
