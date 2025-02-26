import numpy as np
import matplotlib.pyplot as plt
import h5py

f = h5py.File(name= '2025_02_25.hdf5', mode='r')
print(list(f.keys()))
g = f['140612']
sub_freq = g['f60.0']
print(list(sub_freq.keys()))

freqs = sub_freq['spectra_frequencies'][()]
spectra = sub_freq['spectra'][()]

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
    p = avg_ant_spectra - avg_load_spectra
    q_arr.append(p)
    f_arr.append(freqs)

q_arr = np.array(q_arr)
f_arr = np.array(f_arr)




flat_q = q_arr.flatten()
flat_f = f_arr.flatten()

flat_q = [q for _,q in sorted(zip(flat_f, flat_q))]
flat_f =  [f for f,_ in sorted(zip(flat_f, flat_q))]

flat_q = np.array(flat_q)
flat_f = np.array(flat_f)

plt.plot(flat_f / 10**6, flat_q)
plt.show()

