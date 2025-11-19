#!/bin/bash
# observe.sh

end=$((SECONDS+15))

sudo date -s "$(wget --method=HEAD -qSO- --max-redirect=0 google.com 2>&1 | sed -n 's/^ *Date: *//p')"

echo "Launching RHINO Observing"

yaml_path="/rhino-daq/obs_config.yaml"

python3 src/vna_control.py --yaml $yaml_path

while [ $SECONDS -lt $end ]; do
    # Launch both SDR scripts in parallel and arduino script
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

    python3 src/process_cache.py

    echo "Observation Block Complete"
done