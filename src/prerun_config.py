import yaml
import config


def return_sdr_params(yaml_path):
    """
    Returns the SDR parameters from the .yaml file 
    """
    params = config.return_sdr_params(yaml_path)
    with open(yaml_path,'r') as f:
            obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
            pass

    params['runLength'] = obs_config['observationParams']['preRunLength']

    return params

def return_aux_sdr_params(yaml_path):
    """
    Returns the SDR parameters from the .yaml file 
    """
    params = config.return_aux_sdr_params(yaml_path)
    with open(yaml_path,'r') as f:
            obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
            pass

    params['runLength'] = obs_config['observationParams']['preRunLength']

    return params


def return_arduino_params(yaml_path):
    """
    Returns the Arduino parameters from the .yaml file 
    """
    params = config.return_arduino_params(yaml_path)
    with open(yaml_path,'r') as f:
            obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
            pass

    params['runLength'] = obs_config['observationParams']['preRunLength']
    runlength = obs_config['observationParams']['preRunLength']

    unique_states = []
    for state in obs_config['arduino']['switches']['switchSourceTargets']:
        if state not in unique_states:
            unique_states.append(state)
    for state in obs_config['arduino']['switches']['dickeSwitchCycle']:
        if state not in unique_states and state != 'source':
            unique_states.append(state)

    params['switchSourceTargets'] = unique_states
    params['dickeSwitchCycle'] = ['source']
    params['DickeSwitchCycleLength'] = runlength / len(unique_states)
    
    return params


def return_cache_params(yaml_path):
    """
    Returns the cache parameters from the .yaml file 
    """
    params = config.return_cache_params(yaml_path)
    with open(yaml_path,'r') as f:
            obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
            pass
    
    prerun_dir = obs_config['observationParams']['preRunDirectory']

    params['final_data_destination'] = prerun_dir

    return params
