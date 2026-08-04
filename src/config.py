import numpy as np
import h5py
import yaml
import datetime

def return_sdr_params(yaml_path):
    """
    Returns the SDR parameters from the .yaml file 
    """
    with open(yaml_path,'r') as f:
            obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
            pass
    
    obsCachePath = obs_config['observationParams']['obsCachePath']
    runLength = obs_config['observationParams']['runLength']
    sdr_config_path = 'sdr'

    sdr_config = obs_config[sdr_config_path]
    active = sdr_config['active']
    centreFrequency = sdr_config['centreFrequency']
    bandwidth = sdr_config['bandwidth']
    nChannels = sdr_config['nChannels']
    sdrDriver = sdr_config['sdrDriver']
    sdrLabel = sdr_config['sdrLabel']
    sdrId = sdr_config['sdrId']
    sampleIntegrationTime = sdr_config['sampleIntegrationTime']
    spectrometerMode = sdr_config['spectrometerMode']
    sdrGain = sdr_config['sdrGain']
    sdrRFGR = sdr_config['sdrRFGR']
    sdrIFGR = sdr_config['sdrIFGR']
    sdrFlags = sdr_config['sdrFlags']
    delay = sdr_config['delay']
    partial_save_block = sdr_config['partial_save_block']
    if not isinstance(sdrGain, int) or not isinstance(sdrGain, float):
        sdrGain = None

    if spectrometerMode == 'pfb':
        nTaps = sdr_config['pfbParams']['nTaps']
        appliedWindow = sdr_config['pfbParams']['appliedWindow']
    else:
        nTaps = None
        appliedWindow = sdr_config['fftParams']['appliedWindow']


    return {'centreFrequency': centreFrequency,
            'bandwidth': bandwidth,
            'nChannels': nChannels,
            'sdrDriver': sdrDriver,
            'sdrLabel': sdrLabel,
            'sdrId': sdrId,
            'sampleIntegrationTime': sampleIntegrationTime,
            'spectrometerMode': spectrometerMode,
            'sdrGain': sdrGain,
            'sdrRFGR': sdrRFGR,
            'sdrIFGR': sdrIFGR,
            'delay': delay,
            'runLength': runLength,
            'obsCachePath': obsCachePath,
            'sdrFlags': sdrFlags,
            'active': active,
            'nTaps': nTaps,
            'appliedWindow': appliedWindow,
            'partial_save_block': partial_save_block
            }

def return_aux_sdr_params(yaml_path):
    """
    Returns the SDR parameters from the .yaml file 
    """
    with open(yaml_path,'r') as f:
            obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
            pass
    
    obsCachePath = obs_config['observationParams']['obsCachePath']

    runLength = obs_config['observationParams']['runLength']

    sdr_config_path = 'auxSdr'

    sdr_config = obs_config[sdr_config_path]
    active = sdr_config['active']
    centreFrequency = sdr_config['centreFrequency']
    bandwidth = sdr_config['bandwidth']
    nChannels = sdr_config['nChannels']
    sdrDriver = sdr_config['sdrDriver']
    sdrLabel = sdr_config['sdrLabel']
    sdrId = sdr_config['sdrId']
    sampleIntegrationTime = sdr_config['sampleIntegrationTime']
    spectrometerMode = sdr_config['spectrometerMode']
    sdrGain = sdr_config['sdrGain']
    sdrRFGR = sdr_config['sdrRFGR']
    sdrIFGR = sdr_config['sdrIFGR']
    delay = sdr_config['delay']
    if not isinstance(sdrGain, int) or not isinstance(sdrGain, float):
        sdrGain = None

    if spectrometerMode == 'pfb':
        nTaps = sdr_config['pfbParams']['nTaps']
        appliedWindow = sdr_config['pfbParams']['appliedWindow']
    else:
        nTaps = None
        appliedWindow = sdr_config['fftParams']['appliedWindow']


    return {'centreFrequency': centreFrequency,
            'bandwidth': bandwidth,
            'nChannels': nChannels,
            'sdrDriver': sdrDriver,
            'sdrLabel': sdrLabel,
            'sdrId': sdrId,
            'sampleIntegrationTime': sampleIntegrationTime,
            'spectrometerMode': spectrometerMode,
            'sdrGain': sdrGain,
            'sdrRFGR': sdrRFGR,
            'sdrIFGR': sdrIFGR,
            'delay': delay,
            'runLength': runLength,
            'obsCachePath': obsCachePath,
            'active': active,
            'nTaps': nTaps,
            'appliedWindow': appliedWindow
            }

def return_arduino_params(yaml_path):
    """
    Returns the Arduino parameters from the .yaml file 
    """
    with open(yaml_path,'r') as f:
            obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
            pass
    
    obsCachePath = obs_config['observationParams']['obsCachePath']
    runLength = obs_config['observationParams']['runLength']

    arduino_config = obs_config['arduino']
    active = arduino_config['active']

    baud_rate = arduino_config['baudRate']
    com_port = arduino_config['comPort']

    # dictionary for switches e.g 'load':'t1t1e5'
    switch_dictionary = arduino_config['switchDictionary']

    temp_monitoring_status = arduino_config['temperatureMonitoring']['active']
    switch_status = arduino_config['switches']['active']

    if temp_monitoring_status:
        n_temp_sens = arduino_config['temperatureMonitoring']['nProbes']
        temp_cadence = arduino_config['temperatureMonitoring']['cadence']
    else:
        n_temp_sens = None

    switchSourceTargets = obs_config['arduino']['switches']['switchSourceTargets']
    dickeSwitchCycle = obs_config['arduino']['switches']['dickeSwitchCycle']
    DickeSwitchCycleLength = obs_config['arduino']['switches']['DickeSwitchCycleLength']

    return {'baudRate': baud_rate,
            'comPort': com_port,
            'switchDictionary': switch_dictionary,
            'temp_monitoring_status': temp_monitoring_status,
            'switch_status': switch_status,
            'n_temp_sens': n_temp_sens,
            'temp_cadence': temp_cadence,
            'runLength': runLength,
            'obsCachePath': obsCachePath,
            'active': active,
            'switchSourceTargets': switchSourceTargets,
            'dickeSwitchCycle': dickeSwitchCycle,
            'DickeSwitchCycleLength': DickeSwitchCycleLength}
    
def return_cache_params(yaml_path):
    with open(yaml_path,'r') as f:
        obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
        pass
    final_data_destination = obs_config['observationParams']['dataDirectory']
    cached_path = obs_config['observationParams']['obsCachePath']

    if obs_config['observationParams']['customName'] is None:
        currentTime = datetime.datetime.now()
        filename = currentTime.strftime("%Y-%m-%d_%H-%M-%S_obs")
    else:
        filename = obs_config['observationParams']['dataDirectory']['customName']

    return {'final_data_destination': final_data_destination,
            'cached_path': cached_path,
            'filename': filename,
            'obs_config': obs_config}
