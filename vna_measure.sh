#!/bin/bash
# vna_measure.sh

sudo date -s "$(wget --method=HEAD -qSO- --max-redirect=0 google.com 2>&1 | sed -n 's/^ *Date: *//p')"

echo "Launching VNA Measurements"

yaml_path="/rhino-daq/obs_config.yaml"

python3 src/vna_control.py --yaml $yaml_path

