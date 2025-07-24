from observe_func import *
import argparse
import os
import time

# initalise and take the arg_parse

# define switch directory here....
SWITCH_DICTIONARY = {'vna_short':'t2t2e5'} # fill this out
# switch sleep time ...
SWITCH_SLEEP_TIME = 0.1

VNA_N_INT = 10

SAVE_PATH = 'Observation_Data'

DATA_SPLIT_TIME = 60*60

def switching_observing(sample_rate,
                        centre_frequency,
                        integration_time,
                        fft_length,
                        window,
                        gain,
                        com_port,
                        baud_rate,
                        switch_dictionary,
                        switch_sleep_time,
                        vna_n_int,
                        save_path,
                        observation_length,
                        switch_duration):
    
    SDR = SDRObserver(sample_rate=sample_rate,centre_frequency=centre_frequency,
                      integration_time=integration_time, fft_length=fft_length,window=window,
                      gain=gain)
    
    switches = Switches(com_port=com_port, baud_rate=baud_rate, switch_dictionary=switch_dictionary,
                        sleep_time=switch_sleep_time)

    VNA = VNAController(min_freq=SDR.freq_channels_mhz[0]*1e6 - 2e6,
                        max_freq=SDR.freq_channels_mhz[-1]*1e6 + 2e6,
                        n_int=vna_n_int)

    

    dicke_switch_list = ['vna_load',
                         'vna_ns',
                         'vna_ant',
                         'vna_receiver']
    
    switch_source_list = ['receiver_load',
                          'reeiver_ns',
                          'receiver_ant']
    
    # initial measure each source
    s11_measurements = []
    for st in dicke_switch_list:
        switches.set_switch_state(st)
        s11 = VNA.measure_s11()
        s11_measurements.append(s11)
    

    # set up saving directory if one doesn't exit
    if not os.path.exists(path=save_path):
        os.makedirs(save_path)
        print('Save Path Created')
    else:
        print('Save Path Set Up')
    save_path = save_path+'/'

    t_save = int(time.time())
    t_init = t_save
    t_end_obs = t_init + observation_length

    timer = time.time()

    with h5py.File(f"{save_path}data_{t_save}.hd5f", mode='a') as file:
        while timer <  t_end_obs:
            timer = time.time()
            t_group_init = int(time.time())
            t_group_end_time = t_group_init + DATA_SPLIT_TIME

            obs_group = file.create_group(f"{t_group_init}")
            
            vna_measurement_group = obs_group.create_group('VNA_Measurements')

            # measure SOL calibrators
            s, o, l = VNA.measure_SOL_calibrators(switches=switches)

            vna_measurement_group.create_dataset('Short_Calibration', data=s, dtype=s.dtype)
            vna_measurement_group.create_dataset('Open_Calibration', data=o, dtype=o.dtype)
            vna_measurement_group.create_dataset('Load_Calibration', data=l, dtype=l.dtype)

            for target_string in dicke_switch_list:
                switches.set_switch_state(target_string)
                s11 = VNA.measure_s11()
                vna_measurement_group.create_dataset(target_string, data=s11, dtype=s11.dtype) # measure the sources in the switch list with VNA
            
            
            spectra_measurement_group = obs_group.create_group('SDR_Measurements')

            # initial measurements
            # take and save the vna measurements
            spectra_list = []
            spectra_times = []


            switch_states = []
            switch_times = []
            switch_index = 0
            
            switch_target = switch_source_list[switch_index]
            switches.set_switch_state(switch_target)
            switch_over_time = time.time()+switch_duration

            SDR.initialise()
            while timer <  t_group_end_time and timer < t_end_obs:
                
                while timer  <  switch_over_time:
                    timer = time.time()
                    spectrum = SDR.get_averaged_spectra()
                    spectra_list.append(spectrum)
                    spectra_times.append(timer)
                
                switch_index += 1
                if switch_index >= len(switch_source_list):
                    switch_index = 0

                switch_target = switch_source_list[switch_index]
                switch_over_time = time.time() + switch_duration
                switch_states.append(switch_target)
                switch_times.append(timer)

            spectra_list = np.array(spectra_list)
            spectra_times = np.array(spectra_times)
            spectra_measurement_group.create_dataset('SDR_Spectra', data=spectra_list, dtype=spectra_list.dtype)
            spectra_measurement_group.create_dataset('SDR_Spectra_Times', data=spectra_times, dtype=spectra_times.dtype)
            
            print(f'Saved Group {t_group_init}')
        
    print(f'Saved hd5f file at {save_path}data_{t_save}.hd5f')

    print('Observation Done')

            
                # take spectra measurements
    


def no_switching_observing(sample_rate, #FIXME
                        centre_frequency,
                        integration_time,
                        fft_length,
                        window,
                        gain,
                        com_port,
                        baud_rate,
                        switch_dictionary,
                        switch_sleep_time,
                        vna_n_int,
                        save_path,
                        observation_length):
    
    SDR = SDRObserver(sample_rate=sample_rate,centre_frequency=centre_frequency,
                      integration_time=integration_time, fft_length=fft_length,window=window,
                      gain=gain)
    
    switches = Switches(com_port=com_port, baud_rate=baud_rate, switch_dictionary=switch_dictionary,
                        sleep_time=switch_sleep_time)

    VNA = VNAController(min_freq=SDR.freq_channels_mhz[0]*1e6 - 2e6,
                        max_freq=SDR.freq_channels_mhz[-1]*1e6 + 2e6,
                        n_int=vna_n_int)

    

    dicke_switch_list = ['vna_load',
                         'vna_ns',
                         'vna_ant',
                         'vna_receiver']
    
    # initial measure each source
    s11_measurements = []
    for st in dicke_switch_list:
        switches.set_switch_state(st)
        s11 = VNA.measure_s11()
        s11_measurements.append(s11)
    

    # set up saving directory if one doesn't exit
    if not os.path.exists(path=save_path):
        os.makedirs(save_path)
        print('Save Path Created')
    else:
        print('Save Path Set Up')
    save_path = save_path+'/'

    t_save = int(time.time())
    t_init = t_save
    t_end_obs = t_init + observation_length

    timer = time.time()

    with h5py.File(f"{save_path}data_{t_save}.hd5f", mode='a') as file:
        while timer <  t_end_obs:
            timer = time.time()
            t_group_init = int(time.time())
            t_group_end_time = t_group_init + DATA_SPLIT_TIME

            obs_group = file.create_group(f"{t_group_init}")
            
            vna_measurement_group = obs_group.create_group('VNA_Measurements')

            # measure SOL calibrators
            s, o, l = VNA.measure_SOL_calibrators(switches=switches)

            vna_measurement_group.create_dataset('Short_Calibration', data=s, dtype=s.dtype)
            vna_measurement_group.create_dataset('Open_Calibration', data=o, dtype=o.dtype)
            vna_measurement_group.create_dataset('Load_Calibration', data=l, dtype=l.dtype)

            for target_string in dicke_switch_list:
                switches.set_switch_state(target_string)
                s11 = VNA.measure_s11()
                vna_measurement_group.create_dataset(target_string, data=s11, dtype=s11.dtype) # measure the sources in the switch list with VNA
            
            
            spectra_measurement_group = obs_group.create_group('SDR_Measurements')

            # initial measurements
            # take and save the vna measurements
            spectra_list = []
            spectra_times = []
            SDR.initialise()
            while timer <  t_group_end_time and timer < t_end_obs:
                timer = time.time()
                spectrum = SDR.get_averaged_spectra()
                spectra_list.append(spectrum)
                spectra_times.append(timer)

            spectra_list = np.array(spectra_list)
            spectra_times = np.array(spectra_times)
            spectra_measurement_group.create_dataset('SDR_Spectra', data=spectra_list, dtype=spectra_list.dtype)
            spectra_measurement_group.create_dataset('SDR_Spectra_Times', data=spectra_times, dtype=spectra_times.dtype)
            
            print(f'Saved Group {t_group_init}')
        
    print(f'Saved hd5f file at {save_path}data_{t_save}.hd5f')

    print('Observation Done')



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
    # ----------------------- parsed arguments ----------

    if switching:
        switching_observing()
    else:
        pass
    
