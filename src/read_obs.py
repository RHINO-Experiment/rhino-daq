import numpy as np
import matplotlib.pyplot as plt
import h5py
import pickle

def load_dict_from_group(group: h5py.Group):
    """
    Load a dictionary from a group previously written with save_dict_to_group.
    Restores nested dicts, pickled values, None, and strings.
    """
    def _load(group):
        out = {}
        for key, item in group.items():
            # Sub-group
            if isinstance(item, h5py.Group):
                out[key] = _load(item)

            # Dataset
            elif isinstance(item, h5py.Dataset):

                # None marker
                if item.attrs.get("__is_none__", False):
                    out[key] = None
                    continue

                # Pickled object
                if item.attrs.get("__pickled__", False):
                    raw = bytes(np.asarray(item))
                    out[key] = pickle.loads(raw)
                    continue

                # Standard dataset
                data = item[()]
                # Convert bytes → str if possible
                if isinstance(data, bytes):
                    try:
                        data = data.decode("utf-8")
                    except Exception:
                        pass
                # Convert 0-dim array → Python scalar
                if isinstance(data, np.ndarray) and data.shape == ():
                    data = data.tolist()

                out[key] = data

        return out

    return _load(group)


class ObsObj: # object for working with 
    def __init__(self,
                 filepath : str,
                 target='ant',
                 switch_buffer = 1,
                 noise_diode_ENR_dB = 9.6):
        """
        filepath: hd5f filepath 
        """
        
        # read in
        with h5py.File(filepath, 'r') as f:
            self.sdr_waterfall = f['sdr']['sdr_waterfall'][()]
            self.sdr_times = f['sdr']['sdr_times'][()]
            self.sdr_freqs = f['sdr']['sdr_freqs'][()]
            self.switch_states = f['switches']['switch_states'][()]
            self.switch_times = f['switches']['switch_times'][()]
            self.temperatures = f['temperatures']['temperatures'][()] 
            self.temperature_times = f['temperatures']['temperature_times'][()]
            config_group = f['obs_config']
            try:
                self.obs_config = load_dict_from_group(config_group)
            except:
                print('obs_config not accessible')
            pass
        
        # flag for temperature errors
        mask = ~np.isin(self.temperatures, -273)
        mask = np.array(np.prod(mask, axis=1), dtype=bool)

        self.temperature_times = self.temperature_times[mask]
        self.temperatures = self.temperatures[mask] + 273.15

        self.source_target = target
        self.switch_buffer = switch_buffer
        self.noise_diode_ENR_dB = noise_diode_ENR_dB
        self.processed_spectra_bool = False
        pass
    
    def zero_times(self, zero_to_sdr=True):
        if zero_to_sdr:
            t0 = self.sdr_times[0]
        else:
            t0 = self.switch_times[0]

        self.sdr_times -= t0
        self.temperature_times -= t0
        self.switch_times -= t0

    def plot_all(self):
        plt.imshow(10*np.log10(self.sdr_waterfall), aspect='auto', cmap='jet')
        plt.show()

        plt.plot(np.mean(self.sdr_waterfall, axis=0))
        plt.yscale('log')
        plt.show()

        for temps in self.temperatures.T:
            plt.plot(self.temperature_times - self.temperature_times[0], temps)
        plt.show()

        plt.scatter(self.switch_times, self.switch_states)
        plt.show() # make more elaborate

    def process_and_seperate_sources(self):
        observation_spectra_dict = {}
        for state in self.switch_states:
            state = self.strip_string(state)
            if state not in observation_spectra_dict:
                observation_spectra_dict[state] = [] # creates a list for a given switch state

        avg_temps = []
        times  = []

        for i, (state, time) in enumerate(zip(self.switch_states, self.switch_times)):
            state = self.strip_string(state) # the switch_state_observed
            t_min = time + self.switch_buffer
            # get corresponding spectra
            if i != len(self.switch_times)-1:
                t_max = self.switch_times[i+1] - self.switch_buffer
                spectra_mask = (self.sdr_times >= t_min) & (self.sdr_times <= t_max)
                temperatures_mask = (self.temperature_times >= t_min) & (self.temperature_times <= t_max)
            else:
                spectra_mask = (self.sdr_times >= t_min)
                temperatures_mask = (self.temperature_times >= t_min)
            ##
            spectra = self.sdr_waterfall[spectra_mask]
            temperatures = self.temperatures[temperatures_mask] # mask temperatures and spectra

            spectra = np.mean(spectra, axis=0)
            observation_spectra_dict[state].append(spectra)     # averaged spectra
            avg_temps.append(np.mean(temperatures, axis=0))     # averaged temperature
            times.append(np.mean(self.sdr_times[spectra_mask])) # average spectra time
        
        avg_temps = np.array(avg_temps)
        times = np.array(times)

        self.observation_spectra_dict = observation_spectra_dict
        self.times = times
        self.avg_temps = avg_temps
        self.processed_spectra_bool = True
        pass

    def plot_avg_spectra(self):
        if self.processed_spectra_bool is not True:
            self.process_and_seperate_sources()
        
        for state, spectra_list in self.observation_spectra_dict.items():
            # average spectra
            spectra_list = np.array(spectra_list)
            mean_spectra = np.mean(spectra_list, axis=0)
            plt.plot(self.sdr_freqs / 1e6, mean_spectra, label=state)
        plt.ylabel(r'$P$ [arb.]')
        plt.xlabel(r'$\nu$ [MHz]')
        lower_quantile = np.quantile(self.sdr_waterfall, 0.05)
        upper_quantile = np.quantile(self.sdr_waterfall, 0.95)
        plt.ylim(lower_quantile, upper_quantile)
        plt.legend()
        plt.show()


    def process_and_seperate_sources_old(self, plot=True):
        source_spectra = []
        load_spectra = []
        ns_spectra = []
        load_temps = []

        observation_spectra = {}
        for state in self.switch_states:
            state = self.strip_string(state)
            if state not in observation_spectra:
                observation_spectra[state] = [] # creates a list for a given switch state

        state = self.strip_string(state) # the switch_state_observed
        t_min = time + self.switch_buffer
        # get corresponding spectra
        if i != len(self.switch_times)-1:
            t_max = self.switch_times[i+1] - self.switch_buffer
            spectra_mask = (self.sdr_times >= t_min) & (self.sdr_times <= t_max)
            temperatures_mask = (self.temperature_times >= t_min) & (self.temperature_times <= t_max)
        else:
            spectra_mask = (self.sdr_times >= t_min)
            temperatures_mask = (self.temperature_times >= t_min)
        ##
        spectra = self.sdr_waterfall[spectra_mask]
        temperatures = self.temperatures[temperatures_mask]
        spectra = np.mean(spectra, axis=0)
        observation_spectra[state].append(spectra)
        
    
        list_dictionary = {f'receiver_{self.source_target}':source_spectra,
                           'receiver_obsload':load_spectra,
                           'receiver_ns':ns_spectra}

        for i, (state, time) in enumerate(zip(self.switch_states, self.switch_times)):
            state = self.strip_string(state) # the switch_state_observed
            t_min = time + self.switch_buffer
            # get corresponding spectra
            if i != len(self.switch_times)-1:
                t_max = self.switch_times[i+1] - self.switch_buffer
                spectra_mask = (self.sdr_times >= t_min) & (self.sdr_times <= t_max)
                temperatures_mask = (self.temperature_times >= t_min) & (self.temperature_times <= t_max)
            else:
                spectra_mask = (self.sdr_times >= t_min)
                temperatures_mask = (self.temperature_times >= t_min)
            ##
            spectra = self.sdr_waterfall[spectra_mask]
            temperatures = self.temperatures[temperatures_mask]
            spectra = np.mean(spectra, axis=0)
            list_dictionary[state].append(spectra)
            if state == 'receiver_obsload':
                load_temps.append(np.mean(temperatures, axis=0))
        
        if plot:
            for spectra in source_spectra:
                plt.plot(spectra, c='b')
        
            for spectra in load_spectra:
                plt.plot(spectra, c='g')
        
            for spectra in ns_spectra:
                plt.plot(spectra, c='r')
            
            plt.yscale('log')
            plt.xlim(200, 1800)
            plt.ylim(1e-9, 1e-6)
            plt.show()
            pass
        
        n_cal_cycles = min([len(load_spectra), len(ns_spectra), len(source_spectra)])

        q_spectra = []
        t_stars = []

        for i in range(n_cal_cycles):
            src, load, ns = source_spectra[i], load_spectra[i], ns_spectra[i]

            t_load = load_temps[i][0]
            t_ns = load_temps[i][1] * 10 ** (self.noise_diode_ENR_dB / 10)

            q = (src - load) / (ns - load)
            q_spectra.append(q)

            t_cal = (t_ns * q) + t_load
            t_stars.append(t_cal)
            pass
        for q in q_spectra:
            plt.plot(q)
        plt.ylabel('q')
        plt.show()

        for t in t_stars:
            plt.plot(t)
        plt.ylabel(r'$T_{\rm cal}$')
        plt.ylim(0,1000)
        plt.title('rough approximation')
        plt.show()

        

    def strip_string(self, string):
        return str(string)[2:-1]