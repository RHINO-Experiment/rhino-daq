#!/usr/bin/env python3


import SoapySDR
from SoapySDR import * #SOAPY_SDR_ constants
import numpy as np
import matplotlib.pyplot as plt
import sys, time

sample_rate = 8e6
center_freq = 70.3e6
gain = 36
nthin = 1
nsamp = 400
rx_chan = 0 # only 1 channel on RSP1A
sdr = SoapySDR.Device(dict(driver="sdrplay"))
sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, sample_rate)
sdr.setFrequency(SOAPY_SDR_RX, rx_chan, center_freq)
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

#print("Setting:", sdr.readSetting("rfnotch_ctrl"))

#print("Time:", SOAPY_SDR_HAS_TIME)
#print("Ref. clock rate:", sdr.getReferenceClockRate())
#sys.exit(0)
nblocks = 1
for n in range(nblocks):
    status = sdr.activateStream(rxStream) #start streaming
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
    sdr.deactivateStream(rxStream) #stop streaming

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


#print(dir(sdr))
print(sdr.listGains(SOAPY_SDR_RX, rx_chan))
print(sdr.getBandwidth(SOAPY_SDR_RX, rx_chan))
print(sdr.listAntennas(SOAPY_SDR_RX, rx_chan))

#import sys
#sys.exit(0)
#####

# Plot result
#print(buff[0:20])
#plt.figure(0)
#plt.plot(np.real(buff), '.')
#plt.plot(np.imag(buff), '.')

plt.figure(0)
# FIXME
f = np.linspace(-sample_rate/2/1e6, sample_rate/2/1e6, num_samps)[::nthin]
wfall = []
for i in range(len(buffs)):
    PSD = 10*np.log10(np.abs(np.fft.fftshift(np.fft.fft(buffs[i])))**2)
    wfall.append(PSD)
wfall = np.array(wfall)
print("Data shape:", wfall.shape)

#plt.plot(f, PSD, alpha=0.4, label="gain %s" % gains[i])
plt.matshow(wfall, fignum=False, aspect='auto', 
            extent=[center_freq/1e6 + f.min(), 
                    center_freq/1e6 + f.max(), 
                    t_all_end - t_all_start, 
                    0.])
plt.colorbar()
#plt.legend(loc='upper right')

plt.figure(1)
plt.plot(f + center_freq/1e6, np.mean(wfall, axis=0))
plt.grid()
#plt.title("Gain: %s | gain idx: %s | duration: %5.3f sec" % (final_gain, rfgain, t_all_end - t_all_start))
plt.ylim((-40., 40.))

plt.show()
#plt.savefig("sdrplay_samples.png")
