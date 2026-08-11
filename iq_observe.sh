#!/bin/bash
# iq_observe.sh

yaml_path="${1:-/rhino-daq/obs_config.yaml}"

python3 raw_iq_observe.py --yaml $yaml_path --target antenna

python3 raw_iq_observe.py --yaml $yaml_path --target load

python3 raw_iq_observe.py --yaml $yaml_path --target noise_diode
