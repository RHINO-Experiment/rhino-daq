import numpy as np
import serial
import time

#### Arduino Class for control
class Arduino:
    def __init__(self,
                 n__temp_sens,
                 com_port,
                 baud_rate,
                 switch_dictionary):
        
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.n_sens = n__temp_sens
        self.serial = serial.Serial(com_port, baud_rate)
        self.switch_dict = switch_dictionary
        pass

    def open(self):
        if self.serial is None:
            self.serial = serial.Serial(self.com_port, self.baud_rate)
        pass
    
    def get_temperature_from_line(self,
                                  line,
                                  delim=[',',':']):
        # line may be in the form 'T1:27.8,T2:89.0'
        # add try except and number of attempts if there is an error with reading temperature
        try:
            line = line.split(delim[0]) # ['T1:27.8','T2:89.0']
            temps = [float(l.split(delim[-1])[-1]) for l in line]
            print('Temps - ', temps)
            return temps
        except:
            print('TempSensorError')
            print(line)
            temps = [-273 for i in range(len(self.n_sens))]
            return temps

    def read_temp(self):
        self.open()
        self.serial.reset_input_buffer()
        line = self.serial.readline().decode('utf-8')
        line = line.rstrip('\n')
        print(line)
        temps = self.get_temperature_from_line(line)
        self.close()
        return temps
    
    def close(self):
        if self.serial:
            self.serial.close()
        self.serial = None
    
    def set_switch_state(self, switch_cmd):
        self.open()
        time.sleep(0.2)
        cmd = self.switch_dict[switch_cmd]
        print(cmd)
        self.serial.write(cmd.encode())
        time.sleep(0.2)
        self.close()
        pass

####

def continous_arduino_operation(arduino: Arduino,
                                runLength,
                                temperature_cadence,
                                switch_cycleLength,
                                switchTargets):
    
    t = time.time()
    temperatures = []
    temperature_times = []
    switch_states = []
    switch_times = []

    switch_duration = switch_cycleLength / len(switchTargets)

    t_f = t + runLength
    switch_target = switchTargets[0]
    switch_index = 0
    while t < t_f:
        arduino.set_switch_state(switch_target)
        t = time.time()
        t_switch = t + switch_duration
        switch_states.append(switch_target)
        switch_times.append(t)

        while t < t_switch and t < t_f:
            t = time.time()
            temp = arduino.read_temp()
            temperatures.append(temp)
            temperature_times.append(t)
            time.sleep(temperature_cadence)
        switch_index += 1
        if switch_index >= len(switchTargets):
            switch_index = 0
        switch_target = switchTargets[switch_index]
    
    temperatures = np.array(temperatures)
    temperature_times = np.array(temperature_times)
    switch_states = np.array(switch_states, dtype='S')
    switch_times = np.array(switch_times)


    return temperatures, temperature_times, switch_states, switch_times

def continous_temperatures(arduino: Arduino,
                           run_length,
                           temperature_cadence):
    t = time.time()
    temperatures = []
    temperature_times = []
    
    t_f = t + run_length # define end

    while t < t_f:
        t = time.time()
        temp = arduino.read_temp()
        temperatures.append(temp)
        temperature_times.append(t)
        time.sleep(temperature_cadence) # get temperatures
    
    temperatures = np.array(temperatures) # n_sens x n_temps array
    temperature_times = np.array(temperature_times)

    return temperatures, temperature_times

def continous_equal_switching(arduino: Arduino,
                              run_length,
                              cycle_length,
                              switch_targets: list):
    t = time.time()
    switch_duration = cycle_length / len(switch_targets) # time per target
    t_f = t + run_length # end of observation
    switch_states = []
    switch_times = []
    switch_target = switch_targets[0] # set initial position
    while t < t_f:
        arduino.set_switch_state(switch_target)
        t = time.time()
        t_switch = t + switch_duration
        switch_states.append(switch_target)
        switch_times.append(t)

        while t < t_switch and t < t_f:
            t = time.time()
            time.sleep(0.1)
        switch_index += 1
        if switch_index >= len(switch_targets):
            switch_index = 0
        switch_target = switch_targets[switch_index]
        pass

    switch_states = np.array(switch_states, dtype='S')
    switch_times = np.array(switch_times)

    return switch_states, switch_times