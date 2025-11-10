## Based on Danny Price's PFB notebook

from scipy.signal import firwin, freqz, lfilter, get_window
import numpy as np


def pfb_fir_frontend(x, win_coeffs, nTaps, nChannels):
    W = x.shape[0] // nTaps // nChannels               # number of Ps in the data - will be integer for simulations
    x_p = x.reshape((W*nTaps, nChannels)).T             # reshapes data in rows of length P
    h_p = win_coeffs.reshape((nTaps, nChannels)).T      # reshapes window coefficients
    x_weighted = x_p * h_p                  # weighted sum
    x_summed = np.sum(x_weighted, axis=1)   # sum along to get final array f P values
    return x_summed

def fft(x_p1):
    return np.fft.fft(x_p1)

def pfb_filterbank(x, win_coeffs, nTaps, nChannels):
    """ 
    x:
        voltage TODs
    win_coeffs:
        window coeffcients generated using create_window()
    M:
        number of taps
    P:
        final number of channels
    """
    x_fir = pfb_fir_frontend(x, win_coeffs, nTaps, nChannels)
    x_pfb = fft(x_fir)
    return np.abs(x_pfb)**2

def create_window(appliedWindow, nChannels, nTaps):
    win_coeffs = get_window(appliedWindow, nTaps*nChannels)
    sinc       = firwin(nTaps * nChannels, cutoff=1.0/nChannels, window="rectangular")
    win_coeffs *= sinc
    return win_coeffs

def buffs_to_powers(buffs, win_coeffs, nChannels, nTaps):
    spectra = [pfb_filterbank(b, win_coeffs, nTaps, nChannels) for b in buffs]
    spectra = np.array(spectra)
    spectra = np.mean(spectra, axis=0)
    spectra = np.fft.fftshift(spectra)
    return spectra
