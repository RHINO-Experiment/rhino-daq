from observe_func import *
import argparse
import os
import time

# initalise and take the arg_parse

# define switch directory here....
SWITCH_DICTIONARY = {'vna_short':'t1t1e5',
                     'vna_open':'t1t1e6',
                     'vna_load':'t1t1e7',
                     'vna_receiver':'t2t2e8',
                     'vna_ns':'t1t1e3',
                     'vna_obsload':'t1t1e2',
                     'vna_ant':'t1t1e4',
                     'receiver_load':'t2t2e2',
                     'receiver_ns':'t2t2e3',
                     'receiver_ant':'t2t2e4'} # fill this out


# switch sleep time ...
SWITCH_SLEEP_TIME = 1

VNA_N_INT = 20

SAVE_PATH = 'Observation_Data'

DATA_SPLIT_TIME = 60*60

ARDUINO_COM_PORT = '/dev/ttyACM0'
ARDUINO_BAUD_RATE = 9600

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
    print('Observation Start ---')
    SDR = SDRObserver(sample_rate=sample_rate,centre_frequency=centre_frequency,
                      integration_time=integration_time, fft_length=fft_length,window=window,
                      gain=gain)

    VNA = VNAController(min_freq=SDR.freq_channels_mhz[0]*1e6 - 1e6,
                        max_freq=SDR.freq_channels_mhz[-1]*1e6 + 1e6,
                        n_int=vna_n_int)

    
    temp_sens_switches = Arduino(n_sens=2, com_port=com_port, baud_rate=baud_rate, switch_dictionary=switch_dictionary,
                                 sleep_time=switch_sleep_time)

    vna_switch_list = ['vna_obsload',
                         'vna_ns',
                         'vna_ant',
                         'vna_receiver']
    
    switch_source_list = ['receiver_load',
                          'receiver_ns',
                          'receiver_ant']

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

            temp_group = obs_group.create_group('Temperature_Measurements')

            # measure SOL calibrators
            s, o, l = VNA.measure_SOL_calibrators(switches=temp_sens_switches)

            vna_freqs = np.array(VNA.frequencies)

            vna_measurement_group.create_dataset('Short_Calibration', data=s, dtype=s.dtype)
            vna_measurement_group.create_dataset('Open_Calibration', data=o, dtype=o.dtype)
            vna_measurement_group.create_dataset('Load_Calibration', data=l, dtype=l.dtype)
            vna_measurement_group.create_dataset('VNA_Frequencies', data=vna_freqs,
                                                 dtype=vna_freqs.dtype)

            print('SOL Calibration Complete')
            for target_string in vna_switch_list:
                temp_sens_switches.set_switch_state(target_string)
                s11 = VNA.measure_s11()
                vna_measurement_group.create_dataset(target_string, data=s11, dtype=s11.dtype) # measure the sources in the switch list with VNA
            
            
            spectra_measurement_group = obs_group.create_group('SDR_Measurements')

            # initial measurements
            # take and save the vna measurements
            spectra_list = []
            spectra_times = []

            temperatures = []
            temperature_times = []

            switch_states = []
            switch_times = []
            switch_index = 0

            SDR.start_stream()
            while timer <  t_group_end_time and timer < t_end_obs:
                switch_target = switch_source_list[switch_index]
                temp_sens_switches.set_switch_state(switch_target)
                print('----Switch Target : ', switch_target, '----')
                switch_over_time = time.time() + switch_duration

                switch_states.append(switch_target)
                switch_times.append(timer)

                while timer  <  switch_over_time:
                    timer = time.time()
                    spectrum = SDR.get_averaged_spectra()
                    spectra_list.append(spectrum)
                    spectra_times.append(timer) # append averaged spectrum to list
                    temps = temp_sens_switches.read_temp()
                    temperatures.append(temps) # read temperatures and add to list
                
                switch_index += 1
                if switch_index >= len(switch_source_list):
                    switch_index = 0


            SDR.deactivate_stream()
            spectra_list = np.array(spectra_list)
            spectra_times = np.array(spectra_times)

            temperatures = np.array(temperatures)
            temperature_times = spectra_times

            sdr_freqs = np.array(SDR.freq_channels_mhz)

            spectra_measurement_group.create_dataset('SDR_Spectra', data=spectra_list, dtype=spectra_list.dtype)
            spectra_measurement_group.create_dataset('SDR_Times', data=spectra_times, dtype=spectra_times.dtype)
            spectra_measurement_group.create_dataset('SDR_Frequencies', data=sdr_freqs, dtype=sdr_freqs.dtype)

            temp_group.create_dataset('Temperatures', data=temperatures, dtype=temperatures.dtype)
            temp_group.create_dataset('Times', data=temperature_times, dtype=temperature_times.dtype)
            
            switch_group = obs_group.create_group('Switches')
            switch_times = np.array(switch_times)
            switch_group.create_dataset('Switch_States', data=np.array(switch_states, dtype='S'))
            switch_group.create_dataset('Switch_Times', data=switch_times, dtype=switch_times.dtype)


            print(f'Saved Group {t_group_init}')
        
    print(f'Saved hd5f file at {save_path}data_{t_save}.hd5f')

    print('Observation Done')

            
                # take spectra measurements
    
def SDR_only_observing(sample_rate, #FIXME
                        centre_frequency,
                        integration_time,
                        fft_length,
                        window,
                        gain,
                        save_path,
                        observation_length):
    
    SDR = SDRObserver(sample_rate=sample_rate,centre_frequency=centre_frequency,
                      integration_time=integration_time, fft_length=fft_length,window=window,
                      gain=gain)
    

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

            spectra_measurement_group = obs_group.create_group('SDR_Measurements')

            # initial measurements
            # take and save the vna measurements
            spectra_list = []
            spectra_times = []
            SDR.start_stream()
            while timer <  t_group_end_time and timer < t_end_obs:
                timer = time.time()
                spectrum = SDR.get_averaged_spectra()
                spectra_list.append(spectrum)
                spectra_times.append(timer)

            spectra_list = np.array(spectra_list)
            spectra_times = np.array(spectra_times)
            sdr_freqs = np.array(SDR.freq_channels_mhz)

            spectra_measurement_group.create_dataset('SDR_Spectra', data=spectra_list, dtype=spectra_list.dtype)
            spectra_measurement_group.create_dataset('SDR_Times', data=spectra_times, dtype=spectra_times.dtype)
            spectra_measurement_group.create_dataset('SDR_Frequencies', data=sdr_freqs, dtype=sdr_freqs.dtype)
            
            print(f'Saved Group {t_group_init}')
    
    SDR.deactivate_stream()
    print(f'Saved hd5f file at {save_path}data_{t_save}.hd5f')

    print('Observation Done')




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
            SDR.start_stream()
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
    parser.add_argument("-swd", "--switch_duration", help='Observation Time Per Switch')
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
        fft_window = "Rectangular"
    else:
        fft_window = str(args.fft_window)

    # SDR Gain
    if args.sdr_gain == None:
        gain = 36
    else:
        gain = int(args.sdr_gain) #FIXME add in function to check if gains are in list and to round (maybe add full list to the options)

    if args.sample_rate == None: # same for this
        sample_rate = 8e6
    else:
        sample_rate = args.sample_rate
    
    #if args.switching is None:
    #    switching = False
    #elif args.switching == True or args.swiching == 'True': # prepare switching
    #    switching = True
    #else:
    #    switching = False

    if args.switch_duration is None:
        switch_duration = 20
    else:
        switch_duration = float(args.switch_duration)


    integration_time = float(args.averaging_time)
    observation_length = float(args.observation_duration)

    switching = True

    # ----------------------- parsed arguments ----------

    if switching:
        switching_observing(sample_rate=sample_rate,
                            centre_frequency=centre_freq,
                            integration_time=integration_time,
                            fft_length=fft_length,
                            window=fft_window,
                            gain=gain,
                            com_port=ARDUINO_COM_PORT,
                            baud_rate=ARDUINO_BAUD_RATE,
                            switch_dictionary=SWITCH_DICTIONARY,
                            switch_sleep_time=SWITCH_SLEEP_TIME,
                            vna_n_int=VNA_N_INT,
                            save_path=SAVE_PATH, observation_length=observation_length,
                            switch_duration=switch_duration)
    else:
        SDR_only_observing(sample_rate=sample_rate,
                           centre_frequency=centre_freq,
                           integration_time=integration_time,
                           fft_length=fft_length, window=fft_window, gain=gain, save_path=SAVE_PATH,
                           observation_length=observation_length)
        pass

    
