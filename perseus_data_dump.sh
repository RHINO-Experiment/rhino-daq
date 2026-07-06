#!/bin/bash
# perseus_data_dump.sh

# define the proxycommand

# proxycommand = "ProxyCommand=ssh -q -W %h:%p username@external.jb.man.ac.uk"


TUNNEL_HOST="external.jb.man.ac.uk"
TARGET_HOST="perseus2"

LOCAL_DIR="/media/usb0/rhino-data"
TARGET_DIR="/raid1/rhino/obs_data"


read -rp "Enter your JBCA username: " USERNAME  

scp -r \
    -o "ProxyCommand=ssh -q -W %h:%p ${USERNAME}@${TUNNEL_HOST}" \
    "${LOCAL_DIR}" \
    "${USERNAME}@${TARGET_HOST}:${TARGET_DIR}"

echo "Copy complete."