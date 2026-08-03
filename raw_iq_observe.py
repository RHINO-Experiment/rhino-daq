"""
Script for getting raw IQ samples from the receiver.
"""

import numpy as np
import SoapySDR
from SoapySDR import * #SOAPY_SDR_ constants
import time
from src.arduino_funcs import Arduino
import argparse
import yaml

def initialise_sdr_and_sample(nsamps,
                              nStream,
                              sdrDriver,
                              sdrLabel,
                              bandwidth,
                              centre_frequency,
                              sdrRFGR,
                              sdrIFGR,
                              delay=10,
                              ):
    print('nsamp', nsamps)
    rx_chan = 0 # only 1 channel on RSP1A
    sdr = SoapySDR.Device(dict(driver=sdrDriver, label=sdrLabel))
    sdr.setSampleRate(SOAPY_SDR_RX, rx_chan, bandwidth)
    sdr.setFrequency(SOAPY_SDR_RX, rx_chan, centre_frequency)
    sdr.setBandwidth(SOAPY_SDR_RX, rx_chan, int(bandwidth)) # intialises the SDR with settings

    print("SDR:","hardware info", sdr.getHardwareInfo())

    sdr.setGainMode(SOAPY_SDR_RX, rx_chan, False) # turn ON AGC

    
    sdr.setGain(SOAPY_SDR_RX, rx_chan, "RFGR", sdrRFGR) # set RF gain
    sdr.setGain(SOAPY_SDR_RX, rx_chan, "IFGR", sdrIFGR) # set IF gain

    print("Current RF Gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan, "RFGR"))
    print("Current IF Gain:", sdr.getGain(SOAPY_SDR_RX, rx_chan, "IFGR"))

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
    #sdr.writeSetting("biasT_ctrl", "false")

    sdr.writeSetting(SOAPY_SDR_RX, rx_chan, "rfnotch_ctrl", "true")
    sdr.writeSetting(SOAPY_SDR_RX, rx_chan, "dabnotch_ctrl", "true")

    # Enable RF notch filters

    sdr.writeSetting(SOAPY_SDR_RX, rx_chan,"fmmnotch_ctrl", "true")  # FM broadcast notch

    print("RF gain idx:", sdr.readSetting("rfgain_sel"))

    #final_gain = 0 # FIXME
    sdr.deactivateStream(rxStream) #stop streaming

    if sdr.getStreamMTU(rxStream) < nStream:
        nStream = sdr.getStreamMTU(rxStream)

    time.sleep(delay)

    sdr.activateStream(rxStream)

    buff = np.zeros((nStream,), np.complex64)

    samples = []

    buffs = []
    for i in range(nsamps):
        # Receive some samples
        t0 = time.perf_counter_ns()
        sr = sdr.readStream(rxStream, [buff], len(buff), timeoutUs=int(100e3))
        tend = time.perf_counter_ns()

        if int(sr.ret) < 0:
            print("Error status encountered: %d (%d)" % (sr.ret, i))

        if i % 500 == 0:
            print("Time diff (ms):", (tend - t0)/1e6)
            print("Samples received:", sr.ret, np.sum(buff)) # number of samples read or the error code

        buffs.append(buff[::1].copy())
        buff[:] = 0.

        # Save output

    iq_buffs = np.array(buffs)
    
    sdr.deactivateStream(rxStream) #stop streaming
    sdr.closeStream(rxStream)

    return iq_buffs



def main():
    parser = argparse.ArgumentParser(description='Raw IQ Sample Accumalator')

    parser.add_argument('--target', type=str,
                        default='antenna')

    
    parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    
    parser.add_argument('--nblocks', type=int,
                        default=200)

    parser.add_argument('--nstream', type=int,
                        default=2**18)

    parser.add_argument('--sdr_delay', default=10, type=float)

    parser.add_argument('--savedir', type=str,
                        default='/media/usb0/rhino-data/iq_tests')

    args = parser.parse_args()
    yaml_path = args.yaml

    with open(yaml_path,'r') as f:
            obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
            pass

    arduino_object = Arduino(n__temp_sens=obs_config['arduino']['temperatureMonitoring']['nProbes'],
                             com_port=obs_config['arduino']['comPort'],
                             baud_rate=obs_config['arduino']['baudRate'],
                             switch_dictionary=obs_config['arduino']['switchDictionary'])
    
    arduino_object.set_switch_state(args.target)
    print('Target Set')


    samples = initialise_sdr_and_sample(nsamps=args.nblocks,
                                        nStream=args.nstream,
                                        sdrDriver=obs_config['sdr']['sdrDriver'],
                                        sdrLabel=obs_config['sdr']['sdrLabel'],
                                        bandwidth=obs_config['sdr']['bandwidth'],
                                        centre_frequency=obs_config['sdr']['centreFrequency'],
                                        sdrIFGR=obs_config['sdr']['sdrIFGR'],
                                        sdrRFGR=obs_config['sdr']['sdrRFGR'],
                                        delay=args.sdr_delay)
    
    np.savez(file=f'{args.savedir}/{args.target}.npz',
             iq_samples=samples,
             sample_rate=obs_config['sdr']['bandwidth'])

    print('Done')


if __name__ == "__main__":
     main()