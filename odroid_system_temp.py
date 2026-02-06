#!/usr/bin/env python
"""
Parse system temperature data dumped to a log file. 
"""
import numpy as np
import pylab as plt
from datetime import datetime
from suntime import Sun, SunTimeException
import re


fname = "temp_monitoring.txt"

# Get data
with open(fname, 'r') as f:
    lines = f.readlines()

# JBO lat/long
latitude = 53.23503660787365
longitude = -2.30498253073103
sun = Sun(latitude, longitude)

# Get today's sunrise and sunset in UTC
today_sr = sun.get_sunrise_time()
today_ss = sun.get_sunset_time()
sunrise_time = today_sr.hour + today_sr.minute/60.
sunset_time = today_ss.hour + today_ss.minute/60.


# Loop over lines to extract
timestamps = []
temp1 = []
temp2 = []
cur = 0
for line in lines:
    if 'UTC' in line:
        try:
            dt = datetime.strptime(line.replace("\n", ""), 
                                   "%a %b %d %H:%M:%S %Z %Y")
        except:
            raise
        timestamps.append(dt)
        
    if 'temp' in line:
        l = re.split("\+", line)
        temp_deg = float(l[1][:4])
        
        if cur % 2 == 0:
            temp1.append(temp_deg)
            
        if cur % 2 == 1:
            temp2.append(temp_deg)
        
        cur += 1

print(len(temp1), len(temp2), len(timestamps))

# Fix jump in time due to clock sync issue
t = np.array([float(_t.hour) + _t.minute/60. for _t in timestamps])
t_fixed = t[-1] - (t[-1] - t[-2]) * np.arange(t.size)[::-1]
plt.plot(t_fixed, temp1)
plt.plot(t_fixed, temp2)

plt.axvline(sunrise_time, ls='dashed', color='k')
plt.axvline(sunset_time, ls='dashed', color='k')

plt.xlabel("Time [hours UTC]", fontsize=14)
plt.ylabel("Temp. [deg C]", fontsize=14)
plt.show()
