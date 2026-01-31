import numpy as np
from scipy.signal import windows, firwin, freqz, lfilter

window_dict = {'Blackman':np.blackman,
               'BlackmanHarris':windows.blackmanharris,
               'Rectangular':np.ones,
               'Cosine':windows.cosine}

def buffs_to_powers(buffs, win_coeffs, nChannels, nTaps):
    spectra = [np.abs(np.fft.fft(b*win_coeffs))**2 for b in buffs] # goes through the buffer and ffts and sqaures
    spectra = np.array(spectra)
    spectra = np.mean(spectra, axis=0) # average along time-axis
    spectra = np.fft.fftshift(spectra)
    # split buffer into nChannels
    return spectra
