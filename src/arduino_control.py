import numpy as np
import serial
import yaml
import argparse
import arduino_funcs

def main():
    parser = argparse.ArgumentParser(description="Arduino Control") # Set up parser

    # Add more arguments for lone-running

    # Point to yaml file for configuration
    parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    
    args = parser.parse_args()
    yaml_path = args.yaml

    # load the .yaml as a list to get settings
    with open(yaml_path,'r') as f:
        obs_config = yaml.safe_load(f) 
        pass
    
    # Observation Parameters
    runLength = obs_config['observationParams']['runLength']
    obsCachePath = obs_config['observationParams']['obsCachePath']

    arduino_config = obs_config['arduino']

    # returns from main if the program is not active
    active = arduino_config['active']
    if not active: 
        return
    pass

    # check status of the temperature monitoring and switches
    temp_monitoring_status = obs_config['arduino']['temperatureMonitoring']['active']
    switch_status = obs_config['arduino']['switches']['active']

    baud_rate = obs_config['arduino']['baudRate']
    com_port = obs_config['arduino']['comPort']

    gcrObserving = obs_config['arduino']['switches']['gcrObserving']

    # dictionary for switches e.g 'load':'t1t1e5'
    switch_dictionary = obs_config['switchDictionary']

    if temp_monitoring_status:
        n_temp_sens = obs_config['arduino']['temperatureMonitoring']['nProbes']
        temp_cadence = obs_config['arduino']['temperatureMonitoring']['cadence']
    else:
        n_temp_sens = None

    # set up the arduino class to use in observations
    arduino_object = arduino_funcs.Arduino(n__temp_sens=n_temp_sens,
                                           com_port=com_port,
                                           baud_rate=baud_rate,
                                           switch_dictionary=switch_dictionary)
    
    # switchSourceTargets
    switchSourceTargets = obs_config['arduino']['switches']['switchSourceTargets']
    dickeSwitchCycle = obs_config['arduino']['switches']['dickeSwitchCycle']
    DickeSwitchCycleLength = obs_config['arduino']['switches']['DickeSwitchCycleLength']

    if temp_monitoring_status and switch_status:
        print('|| arduino_control.py Begining General Observing ||')
        temperatures, temperature_times, \
        switch_states, switch_times = arduino_funcs.general_observing(arduino=arduino_object,
                                                                      runLength=runLength,
                                                                      temperature_cadence=temp_cadence,
                                                                      dickeSwitchCycleLength=DickeSwitchCycleLength,
                                                                      switchSourceTargets=switchSourceTargets,
                                                                      dickeSwitchCycle=dickeSwitchCycle)
        np.save(f'{obsCachePath}/temperature_array.npy', arr=temperatures)
        np.save(f'{obsCachePath}/temperature_times.npy', arr=temperature_times)
        np.save(f'{obsCachePath}/switch_states.npy', arr=switch_states)
        np.save(f'{obsCachePath}/switch_times.npy', arr=switch_times)
        print('Arduino Function Finished and Cached')
        
        return


    elif temp_monitoring_status and not switch_status:
        temperatures, temperature_times = arduino_funcs.continous_temperatures(arduino=arduino_object,
                                                                               run_length=runLength,
                                                                               temperature_cadence=temp_cadence)
        np.save(f'{obsCachePath}/temperature_array.npy', arr=temperatures)
        np.save(f'{obsCachePath}/temperature_times.npy', arr=temperature_times)

        print('Arduino Function Finished and Cached')
        return

    
    primaryTarget = obs_config['arduino']['switches']['primaryTarget']
    if primaryTarget is not None:
        switch_targets = [primaryTarget, 'receiver_obsload', 'receiver_ns']
    else:
        switch_targets = obs_config['arduino']['switches']['switchTargets']
    cycleLength = obs_config['arduino']['switches']['cycleLength']

    if switch_status and not temp_monitoring_status:
        
        switch_states, switch_times = arduino_funcs.continous_equal_switching(arduino_object,
                                                                              runLength,
                                                                              cycleLength,
                                                                              switch_targets)

        np.save(f'{obsCachePath}/switch_states.npy', arr=switch_states)
        np.save(f'{obsCachePath}/switch_times.npy', arr=switch_times)
        print('Arduino Function Finished and Cached')
        return

    if gcrObserving:
        temperatures, temperature_times, \
        switch_states, switch_times = arduino_funcs.gcr_continous_arduino_operation(arduino_object,
                                                                                runLength,
                                                                                temp_cadence,
                                                                                cycleLength,
                                                                                switch_targets)
        np.save(f'{obsCachePath}/temperature_array.npy', arr=temperatures)
        np.save(f'{obsCachePath}/temperature_times.npy', arr=temperature_times)
        np.save(f'{obsCachePath}/switch_states.npy', arr=switch_states)
        np.save(f'{obsCachePath}/switch_times.npy', arr=switch_times)
        print('Arduino Function Finished and Cached')

    else:
        temperatures, temperature_times, \
        switch_states, switch_times = arduino_funcs.continous_arduino_operation(arduino_object,
                                                                                runLength,
                                                                                temp_cadence,
                                                                                cycleLength,
                                                                                switch_targets)
        np.save(f'{obsCachePath}/temperature_array.npy', arr=temperatures)
        np.save(f'{obsCachePath}/temperature_times.npy', arr=temperature_times)
        np.save(f'{obsCachePath}/switch_states.npy', arr=switch_states)
        np.save(f'{obsCachePath}/switch_times.npy', arr=switch_times)
        print('Arduino Function Finished and Cached')
        
        return


if __name__ == "__main__":
    main()

