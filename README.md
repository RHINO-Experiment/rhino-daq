# rhino-daq
Data acquisition code for RHINO receiver prototypes

In its current state, the code uses SoapySDR to interface with an SDRPlay RSP1A to 
acquire I/Q data via USB. This is then FFT'd and averaged in frequency and time.

The code is designed to work on a mini-PC, like a Raspberry Pi or Odroid.

# Requirements
-  SoapySDR and relevent drivers for the observing SDRs
-  numpy
-  scipy
-  pySerial
-  nanovna.py

# /src/
The Python files in /src/ are supposed to be ran through observe.sh or similar shell functions to facilitate observations. Each is for a specific piece of hardware e.g. arduino_contol.py -arduino... Parameters and configuration should be set up in obs_config.yaml and read by each function.
## arduino_control.py
Script to run the arduino due to perform temperature measurements, switching, CW control etc.

## sdr_control.py/aux_sdr_control.py
Script to run the SDRs used during observing. aux_sdr is the auxillery sdr for observing the CW

## fft_funcs.py
Utility functions for running an FFT spectrometer with sdr_control.py

## pfb_funcs.py
Utility functions for running a PFB spectrometer with sdr_control.py. Largely based on the code by Danny Price at https://github.com/telegraphic/pfb_introduction/tree/master

## vna_control.py
Script for communication and data logging with the VNA

## process_cache.py
Scipt to convert the data numpy arrays and observing information saved to the cache folder during observations to .hd5f observation data files

# observe.sh
Shell script for running observations. Will run scripts for hardware in parallell with setting defined prior to observing with obs_config.yaml.

# old - observe.func.py
Old utility functions and classes for running observations. Needs to be integrated into /src/

# old - observing_program.py
Old script for running observations from a single python script using argparse to set parameters. Arduino sections need integrating into arduino_control.py

