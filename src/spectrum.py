
import numpy as np
from scipy.signal import windows, firwin, freqz, lfilter, get_window


window_dict = {
                'Blackman':          np.blackman,
                'BlackmanHarris':    windows.blackmanharris,
                'Rectangular':       np.ones,
                'Cosine':            windows.cosine
              }


def buffer_to_psd_fft(frame_set, win_coeffs, nChannels, nTaps=None):
    """
    Channelise and accumulate IQ samples into a single PSD (spectrum) time 
    sample, using a windowed FFT for channelisation. 
    
    Parameters:
        frame_set (array_like):
            Complex array of IQ samples from the ADC, of shape 
            `(time_samples, freq_samples)`.
        win_coeffs (array_like):
            Window coeffcients generated using `create_window()`.
        nChannels (int):
            Number of frequency channels to produce.
        nTaps (int):
            Number of taps. This parameter is ignored.
    """
    # Perform an FFT on the windowed buffer, then calculate PSD
    spectrum = np.fft.fft(frame_set * win_coeffs[np.new_axis,:], axis=1)
    psd = (spectrum * spectrum.conj()).real
    
    # Average along time axis and shift into frequency channel ordering
    return np.fft.fftshift( np.mean(psd, axis=0) )
    

def pfb_fir_frontend(x, win_coeffs, nTaps, nChannels):
    """
    
    Parameters:
        x (array_like):
            TBC.
        win_coeffs (array_like):
            TBC.
        nTaps (int):
            Number of PFB taps to use.
        nChannels (int):
            Number of PFB frequency channels to compute.
    """
    # Number of Ps in the data (will be integer for simulations)
    W = x.shape[0] // nTaps // nChannels
    
    # Reshape data and (window coeffs) in rows of length P, then do weighted sum
    x_p = x.reshape((W*nTaps, nChannels)).T
    h_p = win_coeffs.reshape((nTaps, nChannels)).T
    x_weighted = x_p * h_p
    
    # Sum along to get final array f P values
    x_summed = np.sum(x_weighted, axis=1)
    return x_summed


def pfb_filterbank(x, win_coeffs, nTaps, nChannels):
    """ 
    Based on Danny Price's PFB notebook
    
    Parameters:
        x (array_like):
            Voltage TODs.
        win_coeffs (array_like):
            Window coeffcients generated using `create_window()`.
        M (int):
            Number of taps.
        P (int):
            Final number of channels.
    """
    x_fir = pfb_fir_frontend(x, win_coeffs, nTaps, nChannels)
    x_pfb = np.fft.fft(x_fir)
    return np.abs(x_pfb)**2

def create_window(appliedWindow, nChannels, nTaps):
    """
    Create a set of window coefficients.
    """
    return get_window(appliedWindow, 
                      nTaps*nChannels) \
           * firwin(nTaps * nChannels, 
                    cutoff=1.0/nChannels, 
                    window="rectangular")

def buffer_to_psd_pfb(frame_set, win_coeffs, nChannels, nTaps):
    """
    Channelise and accumulate IQ samples into a single PSD (spectrum) time 
    sample, using a polyphase filter bank (PFB) for channelisation.
    
    Parameters:
        frame_set (array_like):
            Complex array of IQ samples from the ADC, of shape 
            `(time_samples, freq_samples)`.
        win_coeffs (array_like):
            Window coeffcients generated using `create_window()`.
        nChannels (int):
            Number of frequency channels to produce.
        nTaps (int):
            Number of taps.
    """
    spectra = np.array([pfb_filterbank(b, win_coeffs, nTaps, nChannels) 
                        for b in frame_set])
    return np.fft.fftshift( np.mean(spectra, axis=0) )

