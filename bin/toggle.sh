#!/bin/bash

# Define the process name to look for (identifying the python script)
PROCESS_NAME="run.py"

# Function to check if the app is running
is_running() {
    pgrep -f "$PROCESS_NAME" > /dev/null
}

if is_running; then
    # App is running, send SIGUSR1 to toggle listening
    pkill -USR1 -f "$PROCESS_NAME"
else
    # App is not running, launch it
    # Determine the directory where this script is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    # Execute the run script
    # We use nohup to detach it so it keeps running if this script exits
    # Redirect output to log for debugging if needed, or /dev/null
    nohup "$PROJECT_DIR/venv/bin/python" "$PROJECT_DIR/run.py" > /dev/null 2>&1 &
fi
