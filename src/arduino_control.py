import numpy as np
import serial
import yaml
import argparse

def main():
    parser = argparse.ArgumentParser(description="Arduino Control")

    # Add more arguments for lone-running
    parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    
    
    args = parser.parse_args()

    yaml_path = args.yaml


    with open(yaml_path,'r') as f:
        obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
        pass
    # Observation Parameters

    runLength = obs_config['observationParams']['runLength']
    obsCachePath = obs_config['observationParams']['obsCachePath']

    arduino_config = obs_config['arduino']
    active = arduino_config['active']
    if not active: # returns from main if the program is not active
        return
    pass

if __name__ == "__main__":
    main()