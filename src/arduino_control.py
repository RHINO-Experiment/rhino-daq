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
    obsCachePath = params['obsCachePath']

    # returns from main if the program is not active
    active = params['active']
    if not active: 
        return

    # check status of the temperature monitoring and switches
    temp_monitoring_status = params['temp_monitoring_status']
    switch_status = params['switch_status']

    arduino_object = arduino_funcs.Arduino(n__temp_sens=params['n_temp_sens'],
                                           com_port=params['comPort'],
                                           baud_rate=params['baudRate'],
                                           switch_dictionary=params['switchDictionary'])

    if temp_monitoring_status and switch_status:
        print('|| arduino_control.py Begining General Observing ||')
        temperatures, temperature_times, \
        switch_states, switch_times = arduino_funcs.general_observing(arduino=arduino_object,
                                                                      runLength=params['runLength'],
                                                                      temperature_cadence=params['temp_cadence'],
                                                                      dickeSwitchCycleLength=params['DickeSwitchCycleLength'],
                                                                      switchSourceTargets=params['switchSourceTargets'],
                                                                      dickeSwitchCycle=params['DickeSwitchCycleLength'])

        np.savez_compressed(f'{obsCachePath}/temperature_data.npz',
                            temperatures=temperatures,
                            temperature_times=temperature_times)

        np.savez_compressed(f'{obsCachePath}/switch_data.npz',
                            switch_states=switch_states,
                            switch_times=switch_times)

        print('Arduino Function Finished and Cached')
        
        return


    elif temp_monitoring_status and not switch_status:
        temperatures, temperature_times = arduino_funcs.continous_temperatures(arduino=arduino_object,
                                                                               run_length=params['runLength'],
                                                                               temperature_cadence=params['temp_cadence'])
        np.savez_compressed(f'{obsCachePath}/temperature_data.npz',
                                    temperatures=temperatures,
                                    temperature_times=temperature_times)

        print('Arduino Function Finished and Cached')
        return

    if switch_status and not temp_monitoring_status:
        
        switch_states, switch_times = arduino_funcs.continous_equal_switching(arduino_object,
                                                                              params['runLength'],
                                                                              params['DickeSwitchCycleLength'],
                                                                              params['switchSourceTargets'])

        np.savez_compressed(f'{obsCachePath}/switch_data.npz',
                                    switch_states=switch_states,
                                    switch_times=switch_times)
        print('Arduino Function Finished and Cached')
        return


if __name__ == "__main__":
    main()

