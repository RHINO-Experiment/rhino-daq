import numpy as np
import argparse
import arduino_funcs
import config
import prerun_config

def main():
    parser = argparse.ArgumentParser(description="Arduino Control") # Set up parser

    # Add more arguments for lone-running

    # Point to yaml file for configuration
    parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    
    parser.add_argument('--prerun',
                        action='store_true',
                        help='Runs the Script in Prerun Mode')
    
    args = parser.parse_args()
    yaml_path = args.yaml

    if args.prerun:
        params = prerun_config.return_arduino_params(yaml_path)
    else:
        params = config.return_arduino_params(yaml_path)
    
    # Observation Parameters
    runLength = params['runLength']
    obsCachePath = params['obsCachePath']

    # returns from main if the program is not active
    active = params['active']
    if not active: 
        return

    # check status of the temperature monitoring and switches
    temp_monitoring_status = params['temp_monitoring_status']
    switch_status = params['switch_status']

    baud_rate = params['baudRate']
    com_port = params['comPort']

    # dictionary for switches e.g 'load':'t1t1e5'
    switch_dictionary = params['switchDictionary']
    n_temp_sens = params['n_temp_sens']
    temp_cadence = params['temp_cadence']

    # switchSourceTargets
    switchSourceTargets = params['switchSourceTargets']
    dickeSwitchCycle = params['dickeSwitchCycle']
    DickeSwitchCycleLength = params['DickeSwitchCycleLength']

    arduino_object = arduino_funcs.Arduino(n__temp_sens=n_temp_sens,
                                           com_port=com_port,
                                           baud_rate=baud_rate,
                                           switch_dictionary=switch_dictionary)

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

    if switch_status and not temp_monitoring_status:
        
        switch_states, switch_times = arduino_funcs.continous_equal_switching(arduino_object,
                                                                              runLength,
                                                                              DickeSwitchCycleLength,
                                                                              switchSourceTargets)

        np.save(f'{obsCachePath}/switch_states.npy', arr=switch_states)
        np.save(f'{obsCachePath}/switch_times.npy', arr=switch_times)
        print('Arduino Function Finished and Cached')
        return


if __name__ == "__main__":
    main()

