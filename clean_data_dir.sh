#!/bin/bash
# clean_data_dir.sh

# Directory to clean
DATA_DIR="/media/usb0/rhino-data"

# Check that the directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "Error: Directory does not exist."
    exit 1
fi

echo "This will remove all files from:"
echo "$DATA_DIR/data"
echo "$DATA_DIR/logs"
echo "$DATA_DIR/prerun"

read -p "Are you sure you want to continue? (y/n): " ANSWER

if [ "$ANSWER" = "y" ] || [ "$ANSWER" = "Y" ]; then
    rm -f "$DATA_DIR/data"/*
    rm -f "$DATA_DIR/logs"/*
    rm -f "$DATA_DIR/prerun"/*
    echo "Files removed."
else
    echo "Operation cancelled."
fi