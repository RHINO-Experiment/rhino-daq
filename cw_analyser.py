import h5py
import numpy as np
import os


def isolate_cw_power(spectrum, freqs, channel_sum_sides=2):
    cw_index = np.argmax(spectrum)
    cw_channels_power = spectrum[cw_index-channel_sum_sides:cw_index+channel_sum_sides]
    cw_channels_power = np.sum(cw_channels_power)
    avg_system_power_lower = np.mean(spectrum[cw_index-channel_sum_sides-5:cw_index-channel_sum_sides-1])
    avg_system_power_upper = np.mean(spectrum[cw_index+channel_sum_sides+1:cw_index+channel_sum_sides+5])
    isolated_cw = cw_channels_power - np.mean(np.array([avg_system_power_lower,
                                                        avg_system_power_upper]))
    return isolated_cw

def PSD_from_spectra(spectra, freqs ,times):
    cw_powers = [isolate_cw_power(s, freqs, 3) for s in spectra]
    cw_powers = np.array(cw_powers)
    dt = (times[-1] - times[0]) / len(times)
    psd = np.fft.rfft(cw_powers)
    psd_freqs = np.fft.rfftfreq(len(times), dt)
    return psd, psd_freqs

def complete_avg_std_spectra(spectra):
    avg_spectra = np.mean(spectra, axis=0)
    std_spectra = np.std(spectra, axis=0)
    return avg_spectra, std_spectra

def extract_local_cw_spectra(spectra, std_spectra,freqs):
    cw_index = np.argmax(spectra[0])
    cw_spectra_freqs = freqs[cw_index-50:cw_index+50]
    cw_spectra = spectra[:, cw_index-50:cw_index+50]
    cw_stds = std_spectra[:, cw_index-50:cw_index+50]
    
    return cw_spectra, cw_stds,cw_spectra_freqs


def avg_spectra_time(spectra, times, avg_time=10):
    t_0 = times[0]
    t_f = times[-1]
    new_spectra = []
    new_spectra_std = []
    while t_0 < t_f:
        spectra_to_avg = spectra[times <= t_0+avg_time]
        spectra_to_avg = spectra[times > t_0]
        mean_spectra = np.mean(spectra_to_avg, axis=0)
        std_spectra = np.std(spectra_to_avg, axis=0)
        new_spectra.append(mean_spectra)
        new_spectra_std.append(std_spectra)
        t_0 += avg_time
    return np.array(new_spectra), np.array(new_spectra_std)

if __name__ == "__main__":
    target_folder = '' # ensure the / is not at the end

    hd5f_save_path = '' #save psd from tests to h5df files as well as other options such as averaged spectra

    test_name = ' ' # give it a name

    f = h5py.File(name=hd5f_save_path+test_name, mode='a')

    avg_spectra_grp = f.create_group(name='averaged_spectra')
    std_spectra_grp = f.create_group(name='std_spectra')
    psd_group = f.create_group(name='PSD')
    psd_freq_group = f.create_group(name='PSD_freqs')
    total_spectra_group = f.create_group(name='total_spectra')
    total_std_group = f.create_group(name='total_std')
    running_cw_pwrs_group = f.create_group(name='cw_powers')
    cw_spectra_group = f.create_group(name='cw_spectra')
    cw_spectra_freqs_group = f.create_group(name='cw_spectra_freqs')
    cw_std_group = f.create_group(name='cw_std_spectra')


    for observation in os.listdir(target_folder):
        obs_string = observation[:-5]
        hd5f_to_read = h5py.File(target_folder+'/'+observation, mode='r')
        directory_ = hd5f_to_read[list(hd5f_to_read.keys())[0]]
        spectra = directory_['spectra'][()]
        times = directory_['times'][()]
        freqs = directory_['spectra_frequencies'][()]

        psd, psd_freqs = PSD_from_spectra(spectra, freqs, times)
        psd_group.create_dataset(name=obs_string,
                                 data=psd, dtype=psd.dtype)
        psd_freq_group.create_dataset(name=obs_string, 
                                 data=psd_freqs, dtype=psd_freqs.dtype)

        full_average, full_std = complete_avg_std_spectra(spectra) 
        total_spectra_group.create_dataset(name=obs_string,
                                       data=full_average, dtype=full_average.dtype)
        total_std_group.create_dataset(name=obs_string,
                                       data=full_std, dtype=full_std.dtype)
        

        avg_spectra, avg_stds = avg_spectra_time(spectra, times, 30)

        avg_spectra_grp.create_dataset(name=obs_string, data=avg_spectra, dtype=avg_spectra.dtype)
        std_spectra_grp.create_dataset(name=obs_string, data=avg_stds,
                                       dtype=avg_spectra.dtype)
        
        running_cw_spectra, running_cw_stds,running_cw_spectra_freqs = extract_local_cw_spectra(spectra, freqs)

        cw_spectra_group.create_dataset(name=obs_string, data=running_cw_spectra,
                                        dtype=running_cw_spectra.dtype)
        cw_spectra_freqs_group.create_dataset(name=obs_string, data=running_cw_spectra_freqs,
                                              dtype=running_cw_spectra_freqs.dtype)        

        cw_std_group.create_dataset(name=obs_string, data=running_cw_stds,
                                    dtype=running_cw_stds.dtype)
        
        



    f.close()

