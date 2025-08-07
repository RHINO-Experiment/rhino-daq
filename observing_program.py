from observe_func import *
import argparse
import os
import time
from multiprocessing import Process, Queue


# initalise and take the arg_parse

# define switch directory here....
SWITCH_DICTIONARY = {'vna_short':'t1t1e5',
                     'vna_open':'t1t1e6',
                     'vna_load':'t1t1e7',
                     'vna_receiver':'t2t2e8',
                     'vna_ns':'t1t1e3',
                     'vna_obsload':'t1t1e2',
                     'vna_ant':'t1t1e4',
                     'receiver_obsload':'t2t2e2',
                     'receiver_ns':'t2t2e3',
                     'receiver_ant':'t2t2e4',
                     'receiver_short':'t2t2e5',
                     'receiver_open':'t2t2e6',
                     'receiver_load':'t2t2e7',
                     'receiver_longcable':'t2t2e1'} # fill this out


# switch sleep time ...
SWITCH_SLEEP_TIME = 0.1

NOISE_WAVE_CAL_SWITCH_TIME = 60

VNA_N_INT = 20

SAVE_PATH = 'Observation_Data'

TEMP_CACHE = 'Temp_Cache'

DATA_SPLIT_TIME = 60*60

ARDUINO_COM_PORT = '/dev/ttyACM0'

ARDUINO_BAUD_RATE = 9600

HD5F_FILE_SWITCH_PERIOD = 60*60*24 # 1 DAY

def continous_SDR_observing(sdr, observation_length, file, obs_group_string, group_name, temp_cache):
    t = time.time()
    sdr.start_stream()
    spectra = []
    times = []
    t_f = t + observation_length
    while t < t_f:
        s = sdr.get_averaged_spectra()
        t = time.time()
        spectra.append(s)
        times.append(t)
    sdr.deactivate_stream()
    spectra = np.array(spectra)
    times = np.array(times)
    spectra_freqs = sdr.freq_channels_mhz

    np.save(f'{temp_cache}SDR_Spectra.npy', spectra)
    np.save(f'{temp_cache}SDR_Times.npy', times)
    np.save(f'{temp_cache}SDR_Freqs.npy', spectra_freqs)
    #print('SDR Prepare To Put into queue')
    #q.put(('SDR', (spectra, times, spectra_freqs)))
    #print('SDR Has .put succesfully into queue')
    #obs_group = file[obs_group_string]
    #sdr_group = obs_group.create_group(group_name)
    #sdr_group.create_dataset('SDR_Spectra', data=spectra, dtype=spectra.dtype)
    #sdr_group.create_dataset('SDR_Times', data=times, dtype=times.dtype)
    #sdr_group.create_dataset('SDR_Freqs', data=spectra_freqs, dtype=spectra_freqs.dtype)
    print('SDR Group Saved Into Cache')


def continous_arduino_operation(arduino, observation_length, switch_list, switch_duration, file,obs_group_string, group_name, temp_cache):
    t = time.time()
    temperatures = []
    temperature_times = []
    switch_states = []
    switch_times = []

    t_f = t + observation_length
    switch_target = switch_list[0]
    switch_index = 0
    while t < t_f:
        arduino.set_switch_state(switch_target)
        t = time.time()
        t_switch = t + switch_duration
        switch_states.append(switch_target)
        switch_times.append(t)

        while t < t_switch and t < t_f:
            t = time.time()
            temp = arduino.read_temp()
            temperatures.append(temp)
            temperature_times.append(t)
            time.sleep(1)
        switch_index += 1
        if switch_index >= len(switch_list):
            switch_index = 0
        switch_target = switch_list[switch_index]
    
    temperatures = np.array(temperatures)
    temperature_times = np.array(temperature_times)
    switch_states = np.array(switch_states, dtype='S')
    switch_times = np.array(switch_times)

    np.save(f'{temp_cache}Temperatures.npy', temperatures)
    np.save(f'{temp_cache}Temperature_Times.npy', temperature_times)
    np.save(f'{temp_cache}Switch_States.npy', switch_states)
    np.save(f'{temp_cache}Switch_Times.npy', switch_times)

    print('Arduino Data Saved Into Cache')

    #obs_group = file[obs_group_string]
    #arduino_group = obs_group.create_group(group_name)
    #arduino_group.create_dataset('Switch_States', data=switch_states, dtype=switch_states.dtype)
    #arduino_group.create_dataset('Switch_Times', data=switch_times, dtype=switch_times.dtype)
    #arduino_group.create_dataset('Tempertures', data=temperatures, dtype=temperatures.dtype)
    #arduino_group.create_dataset('Temperature_Times', data=temperature_times, dtype=temperature_times.dtype)
    #print(f'Saved {group_name} Variables')

    #q.put(('Arduino', (temperatures, temperature_times, switch_states, switch_times)))
        
def predefined_arduino_observing(arduino, switchtime, switch_list, file, obs_group_string, group_name, temp_cache):
    switch_states = []
    switch_times = []
    temperatures = []
    temperature_times = []

    for switch in switch_list:
        t = time.time()
        arduino.set_switch_state(switch)
        switch_states.append(switch)
        switch_times.append(t)
        t_switch = t + switchtime # define when to change switch
        while t < t_switch:
            t = time.time()
            temperatures.append(arduino.read_temp())
            temperature_times.append(t)
            time.sleep(1)
    print('Arduino finished')
    switch_states = np.array(switch_states, dtype='S')
    switch_times = np.array(switch_times)
    temperatures = np.array(temperatures)
    temperature_times = np.array(temperature_times)

    np.save(f'{temp_cache}Temperatures.npy', temperatures)
    np.save(f'{temp_cache}Temperature_Times.npy', temperature_times)
    np.save(f'{temp_cache}Switch_States.npy', switch_states)
    np.save(f'{temp_cache}Switch_Times.npy', switch_times)

    print('Arduino Data Saved Into Cache')
    #print('Arduino Prepare to put..')
    #q.put(('Arduino', (temperatures, temperature_times, switch_states, switch_times)))
    #print('Arduino Has .put succesfully into queue')
    #obs_group = file[obs_group_string]
    #arduino_group = obs_group.create_group(group_name)
    #arduino_group.create_dataset('Switch_States', data=switch_states, dtype=switch_states.dtype)
    #arduino_group.create_dataset('Switch_Times', data=switch_times, dtype=switch_times.dtype)
    #arduino_group.create_dataset('Tempertures', data=temperatures, dtype=temperatures.dtype)
    #arduino_group.create_dataset('Temperature_Times', data=temperature_times, dtype=temperature_times.dtype)
    #print(f'Saved {group_name} Variables')


def run_simultaneous_obs(sdr,
                         arduino,
                         switch_list,
                         switch_duration, file, obs_group_string, sdr_group_name, arduino_group_name,
                         observation_length=DATA_SPLIT_TIME,
                         continous=True,
                         temp_cache=TEMP_CACHE+'/'):
    #q = Queue()
    #r = Queue()

    if continous:
        sdr_process = Process(target=continous_SDR_observing,
                              args=(sdr,
                                    observation_length,file,obs_group_string, sdr_group_name, temp_cache))
        arduino_process = Process(target=continous_arduino_operation,
                                  args=(arduino,
                                        observation_length,
                                        switch_list,
                                        switch_duration, file,
                                        obs_group_string, arduino_group_name, temp_cache))
    else:
        observation_length = switch_duration * len(switch_list)
        sdr_process = Process(target=continous_SDR_observing,
                              args=(sdr,
                                    observation_length, file ,
                                    obs_group_string,
                                    sdr_group_name, temp_cache)) 
        arduino_process = Process(target=predefined_arduino_observing,
                                  args=(arduino,
                                        switch_duration,
                                        switch_list, file,
                                        obs_group_string, arduino_group_name, temp_cache))
    
    sdr_process.start()
    arduino_process.start()

    #q_results = {}
    #while not q.empty():
    #    func_name, value = q.get()
    #    print('func_name = ', func_name)
    #    q_results[func_name] = value

    #r_results = {}
    #while not q.empty():
    #    func_name, value = r.get()
    #    print('func_name = ', func_name)
    #    r_results[func_name] = value


    sdr_process.join()
    arduino_process.join()


    print('Processes Rejoined Successfully')

    #sdr_results = q_results['SDR'] # tupple
    #print('sdr_results', sdr_results)
    #spectra, spectra_times, spectra_freqs = sdr_results

    #arduino_results = r_results['Arduino']
    #print('arduino results', arduino_results)
    #temperatures, temperature_times, switch_states, switch_times = arduino_results

    #result_dict = {'Spectra':spectra,
    #               'Spectra_Times':spectra_times,
     #              'Spectra_Freqs':spectra_freqs,
      #             'Temperatures':temperatures,
       #            'Temperature_Times':temperature_times,
        #           'Switch_States':switch_states,
         #          'Switch_Times':switch_times}
    #return result_dict    

def switching_observing_mp(sample_rate,
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
                           cache_path,
                           observation_length,
                           switch_duration):
    print('Observation Start ---')
    SDR = SDRObserver(sample_rate=sample_rate,centre_frequency=centre_frequency,
                      integration_time=integration_time, fft_length=fft_length,window=window,
                      gain=gain)

    VNA = VNAController(min_freq=SDR.freq_channels_mhz[0]*1e6 - 1e6,
                        max_freq=SDR.freq_channels_mhz[-1]*1e6 + 1e6,
                        n_int=vna_n_int, out_of_band_freq=2e9)

    temp_sens_switches = Arduino(n_sens=2, com_port=com_port, baud_rate=baud_rate, switch_dictionary=switch_dictionary,
                                 sleep_time=switch_sleep_time)

    vna_switch_list = ['vna_obsload',
                         'vna_ns',
                         'vna_ant',
                         'vna_receiver']
    
    switch_source_list = ['receiver_obsload',
                          'receiver_ns',
                          'receiver_ant']
    
    noise_wave_cal_list = ['receiver_short',
                           'receiver_open',
                           'receiver_load',
                           'receiver_longcable']

    # set up saving directory if one doesn't exit
    if not os.path.exists(path=save_path):
        os.makedirs(save_path)
        print('Save Path Created')
    else:
        print('Save Path Already Set Up')
    save_path = save_path+'/'

    # set up saving directory if one doesn't exit
    if not os.path.exists(path=cache_path):
        os.makedirs(cache_path)
        print('Save Path Created')
    else:
        print('Cache Path Already Set Up')
    cache_path = cache_path+'/'

    t_save = int(time.time())
    t_init = t_save
    t_end_obs = t_init + observation_length + len(noise_wave_cal_list) * NOISE_WAVE_CAL_SWITCH_TIME

    timer = time.time()

    file_switch_over = timer + HD5F_FILE_SWITCH_PERIOD
    while timer < t_end_obs:
        
        file_switch_over = timer + HD5F_FILE_SWITCH_PERIOD

        while timer < file_switch_over and timer <  t_end_obs:

            with h5py.File(f"{save_path}data_{t_save}.hd5f", mode='a') as file:
                while timer <  t_end_obs and timer < file_switch_over:
                    timer = time.time()
                    t_group_init = int(time.time())
                    if t_end_obs < t_group_init+DATA_SPLIT_TIME:
                        duration = np.abs(t_end_obs - timer)
                    else:
                        duration = DATA_SPLIT_TIME
                    obs_group_string = f"{t_group_init}"
                    obs_group = file.create_group(obs_group_string)
            
                    vna_measurement_group = obs_group.create_group('VNA_Measurements')


                    # measure SOL calibrators
                    s, o, l = VNA.measure_SOL_calibrators(switches=temp_sens_switches)

                    vna_freqs = np.array(VNA.frequencies)

                    vna_measurement_group.create_dataset('Short_Calibration', data=s, dtype=s.dtype)
                    vna_measurement_group.create_dataset('Open_Calibration', data=o, dtype=o.dtype)
                    vna_measurement_group.create_dataset('Load_Calibration', data=l, dtype=l.dtype)
                    vna_measurement_group.create_dataset('VNA_Frequencies', data=vna_freqs, dtype=vna_freqs.dtype)

                    print('SOL Calibration Complete')
                    for target_string in vna_switch_list:
                        temp_sens_switches.set_switch_state(target_string)
                        s11 = VNA.measure_s11()
                        vna_measurement_group.create_dataset(target_string, data=s11, dtype=s11.dtype) # measure the sources in the switch list with VNA
                
                    print('VNA Measurements Complete ...')
                

                    print('Measuring Noise-Wave Calibrators')

                    run_simultaneous_obs(sdr=SDR,
                                         arduino=temp_sens_switches,
                                         switch_list=noise_wave_cal_list,
                                         switch_duration=NOISE_WAVE_CAL_SWITCH_TIME,
                                         file=file,
                                         obs_group_string=obs_group_string, sdr_group_name='NW_SDR',
                                         arduino_group_name='NW_ARDUINO',
                                         observation_length=len(noise_wave_cal_list)*NOISE_WAVE_CAL_SWITCH_TIME,
                                         continous=False)
                    
                    nw_group = obs_group.create_group('NoiseWaveMeasurements')

                    temperatures = np.load(f'{cache_path}Temperatures.npy')
                    temperature_times = np.load(f'{cache_path}Temperature_Times.npy')
                    switch_states_string = np.load(f'{cache_path}Switch_States.npy')
                    switch_times = np.load(f'{cache_path}Switch_Times.npy')
                    spectra = np.load(f'{cache_path}SDR_Spectra.npy')
                    times = np.load(f'{cache_path}SDR_Times.npy')
                    spectra_freqs = np.load(f'{cache_path}SDR_Freqs.npy')

                    nw_group.create_dataset('Temperatures', data=temperatures, dtype=temperatures.dtype)
                    nw_group.create_dataset('Temperature_Times', data=temperature_times, dtype=temperature_times.dtype)
                    nw_group.create_dataset('Switch_States', data=switch_states_string, dtype=switch_states_string.dtype)
                    nw_group.create_dataset('Switch_Times', data=switch_times, dtype=switch_times.dtype)
                    nw_group.create_dataset('SDR_Spectra', data=spectra, dtype=spectra.dtype)
                    nw_group.create_dataset('SDR_Times', data=times, dtype=times.dtype)
                    nw_group.create_dataset('SDR_Freqs', data=spectra_freqs, dtype=spectra_freqs.dtype)

                    del temperatures, temperature_times, switch_states_string, switch_times
                    del spectra, times, spectra_freqs
                
                    print('Noise Wave Calibrator Spectra Measured and Saved')

                    print('Starting Full Observations')

                    run_simultaneous_obs(sdr=SDR,
                                         arduino=temp_sens_switches,
                                         switch_list=switch_source_list, 
                                         switch_duration=switch_duration,
                                         file=file,
                                         obs_group_string=obs_group_string,
                                         sdr_group_name='OBS_SDR',
                                         arduino_group_name='OBS_ARDUINO',
                                         observation_length=duration,
                                         continous=True)
                    print('Saving Observation Data')

                    antenna_group = obs_group.create_group('Antenna_Observing')

                    temperatures = np.load(f'{cache_path}Temperatures.npy')
                    temperature_times = np.load(f'{cache_path}Temperature_Times.npy')
                    switch_states_string = np.load(f'{cache_path}Switch_States.npy')
                    switch_times = np.load(f'{cache_path}Switch_Times.npy')
                    spectra = np.load(f'{cache_path}SDR_Spectra.npy')
                    times = np.load(f'{cache_path}SDR_Times.npy')
                    spectra_freqs = np.load(f'{cache_path}SDR_Freqs.npy')

                    antenna_group.create_dataset('Temperatures', data=temperatures, dtype=temperatures.dtype)
                    antenna_group.create_dataset('Temperature_Times', data=temperature_times, dtype=temperature_times.dtype)
                    antenna_group.create_dataset('Switch_States', data=switch_states_string, dtype=switch_states_string.dtype)
                    antenna_group.create_dataset('Switch_Times', data=switch_times, dtype=switch_times.dtype)
                    antenna_group.create_dataset('SDR_Spectra', data=spectra, dtype=spectra.dtype)
                    antenna_group.create_dataset('SDR_Times', data=times, dtype=times.dtype)
                    antenna_group.create_dataset('SDR_Freqs', data=spectra_freqs, dtype=spectra_freqs.dtype)

                    del temperatures, temperature_times, switch_states_string, switch_times
                    del spectra, times, spectra_freqs

                    print(f'Saved Group {t_group_init}')
                    timer = time.time()
        
            print(f'Saved hd5f file at {save_path}data_{t_save}.hd5f')
            timer = time.time()

    print('--- @@@ ---')
    print('Observation Done')
    print('--- @@@ ---')
    pass

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
    
    switch_source_list = ['receiver_obsload',
                          'receiver_ns',
                          'receiver_ant']
    
    noise_wave_cal_list = ['receiver_short',
                           'receiver_open',
                           'receiver_load',
                           'receiver_longcable']

    # set up saving directory if one doesn't exit
    if not os.path.exists(path=save_path):
        os.makedirs(save_path)
        print('Save Path Created')
    else:
        print('Save Path Already Set Up')
    save_path = save_path+'/'

    t_save = int(time.time())
    t_init = t_save
    t_end_obs = t_init + observation_length + len(noise_wave_cal_list) * NOISE_WAVE_CAL_SWITCH_TIME

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

            noise_wave_cal_psds = []
            noise_wave_cal_times = []
            noise_wave_cal_switches = []
            noise_wave_cal_switch_times = []
            noise_wave_cal_temps = []

            switch_states = []
            switch_times = []
            switch_index = 0

            SDR.start_stream()


            for cal in noise_wave_cal_list:
                temp_sens_switches.set_switch_state(cal)
                noise_wave_cal_switches.append(cal)
                timer = time.time()
                noise_wave_cal_switch_times.append(timer)
                switch_over_time = timer + NOISE_WAVE_CAL_SWITCH_TIME
                while timer < switch_over_time:
                    timer = time.time()
                    spectrum = SDR.get_averaged_spectra()
                    noise_wave_cal_psds.append(spectrum)
                    noise_wave_cal_times.append(timer) # append averaged spectrum to list
                    temps = temp_sens_switches.read_temp()
                    noise_wave_cal_temps.append(temps) # read temperatures and add to list

            print('Source Observing Now')

            while timer <  t_group_end_time and timer < t_end_obs:
                switch_target = switch_source_list[switch_index]
                temp_sens_switches.set_switch_state(switch_target)
                print('---- Switch Target : ', switch_target, ': ----')
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
            print(temperatures.shape)
            temperature_times = spectra_times

            sdr_freqs = np.array(SDR.freq_channels_mhz)

            noise_wave_cal_psds = np.array(noise_wave_cal_psds)
            noise_wave_cal_times = np.array(noise_wave_cal_times)
            noise_wave_cal_switches = noise_wave_cal_switches
            noise_wave_cal_switch_times = np.array(noise_wave_cal_switch_times)
            noise_wave_cal_temps = np.array(noise_wave_cal_temps)
            print(noise_wave_cal_temps.shape)


            spectra_measurement_group.create_dataset('SDR_Spectra', data=spectra_list, dtype=spectra_list.dtype)
            spectra_measurement_group.create_dataset('SDR_Times', data=spectra_times, dtype=spectra_times.dtype)
            spectra_measurement_group.create_dataset('SDR_Frequencies', data=sdr_freqs, dtype=sdr_freqs.dtype)
            temp_group.create_dataset('Temperatures', data=temperatures, dtype=temperatures.dtype)
            
            temp_group.create_dataset('Times', data=temperature_times, dtype=temperature_times.dtype)
            
            switch_group = obs_group.create_group('Switches')
            switch_times = np.array(switch_times)
            switch_group.create_dataset('Switch_States', data=np.array(switch_states, dtype='S'))
            switch_group.create_dataset('Switch_Times', data=switch_times, dtype=switch_times.dtype)

            noise_wave_cal_obsgroup = obs_group.create_group('NoiseWaveCal')
            noise_wave_cal_obsgroup.create_dataset('SDR_Spectra', data=noise_wave_cal_psds, dtype=noise_wave_cal_psds.dtype)
            noise_wave_cal_obsgroup.create_dataset('SDR_Times', data=noise_wave_cal_times, dtype=noise_wave_cal_times.dtype)
            noise_wave_cal_obsgroup.create_dataset('SDR_Frequencies', data=sdr_freqs, dtype=sdr_freqs.dtype)
            noise_wave_cal_obsgroup.create_dataset('Switch_States', data=np.array(noise_wave_cal_switches, dtype='S'))
            noise_wave_cal_obsgroup.create_dataset('Switch_Times', data=noise_wave_cal_switch_times, dtype=noise_wave_cal_switch_times.dtype)
            noise_wave_cal_obsgroup.create_dataset('Temperatures', data=noise_wave_cal_temps, dtype=noise_wave_cal_temps.dtype)


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
        switching_observing_mp(sample_rate=sample_rate,
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
                            switch_duration=switch_duration,
                            cache_path=TEMP_CACHE)
    else:
        SDR_only_observing(sample_rate=sample_rate,
                           centre_frequency=centre_freq,
                           integration_time=integration_time,
                           fft_length=fft_length, window=fft_window, gain=gain, save_path=SAVE_PATH,
                           observation_length=observation_length)
        pass

    
