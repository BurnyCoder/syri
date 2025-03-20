#!/bin/bash
# Script to stop the Syri Voice Assistant server

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$ROOT_DIR/triggers/server.pid"

# Check if the PID file exists
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    
    # Check if process is running
    if ps -p $PID > /dev/null; then
        echo "Stopping Syri Voice Assistant server (PID: $PID)..."
        kill $PID
        
        # Wait for process to terminate
        sleep 2
        
        # Force kill if still running
        if ps -p $PID > /dev/null; then
            echo "Server still running, sending SIGKILL..."
            kill -9 $PID
        fi
        
        echo "Server stopped."
    else
        echo "Server not running (PID: $PID)."
    fi
    
    # Remove PID file
    rm "$PID_FILE"
else
    echo "Server not running (no PID file found)."
fi 