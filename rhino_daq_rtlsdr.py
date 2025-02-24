import serial
import numpy as np
from datetime import timedelta, datetime
import time
import h5py
import nanovna
from rtlsdr import *


# establish observing stratergy
class VNA:
    def __init__(self):
        
        pass

    def get_s11_measurements(self, min_freq=60e6, max_freq=80e6, n_integrations=5):
        vna = nanovna.NanoVNA(nanovna.getport())
        vna.open()
        vna.set_frequencies(start=min_freq, stop=max_freq)
        vna.set_sweep(start=min_freq, stop=max_freq)
        scans = [vna.scan() for i in np.arange(n_integrations)]

        scan_s11 = []
        for scan in scans:
            s11 = scan[0]
            scan_s11.append(s11)
        scan_s11 = np.array(scan_s11)
        scan_s11_mean, scan_s11_std = np.mean(scan_s11, axis=0), np.std(scan_s11, axis=0)
        
    
        return scan_s11_mean, scan_s11_std, vna.frequencies
    
    def get_s12_measurements(self, min_freq=60e6, max_freq=80e6, n_integrations=5):
        vna = nanovna.NanoVNA(nanovna.getport())
        vna.open()
        vna.set_frequencies(start=min_freq, stop=max_freq)
        vna.set_sweep(start=min_freq, stop=max_freq)
        scans = [vna.scan() for i in np.arange(n_integrations)]

        scan_s12 = []
        for scan in scans:
            s12 = scan[1]
            scan_s12.append(s12)
        scan_s12 = np.array(scan_s12)
        scan_s12_mean, scan_s12_std = np.mean(scan_s12, axis=0), np.std(scan_s12, axis=0)
        
    
        return scan_s12_mean, scan_s12_std, vna.frequencies

class Thermomotry:
    def __init__(self, com_port, baud_rate):
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.serial = serial.Serial(com_port, baud_rate)
        pass
    def open(self):
        if self.serial is None:
            self.serial = serial.Serial(self.com_port, self.baud_rate)
        pass
    
    def get_temperature_from_line(self, line):
        line = line.split(',')
        ## change this for real format
        return line[-1]

    def read_temp(self):
        self.open()
        self.serial.reset_input_buffer()
        line = self.serial.readline().decode('utf-8')
        temp = self.get_temperature_from_line(line)
        return temp
    
    def close(self):
        if self.serial:
            self.serial.close()
        self.serial = None

class RtlSdrLogger:
    def __init__(self, averaging_time_seconds, sample_rate, 
                 centre_frequency, fft_length, sdr_gain_set, window_function, averaging=True):
        self.averaging = averaging
        self.sample_rate = sample_rate
        self.centre_frequency = centre_frequency
        self.fft_length = fft_length
        self.sdr_gain_set = sdr_gain_set
        self.averaging_time_seconds = averaging_time_seconds

        if window_function == 'Blackman':
            self.fft_filter = np.blackman(self.fft_length)
        elif window_function == 'Hamming':
            self.fft_filter = np.hamming(self.fft_length)
        elif window_function == 'Bartlett':
            self.fft_filter = np.bartlett(self.fft_length)
        elif window_function == 'Hanning':
            self.fft_filter = np.hanning(self.fft_length)
        else:
            self.fft_filter = np.ones(self.fft_length)

        self.num_rows_to_average = int(self.sample_rate * averaging_time_seconds / fft_length)
        pass
    
    def get_avg_spectra(self):
        spectra = []
        for i in self.num_rows_to_average:
            x = self.sdr.read_samples(self.fft_length) * self.fft_filter
            spectra.append(np.abs(np.fft.fft(x))**2)
        spectra = np.array(spectra)
        spectra = np.mean(spectra, axis=0)
        return spectra
    
    def close_sdr(self):
        self.sdr.close()
        pass


    def init_sdr(self):
        self.sdr = RtlSdr()
        self.sdr.sample_rate = self.sample_rate
        self.sdr.center_freq = self.centre_frequency
        self.sdr.gain = self.sdr_gain_set

        #start_time = time.time()
        #start_time = time.strftime("%Y_%m_%d_%H%M%S", start_time)
        #self.file_name = start_time + '.csv'
        #self.text_file_name = start_time+'.txt'
        #t_0 = time.time()
        x = self.sdr.read_samples(self.fft_length)
        del x

        pass

class Switches:
    def __init__(self, com_port, baud_rate, switch_dictionary):
        self.com_port, self.baud_rate = com_port, baud_rate
        self.switch_dict = switch_dictionary
        self.serial = serial.Serial(self.com_port, self.baud_rate)
        pass

    def open(self):
        if self.serial is None:
            self.serial = serial.Serial(self.com_port, self.baud_rate)
        pass
    
    def set_switch_state(self, switch_cmd):
        self.open()
        cmd = self.switch_dict[switch_cmd]
        self.serial.write(cmd.encode())
        time.sleep(0.5)
        pass

    def close(self):
        if self.serial:
            self.serial.close()
        self.serial = None


class MultiFrequencyObserver:
    def __init__(self, thermometry, switches, 
                 freq_range=(60e6, 80e6), sample_rate = 2.0e6, averaging_time_per_sdr_sample = 10, 
                 fft_length = 2048, sdr_gain = 0.0, spectrum_window='None',
                 integration_time_per_frequency = 60, obs_time_split=None, save_folder=''):
        self.thermometry = thermometry
        self.switches =  switches
        self.sample_rate = sample_rate
        self.averaging_time_per_sdr_sample = averaging_time_per_sdr_sample
        self.fft_length = fft_length
        self.sdr_gain = sdr_gain
        self.spectrum_window = spectrum_window
        self.integration_time_per_frequency = integration_time_per_frequency
        self.obs_time_split = obs_time_split
        self.save_folder = save_folder

        self.centre_frequencies = np.linspace(freq_range[0], freq_range[-1], int(freq_range[-1] - freq_range[0] / sample_rate))

        pass

    def get_sol_measurements(self, start_f, end_f, nint):
        vna = VNA()
        self.switch.set_switch_state('vna_short')
        short_s11, _, vna_freqs = vna.get_s11_measurements(min_freq=start_f, max_freq=end_f,n_integrations=nint)

        self.switch.set_switch_state('vna_open')
        open_s11, _, _ = vna.get_s11_measurements(min_freq=start_f, max_freq=end_f,n_integrations=nint)

        self.switch.set_switch_state('vna_load')
        load_s11, _, _ = vna.get_s11_measurements(min_freq=start_f, max_freq=end_f,n_integrations=nint)
        sol_f_array = np.array([short_s11, open_s11, load_s11, vna_freqs])
        return sol_f_array



        

    def begin_observations(self, obs_title=None):
        date_string = datetime.strftime("%Y_%m_%d_%H%M%S", datetime.now())
        time_string = datetime.strftime("%H%M%S", datetime.now())
        save_file = h5py.File(self.save_folder+date_string+".hdf5" ,'a')
        int_time_per_freq = timedelta(seconds=self.integration_time_per_frequency)
        epoch = datetime.now()

        if obs_title is None:
            obs_group = save_file.create_group(time_string)
        else:
            obs_group = save_file.create_group(obs_title)
            # add in option to check if group exists and add_1 to the name

        for cf in self.centre_frequencies:
            freq_string = 'f'+str(self.centre_frequencies / 10**6)
            freq_group = obs_group.create_group(freq_string)
            sdr = RtlSdrLogger(self.averaging_time_per_sdr_sample, self.sample_rate, cf,
                               fft_length=self.fft_length, sdr_gain_set = self.sdr_gain,
                               window_function=self.spectrum_window, averaging=True)
            
            solf_array = self.get_sol_measurements(start_f=cf-self.sample_rate/2, end_f=cf+self.sample_rate/2, nint=10)
            freq_group.create_dataset('sol_f_arr',data=solf_array)

            self.switches.set_switch_state('vna_antenna')
            vna = VNA()
            antenna_s11, _, vna_freqs = vna.get_s11_measurements(start_f=cf-self.sample_rate/2, end_f=cf+self.sample_rate/2, nint=10)
            freq_group.create_dataset('s11_ant',data=antenna_s11)

            self.switches.set_switch_state('vna_load_term')
            load_s11,_,_ = vna.get_s11_measurements(start_f=cf-self.sample_rate/2, end_f=cf+self.sample_rate/2, nint=10)
            freq_group.create_dataset('s11_load',data=load_s11)

            self.switches.set_switch_state('vna_noise_diode')
            noise_diode_s11,_,_ = vna.get_s11_measurements(start_f=cf-self.sample_rate/2, end_f=cf+self.sample_rate/2, nint=10)
            freq_group.create_dataset('s11_noise_diode',data=noise_diode_s11)
            freq_group.create_dataset('s11_vna_freqs', data=vna_freqs)

            t_0 = datetime.now()
            obs_switch_states = ["rec_antenna", "rec_load", "rec_noise_diode"]

            sdr.init_sdr()

            if self.obs_time_split is None:
                switch_time_det = [t_0 + int_time_per_freq/3, t_0 + 2*int_time_per_freq/3, t_0 + int_time_per_freq]
            else:
                switch_time_det = [t_0 + self.obs_time_split[0]*int_time_per_freq, 
                               t_0 + (self.obs_time_split[0]+self.obs_time_split[1])*int_time_per_freq,
                               t_0 + int_time_per_freq]
            

            switch_state = []
            switch_times_real = []
            temperatures = []
            times = []
            spectra = []
            for i in np.arange(len(obs_switch_states)):
                data_log = True
                self.switches.set_switch_state(obs_switch_states[i])
                switch_state.append(obs_switch_states[i])
                switch_times_real.append(datetime.now())

                while data_log:
                    t = datetime.now()
                    temp = self.thermometry.read_temp()
                    s = sdr.get_avg_spectra()
                    spectra.append(s)
                    temperatures.append(temp)
                    times.append(t)
                    
                    if datetime.now() >= switch_time_det[i]:
                        data_log=False
            
            spectra = np.array(spectra)
            frequencies = np.linspace(cf-self.sample_rate/2, cf+self.sample_rate/2, num=self.fft_length)
            temperatures = np.array(temperatures)
            times = [(t - epoch).total_seconds() for t in times]
            switch_times_real = [(t - epoch).total_seconds() for t in switch_times_real]
            epcoh_string = epoch.strftime('%Y_%m_%d_%H%M%S')

            freq_group.create_dataset('spectra', data=spectra)
            freq_group.create_dataset('spectra_frequencies', data=frequencies)
            t_ds = freq_group.create_dataset('times', data=times)
            st_ds = freq_group.create_dataset('switch_times', data=switch_times_real)
            freq_group.create_dataset('temperatures', data=temperatures)

            t_ds.attrs['epoch'] = epcoh_string
            st_ds.attrs['epoch'] = epcoh_string
            for switch_state in np.arange(len(obs_switch_states)):
                st_ds.attrs['switch_state_'+int(switch_state)] = obs_switch_states[switch_state]
            
            freq_group

        save_file.close()
        pass

if __name__ == '__main__':
    switch_dictionary = {}
    switch = Switches(com_port='switch_port', baud_rate=111, switch_dictionary=switch_dictionary)
    thermomotry =  Thermomotry(com_port='temp_sens_port', baud_rate=111)

    observer = MultiFrequencyObserver(thermometry=thermomotry, switches=switch, freq_range=(60e6, 80e6), 
                                      sample_rate=2e6, averaging_time_per_sdr_sample=1, fft_length=2048, sdr_gain=0.0,
                                      spectrum_window='Blackman', integration_time_per_frequency=60, obs_time_split=[1/3,1/3,1/3],
                                      save_folder='')
    
    observer.begin_observations('test')




