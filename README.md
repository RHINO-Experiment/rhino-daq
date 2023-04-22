# rhino-daq
Data acquisition code for RHINO receiver prototypes

In its current state, the code uses SoapySDR to interface with an SDRPlay RSP1A to 
acquire I/Q data via USB. This is then FFT'd and averaged in frequency and time.

The code is designed to work on a mini-PC, like a Raspberry Pi or Odroid.
