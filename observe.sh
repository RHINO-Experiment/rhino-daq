#!/bin/bash
# observe.sh


end=$((SECONDS+54000))

sudo date -s "$(wget --method=HEAD -qSO- --max-redirect=0 google.com 2>&1 | sed -n 's/^ *Date: *//p')"

echo "Launching RHINO Observing Program"

yaml_path="${1:-/rhino-daq/obs_config.yaml}" # Default to /rhino-daq/obs_config.yaml if no argument is provided
log_path="/media/usb0/rhino-data/logs" # Default log path

$(date +"%Y%m%d_%H%M%S")
./prerun_observe.sh $yaml_path \
    2>&1 | tee $log_path/pr_$(date +"%Y%m%d_%H%M%S").log

while [ $SECONDS -lt $end ]; do
    ./block_observe.sh $yaml_path \
        2>&1 | tee $log_path/obs_$(date +"%Y%m%d_%H%M%S").log
done