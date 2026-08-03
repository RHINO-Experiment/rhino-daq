#!/bin/bash
# prerun_observe.sh

echo "Launching RHINO ReRun Observation..."

yaml_path="${1:-/rhino-daq/obs_config.yaml}"

# Launch both SDR scripts in parallel and arduino script
python3 src/sdr_control.py --yaml $yaml_path --prerun &
PID1=$!

python3 src/aux_sdr_control.py --yaml $yaml_path --prerun &
PID2=$!

python3 src/arduino_control.py --yaml $yaml_path --prerun
PID3=$!

# Wait for all to finish
wait $PID1
wait $PID2
wait $PID3

echo "All obs programs completed."

python3 src/process_cache.py --yaml $yaml_path --prerun

echo "||Pre Run Block Complete||"