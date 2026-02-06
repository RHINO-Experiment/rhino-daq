#!/usr/bin/env python3

import numpy as np
import pylab as plt

# Load data
# date, time, Hz low, Hz high, Hz step, samples, dbm, dbm
fname = "sweep_300MHz_450MHz.dat"
d = np.genfromtxt(fname, delimiter=',').T
print(d.shape)

# Load date/time separately
d_date, d_time = np.genfromtxt(fname, delimiter=',', usecols=(0,1), dtype=str).T
#print(d_date)

# Get columns
dates = d[0]
times = d[1]
numin, numax, dnu = d[2:5]
nsamp = d[5]
data = d[6:]

# Get unique frequency ranges
freq_min = np.unique(numin)
freq_max = np.unique(numax)
freq_delta = np.unique(dnu)
assert freq_min.size == freq_max.size
assert freq_delta.size == 1
freq_delta = freq_delta[0]

# Construct entire frequency range
freq_vals = []
freq_samples = {}
for i in range(freq_min.size):
    # Make frequency array for this row
    #_freqs = np.arange(freq_min[i], freq_max[i], freq_delta)
    _freqs = np.linspace(freq_min[i], 
                       freq_max[i], 
                       round((freq_max[i] - freq_min[i]) / freq_delta)+2)
    freq_vals.append(_freqs)
    
    # Keep track of no. of samples per row
    freq_samples[(freq_min[i], freq_max[i])] = _freqs.size
    
freqs = np.concatenate(freq_vals)

# Get unique times
t_unique = np.unique(d_time)

# Set up data array
print("Times:", t_unique.size)
print("Freqs:", freqs.size)
wfall = np.zeros((t_unique.size, freqs.size))

"""
print("-"*40)
kk = 0
#print(freq_min[0], freq_max[0], freq_min[1], freq_max[1])
print(numin[kk], numax[kk], freq_delta)
print((freq_min[kk], freq_max[kk]))
print((freq_max[kk] - freq_min[kk]) / freq_delta)
print(freq_samples[(freq_min[kk], freq_max[kk])])

_freqs = np.linspace(freq_min[kk], 
                       freq_max[kk], 
                       int((freq_max[kk] - freq_min[kk]) / freq_delta)+2)
print(_freqs)
print("**", int((freq_max[kk] - freq_min[kk]) / freq_delta))
print(round((freq_max[kk] - freq_min[kk]) / freq_delta))
print(data[:,0].size)
print("-"*40)
"""

# Loop over unique times
for i, t in enumerate(t_unique):
    # Get entries with this unique time
    idxs = np.where(d_time == t)[0]

    # Get each row of data
    for k in idxs:
        j = np.argmin(np.abs(freqs - numin[k]))
        print( j, numin[k], freqs[j] )
        #print(data[:,k])
        nsamp = freq_samples[(numin[k], numax[k])] # no. of freq. samples
        print("nsamp =", nsamp)
        wfall[i,j:j+nsamp] = data[:nsamp,k]

# Plot waterfall
plt.matshow(wfall, extent=[freqs[0]/1e6, freqs[-1]/1e6, 0, 1], aspect='auto')
plt.xlabel("Freq. [MHz]", fontsize=14)
plt.title("%s" % d_date[0])
plt.colorbar()
plt.show()

#plt.subplot(111)
#plt.plot(freqs/1e6, wfall)
#plt.title("%s %s" % (d_date[0,0], d_date[0,1]))
#plt.show()

#plt.matshow(data[:])
#plt.colorbar()
#plt.show()
