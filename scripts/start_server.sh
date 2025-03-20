#!/bin/bash
# Script to start the Syri Voice Assistant server

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to the root directory
cd "$ROOT_DIR"

# Start the server in the background
echo "Starting Syri Voice Assistant server..."
python run.py &

# Save the PID
echo $! > "$ROOT_DIR/triggers/server.pid"

echo "Server started (PID: $(cat $ROOT_DIR/triggers/server.pid))" 