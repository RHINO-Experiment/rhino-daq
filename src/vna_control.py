import numpy as np
import pynanovna
import argparse
import yaml
import arduino_funcs
import time
import datetime
import h5py


def switch_and_measure(switch_command: str,
                       vna: pynanovna.VNA,
                       arduino: arduino_funcs.Arduino,
                       n_int: int):
    arduino.open()
    arduino.set_switch_state(switch_command)
    time.sleep(1)
    s11_mean, s21_mean, freqs = get_integrated_sparams(vna, n_int)
    return s11_mean, s21_mean, freqs


def measure_only(vna: pynanovna.VNA,
                 n_int: int):
   time.sleep(1)

   s11_mean, s21_mean, freqs = get_integrated_sparams(vna, n_int)
   return s11_mean, s21_mean, freqs

def get_integrated_sparams(vna: pynanovna.VNA,
                           n_int:int):
   s11s, s21s = [], []

   for _ in range(n_int):
      s11, s21, freqs = vna.sweep()
      s11s.append(s11)
      s21s.append(s21)

   s11s, s21s = np.array(s11s), np.array(s21s)
   s11_mean = np.mean(s11s, axis=0)
   s21_mean = np.mean(s21s, axis=0)

   return s11_mean, s21_mean, freqs

def calibrate_vna_manual(vna: pynanovna.VNA,
                         save: bool = True,
                         savepath: str = None):
   print('--- Manual VNA Calibration ---')
   input("Attatch Short - Press any to calibrate")
   vna.calibration_step('short')
   input("Attatch Open - Press any to calibrate")
   vna.calibration_step("open")
   input("Attatch Load - Press any to calibrate")
   vna.calibration_step("load")

   input("Attatch Load to both ports - Press any to calibrate")
   vna.calibration_step("isolation")

   input("Connect Through Port")
   vna.calibration_step("through")

   input("Enter Anything to Continue")

   vna.calibrate()
   if save:
      vna.save_calibration(savepath)
   return vna

def calibrate_vna_switches(vna: pynanovna.VNA,
                           arduino: arduino_funcs.Arduino,
                           vna_calibration_targets:dict,
                           save: bool = True,
                           savepath: str = None):
   
   arduino.set_switch_state(vna_calibration_targets['load'])
   time.sleep(2)
   vna.calibration_step('load')

   arduino.set_switch_state(vna_calibration_targets['short'])
   time.sleep(2)
   vna.calibration_step('short')

   arduino.set_switch_state(vna_calibration_targets['open'])
   time.sleep(2)
   vna.calibration_step('open')

   arduino.set_switch_state(vna_calibration_targets['through'])
   time.sleep(2)
   vna.calibration_step('through')

   vna.calibrate()

   if save:
      vna.save_calibration(savepath)
   return vna


def save_dict_into_hd5f(switch_targets_s11_dict: dict, freqs, filepath):
   """
   Recursively saves dictionary objects into hd5f file 
   """
   with h5py.File(filepath, mode='w') as f:
      f.create_dataset('Frequencies', data=freqs)
      for target, s11 in switch_targets_s11_dict.items():
         f.create_dataset(target, data=s11, dtype=s11.dtype)

def save_into_hd5f(s11_mean,
                   s21_mean,
                   freqs,
                   filepath):
   """
   saves .numpy to hd5f
   """
   with h5py.File(filepath, mode='w') as f:
      f.create_dataset('Frequencies', data=freqs)
      f.create_dataset('s11', data=s11_mean, dtype=s11_mean.dtype)
      f.create_dataset('s21', data=s21_mean, dtype=s21_mean.dtype)


def main():
   parser = argparse.ArgumentParser(description="VNA Control")

   # Add more arguments for lone-running
   parser.add_argument('--yaml', type=str,
                        default='/rhino-daq/obs_config.yaml',
                        help='Config .yaml filepath')
    
   args = parser.parse_args()
   yaml_path = args.yaml

   with open(yaml_path,'r') as f:
      obs_config = yaml.safe_load(f) # load the .yaml as a list to get settings
      pass

   vna_config = obs_config['vna']
   active = vna_config['active']
   if not active: # returns from main if the program is not active
      return
   
   arduino_config = obs_config['arduino']
   switch_dictionary = obs_config['switchDictionary']

   vna_calibation_targets = vna_config['calibrationSwitchPaths']
   vna_calibration_path = vna_config['calibrationPath'] # configuration

   print(vna_calibration_path)
   

   recalibration_status = vna_config['recalibrate']
   n_int = vna_config['integrations']
   lower_sweep, upper_sweep = vna_config['frequencyRange']
   n_points = vna_config['dataPoints']
   vna = pynanovna.VNA()
   vna.set_sweep(lower_sweep, upper_sweep, n_points)

   if vna_config['switching'] or not vna_config['manualCalibration']:
      arduino = arduino_funcs.Arduino(n__temp_sens=arduino_config['temperatureMonitoring']['nProbes'],
                                      com_port=arduino_config['comPort'],
                                      baud_rate=arduino_config['baudRate'],
                                      switch_dictionary=switch_dictionary) # set up arduino for switching

   # Apply or Recalibrate VNA
   if recalibration_status:
      manual = vna_config['manualCalibration']
      if manual:
         vna = calibrate_vna_manual(vna, vna_calibation_targets, savepath=vna_calibration_path)
      else:
         vna = calibrate_vna_switches(vna, arduino, vna_calibation_targets, savepath=vna_calibration_path)
   else:
      vna.load_calibration(vna_calibration_path)
   
   data_path = obs_config['observationParams']['dataDirectory']

   if vna_config['switching']:
      targetS11s = {} # dictionary of s11s

      switch_targets = vna_config['switchTargets']
      for target in switch_targets:
         s11_mean, _, freqs = switch_and_measure(target, vna, arduino, n_int)
         targetS11s[target] = s11_mean
   else:
      s11_mean, s21_mean, freqs = measure_only(vna, n_int)
   

   if not vna_config['customName']:
      currentTime = datetime.datetime.now()
      curentTimestring = currentTime.strftime("%Y-%m-%d_%H-%M-%S_vna")
      filepath = f"{data_path}/{curentTimestring}"
   else:
      custom_name = str(input('Enter Save Name'))
      filepath = f"{data_path}/{custom_name}_vna"

   if vna_config['switching']:
      save_dict_into_hd5f(switch_targets_s11_dict=targetS11s,
                          freqs=freqs,
                          filepath=filepath)
   else:
      save_into_hd5f(s11_mean, s21_mean, freqs, filepath)

   print("VNA Measurements Complete")

   pass


if __name__ == "__main__":
    main()