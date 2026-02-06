
import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32 #SOAPY_SDR_ constants
import numpy as np


def acquire_data_from_sdrplay(sample_rate=8e6, centre_freq=70e6, enable_agc=False, gain=0, rfnotch=False, dabnotch=False):
    """
    
    """
    # Initialise SDR object
    sdr = SoapySDR.Device(dict(driver="sdrplay"))
    
    # Apply settings
    rx_chan = 0 # only one channel on RSP1A
    sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, sample_rate)
    sdr.setFrequency(SOAPY_SDR_RX, rx_chan, center_freq)
    sdr.setBandwidth(SOAPY_SDR_RX, rx_chan, int(sample_rate))
    sdr.setGainMode(SOAPY_SDR_RX, rx_chan, enable_agc)
    
    if not enable_agc:
        sdr.setGain(SOAPY_SDR_RX, rx_chan, gain)

    # Prepare to stream data
    rxStream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [rx_chan])

    # Status stuff
    print("hardware info", sdr.getHardwareInfo())
    status = sdr.activateStream(rxStream) #start streaming
    print("Stream MTU:", sdr.getStreamMTU(rxStream))
    print("Activate status:", status)
    print("Current gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan))
    print(sdr.listGains(SOAPY_SDR_RX, rx_chan))
    print(sdr.getBandwidth(SOAPY_SDR_RX, rx_chan))
    print(sdr.listAntennas(SOAPY_SDR_RX, rx_chan))
    print("")
    
    # Enable or disable notch filters
    sdr.writeSetting("rfnotch_ctrl", str(rfnotch).lower())
    sdr.writeSetting("dabnotch_ctrl", str(dabnotch).lower())

    print("RF gain idx:", sdr.readSetting("rfgain_sel"))
    sdr.deactivateStream(rxStream) # stop streaming
    
    
    
    
    nblocks = 1
    for n in range(nblocks):
        status = sdr.activateStream(rxStream) # start streaming
        num_samps = int(sdr.getStreamMTU(rxStream)) + 0
        buff = np.zeros((num_samps,), np.complex64)
        buffs = []
        gains = []

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
        sdr.deactivateStream(rxStream) # stop streaming

        # Save output
        tt0 = time.time()
        print("    Saving PSD")
        wfall = []
        for i in range(len(buffs)):
            d = buffs[i]
            PSD = 10*np.log10(np.abs(np.fft.fftshift(np.fft.fft(d)))**2)
            wfall.append(PSD)
        wfall = np.array(wfall)
        np.save("data_psd_%d" % time.time(), wfall)
        print("    Saving PSD took %5.2f sec" % (time.time() - tt0))

    # Close the stream
    #sdr.deactivateStream(rxStream) #stop streaming
    sdr.closeStream(rxStream)


