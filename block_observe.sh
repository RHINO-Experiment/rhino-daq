#!/bin/bash
# block_observe.sh

yaml_path="${1:-/rhino-daq/obs_config.yaml}"

python3 src/sdr_control.py --yaml $yaml_path &
PID1=$!

python3 src/aux_sdr_control.py --yaml $yaml_path &
PID2=$!

python3 src/arduino_control.py --yaml $yaml_path
PID3=$!

# Wait for all to finish
wait $PID1
wait $PID2
wait $PID3

echo "All obs programs completed."

python3 src/process_cache.py --yaml $yaml_path

echo "Observation Block Complete"