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

   input("Press [Enter] to Continue... ")

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


class VNAMeasure:
   def __init__(self,
                start_freq,
                stop_freq,
                n_points,
                recalibrate = False,
                manual_recalibration = True,
                overwrite_previous_cal = True,
                n_int=25,
                complete_s_params=False,
                calibration_path=None,
                customName=True,
                saveDirectory=''):
      
      self.vna = pynanovna.VNA()
      self.vna.set_sweep(start_freq, stop_freq, n_points)

      self.recalibrate = recalibrate
      self.manaul_recalibration = manual_recalibration
      self.overwrite_previous_cal = overwrite_previous_cal

      self.calibration_path = calibration_path
      self.n_int = n_int
      self.s11, self.s21, self.s12, self.s22 = None, None, None, None
      self.freqs = None
      self.complete_s_params = complete_s_params

      self.customName = customName
      self.saveDirectory = saveDirectory
      pass
   
   def manually_recalibrate_vna(self, save):
      calibrate_vna_manual(self.vna,
                           save,
                           self.calibration_path)
      self.load_calibration() # loads the saved calibration to be sure
   
   def load_calibration(self):
      self.vna.load_calibration(self.calibration_path)

   def measure_s_params(self):
      self.s11, self.s21, self.freqs = measure_only(self.vna, self.n_int)
      if self.complete_s_params:
         input('Rotate Device Under Test and Press [Enter] to Continue...')
         self.s22, self.s12, _ = measure_only(self.vna, self.n_int)
      else:
         pass
      pass

   def saveTohd5f(self):
      if self.customName:
         name = input('Enter Save label for save file... ')
      else:
         currentTime = datetime.datetime.now()
         name = currentTime.strftime("%Y-%m-%d_%H-%M-%S_vna")
      filepath = f'{self.saveDirectory}/{name}.hd5f'

      with h5py.File(filepath, mode='w') as f:
         f.create_dataset('Frequencies', data=self.freqs, dtype=self.freqs.dtype)
         f.create_dataset('s11', data=self.s11, dtype=self.s11.dtype)
         f.create_dataset('s21', data=self.s21, dtype=self.s21.dtype)
         if self.complete_s_params:
            f.create_dataset('s22', data=self.s22, dtype=self.s22.dtype)
            f.create_dataset('s12', data=self.s12, dtype=self.s12.dtype) # saves reversed
      print(f'Saved at : {filepath}')
   
   def run_measurements(self):
      if self.recalibrate:
         if self.manaul_recalibration:
            self.manually_recalibrate_vna(save=self.overwrite_previous_cal)
         else:
            #FIXME add option for arduino switching eventually
            pass
      else:
         self.load_calibration(self.calibration_path)
      
      self.measure_s_params()

      self.saveTohd5f()

      print('Done ... ')
      pass


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
   
#   arduino_config = obs_config['arduino']
#   switch_dictionary = obs_config['switchDictionary']

#   vna_calibation_targets = vna_config['calibrationSwitchPaths']
#   vna_calibration_path = vna_config['calibrationPath'] # configuration

#   print(vna_calibration_path)
   

#   recalibration_status = vna_config['recalibrate']
#   n_int = vna_config['integrations']
#   lower_sweep, upper_sweep = vna_config['frequencyRange']
#   n_points = vna_config['dataPoints']
#   vna = pynanovna.VNA()
#   vna.set_sweep(lower_sweep, upper_sweep, n_points)


#   if vna_config['switching'] or not vna_config['manualCalibration']:
#      arduino = arduino_funcs.Arduino(n__temp_sens=arduino_config['temperatureMonitoring']['nProbes'],
#                                      com_port=arduino_config['comPort'],
#                                      baud_rate=arduino_config['baudRate'],
#                                      switch_dictionary=switch_dictionary) # set up arduino for switching

   # Apply or Recalibrate VNA
#   if recalibration_status:
#      manual = vna_config['manualCalibration']
#      if manual:
#         vna = calibrate_vna_manual(vna, vna_calibation_targets, savepath=vna_calibration_path)
#      else:
#         vna = calibrate_vna_switches(vna, arduino, vna_calibation_targets, savepath=vna_calibration_path)
#   else:
#      vna.load_calibration(vna_calibration_path)
   
#   data_path = obs_config['observationParams']['dataDirectory']

   #if vna_config['switching']:
   #   targetS11s = {} # dictionary of s11s
#
#      switch_targets = vna_config['switchTargets']
#      for target in switch_targets:
#         s11_mean, _, freqs = switch_and_measure(target, vna, arduino, n_int)
#         targetS11s[target] = s11_mean
#   else:
      #s11_mean, s21_mean, freqs = measure_only(vna, n_int)
#      pass

   startFreq, stopFreq = vna_config['frequencyRange']
   customNameBool = vna_config['customName']
   recalibrationStatus = vna_config['recalibrate']
   calibrationPath= vna_config['calibrationPath']
   dataPoints = vna_config['dataPoints']
   manualRecalibration = vna_config['manualCalibration']
   integrations = vna_config['integrations']
   completeSparams = vna_config['completeSparams']
   saveDirectory = obs_config['observationParams']['dataDirectory']

   vna_meas_obj = VNAMeasure(start_freq=startFreq,
                             stop_freq=stopFreq,
                             n_points=dataPoints,
                             recalibrate=recalibrationStatus,
                             manual_recalibration=manualRecalibration,
                             overwrite_previous_cal=recalibrationStatus,
                             n_int=integrations,
                             complete_s_params=completeSparams,
                             calibration_path=calibrationPath,
                             customName=customNameBool,
                             saveDirectory=saveDirectory)

   vna_meas_obj.run_measurements()

   #if vna_config['switching']:
   #   save_dict_into_hd5f(switch_targets_s11_dict=targetS11s,
   #                       freqs=freqs,
   #                       filepath=filepath)
   #else:
   #   save_into_hd5f(s11_mean, s21_mean, freqs, filepath)

   print("VNA Measurements Complete")

   pass


if __name__ == "__main__":
    main()