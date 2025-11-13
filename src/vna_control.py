import numpy as np
import pynanovna

vna = pynanovna.VNA()

vna.set_sweep(60e6, 80e6, 101)

stream = vna.stream()

for s11, s21, frequencies in stream:
   print(s11, s21, frequencies)