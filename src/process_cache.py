"""
Code to proces the numpy arrays from obsrvations and store in hd5f files
"""
import numpy as np
import h5py
import yaml
import datetime
import argparse

def main():
# Base of actual obs_config.yaml
    parser = argparse.ArgumentParser(description="Dual SDR Observation (RTLSDR + SDRplay)")

    # Add more arguments for lone-running
    parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    
    args = parser.parse_args()

    yaml_path = args.yaml

    with open(yaml_path,'r') as f:
        obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
        pass

    final_data_destination = obs_config['observationParams']['dataDirectory']
    cached_path = obs_config['observationParams']['obsCachePath']

    data_update_status = np.load(f'{cached_path}/new_data_bool.npy')
    # True if data has not been processed yet
    if not data_update_status:
        return

    try:
        mock_data_status = np.load(f'{cached_path}/mock_data_bool.npy')
    except:
        mock_data_status = False

    # Set up a custom name for the file or go with the time/date the function was ran
    if obs_config['observationParams']['customName'] is None:
        currentTime = datetime.datetime.now()
        if mock_data_status:
            filename = currentTime.strftime("%Y-%m-%d_%H-%M-%S_mock")
        else:
            filename = currentTime.strftime("%Y-%m-%d_%H-%M-%S_obs")
    else:
        filename = obs_config['observationParams']['dataDirectory']['customName']

    with h5py.File(f'{final_data_destination}/{filename}.hd5f', mode='a') as f:
        sdr_group = f.create_group('sdr')
        aux_sdr_group = f.create_group('aux_sdr')
        temperature_group = f.create_group('temperatures')
        switching_group = f.create_group('switches')

        if obs_config['sdr']['active']: # set up sdr group
            sdr_waterfall = np.load(f'{cached_path}/sdr_waterfall.npy')
            sdr_freqs = np.load(f'{cached_path}/sdr_freqs.npy')
            sdr_times = np.load(f'{cached_path}/sdr_times.npy')
            sdr_group.create_dataset('sdr_waterfall', data=sdr_waterfall, dtype=sdr_waterfall.dtype)
            sdr_group.create_dataset('sdr_freqs', data=sdr_freqs, dtype=sdr_freqs.dtype)
            sdr_group.create_dataset('sdr_times', data=sdr_times, dtype=sdr_times.dtype)
            pass
        else: # else create empty data sets
            sdr_group.create_dataset('sdr_waterfall', dtype="f")
            sdr_group.create_dataset('sdr_freqs', dtype="f")
            sdr_group.create_dataset('sdr_times', dtype="f")
        
        if obs_config['auxSdr']['active']:
            aux_sdr_waterfall = np.load(f'{cached_path}/aux_sdr_waterfall.npy')
            aux_sdr_freqs = np.load(f'{cached_path}/aux_sdr_freqs.npy')
            aux_sdr_times = np.load(f'{cached_path}/aux_sdr_times.npy')
            aux_sdr_group.create_dataset('aux_sdr_waterfall',
                                         data=aux_sdr_waterfall,
                                         dtype=aux_sdr_waterfall.dtype)
            aux_sdr_group.create_dataset('aux_sdr_freqs',
                                         data=aux_sdr_freqs,
                                         dtype=aux_sdr_freqs.dtype)
            aux_sdr_group.create_dataset('aux_sdr_times',
                                         data=aux_sdr_times,
                                         dtype=aux_sdr_times.dtype)
        else: # else create empty data sets
            aux_sdr_group.create_dataset('aux_sdr_waterfall', dtype="f")
            aux_sdr_group.create_dataset('aux_sdr_freqs', dtype="f")
            aux_sdr_group.create_dataset('aux_sdr_times', dtype="f")

        ## Same but for arduino observables

    # update the update and mock status back to False
    np.save(f'{cached_path}/new_data_bool.npy', False)
    np.save(f'{cached_path}/mock_data_bool.npy', False)

    print('Data Processed into hd5f.')
    pass
    
if __name__ == "__main__":
    main()