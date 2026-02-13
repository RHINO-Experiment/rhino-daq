import numpy as np
import matplotlib.pyplot as plt
import h5py

f = h5py.File(name= '2025_03_04no_vna.hdf5', mode='r')
print(list(f.keys()))
g = f[list(f.keys())[3]]

noise_diode_enr = 12 #dB
fig, axes = plt.subplots(nrows=len(list(g.keys())), sharex=False, figsize=(12,12))
for i in np.arange(len(list(g.keys()))):
    sub_freq = g[list(g.keys())[i]]
    freqs = sub_freq['spectra_frequencies'][()]
    spectra = sub_freq['spectra'][()]
    times = sub_freq["times"][()]
    extent = [freqs[0]/10**6, freqs[-1]/10**6, times[-1], times[0]]
    axes[i].imshow(10*np.log10(spectra), extent=extent, aspect='auto')
    axes[i].set_ylabel('Time [s]')
axes[np.arange(len(list(g.keys())))[-1]].set_xlabel(r'$\nu$ [MHz]')
fig.tight_layout()
plt.show()
#fig.savefig('Spectra_load_vna_on_shifted.pdf')
g = f['151851']
sub_freq = g['f80.0']
print(list(sub_freq.keys()))

times = sub_freq['times'][()]
switch_times = sub_freq['switch_times'][()]
print(switch_times)
epoch = sub_freq['times'].attrs['epoch']

q_arr = []
f_arr = []
for cf in list(g.keys()):
    sub_group = g[cf]
    switch_times = sub_group['switch_times']
    times = sub_group['times']
    spectra = sub_group['spectra']
    freqs = sub_group['spectra_frequencies']
    antenna_spectra = spectra[times < switch_times[1]]
    load_spectra = spectra[times < switch_times[2]]
    load_spectra = spectra[times >= switch_times[1]]
    noise_diode_spectra = spectra[times >= switch_times[2]]
    avg_ant_spectra = np.mean(antenna_spectra, axis=0)
    avg_load_spectra = np.mean(load_spectra, axis=0)
    avg_nd_spectra = np.mean(noise_diode_spectra, axis=0)
    q = (avg_ant_spectra - avg_load_spectra) / (avg_nd_spectra - avg_load_spectra)
    q_arr.append(q)
    f_arr.append(freqs)

q_arr = np.array(q_arr)
f_arr = np.array(f_arr)

flat_q = q_arr.flatten()
flat_f = f_arr.flatten()

flat_q = [q for _,q in sorted(zip(flat_f, flat_q))]
flat_f =  [f for f,_ in sorted(zip(flat_f, flat_q))]

flat_q = np.array(flat_q)
flat_f = np.array(flat_f)

plt.plot(flat_f / 10**6, flat_q, '-')
plt.ylabel('q = src - load / noisediode - load')
plt.xlabel(r'$\nu$ [MHz]')
plt.show()


