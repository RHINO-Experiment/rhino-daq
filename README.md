# rhino-daq
Data acquisition code for the RHINO receiver.

In its current state, the code uses SoapySDR to interface with an SDRPlay RSP1A to 
acquire I/Q data via USB. This is then FFT'd and averaged in frequency and time.

The code is designed to work on a mini-PC, like a Raspberry Pi or Odroid.

# Requirements
-  SoapySDR and relevent drivers for the observing SDRs
-  numpy
-  scipy
-  pySerial
-  pynanovna

# Running Observations
- First, edit or create your own obs_config.yaml file with the specified parameters. Ensure the switch dictionary is accurate as well as the ID numbers of the SDRs and ports for the Arduino.
- Check the cache location for saving data.
- Set a time for the observation to stop looping in observe.sh with end=$((SECONDS+126000))
- Run the observation in a screen with $./observe.sh . If something goes wrong simply kill the screen using $pkill screen from the primary terminal. The sdr interface cannot be killed with ctrl+c.
- When one or all blocks are finished running and have been processed successfully, run $perseus_data_dump.sh to scp the data to the perseus2 machine. This will require your username and password.
- To clear data, run $clean_data_dir.sh to avoid the disk filling mid obsevation. Ensure data has been properly copied over first.

---------------------------------------------------------------------------------------------------
# observe.sh
Shell script for running observations. Will first run the prerun observation for designated amount of time before looping and running block_observe.sh until the time runs out.

# prerun_observe.sh
Shell script for running the prerun observation before launching the full observation program. Will split the time equally between designated targets.

# block_observe.sh
Shell script for observing. Will run the sdr and arduino scripts in parallel.

# /src/
Location for python modules to run observations. These are subdivded into hardware such as sdr and arduino_control.py as well as other modules such as the spectrum.py which contains channelisation code or arduino_funcs.py which houses functions for processessing the arduino inputs and outputs.
## /src/arduino_control.py
Script to run the arduino to enable source switching and temperature monitoring etc.

## /src/sdr_control.py and aux_sdr_control.py
Scripts to run the SDRs used during observing.

## /src/spectrum.py
Utility functions for running a PFB and FFT spectrometer with sdr_control.py. Primarily based on the code by Danny Price at https://github.com/telegraphic/pfb_introduction/tree/master

## /src/vna_control.py
Script for communication and data logging with the VNA

## /src/process_cache.py
Scipt to convert the data numpy arrays and observing information saved to the cache folder during observations to .hdf5 observation data files




# old - observe.func.py
Old utility functions and classes for running observations. Needs to be integrated into /src/

# old - observing_program.py
Old script for running observations from a single python script using argparse to set parameters. Arduino sections need integrating into arduino_control.py

