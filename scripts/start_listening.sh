#!/bin/bash
# Script to trigger the start of voice recording

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TRIGGER_DIR="$ROOT_DIR/triggers"
STATE_FILE="$TRIGGER_DIR/listening_state"

# Ensure the trigger directory exists
mkdir -p "$TRIGGER_DIR"

# Create the start trigger file
touch "$TRIGGER_DIR/start_listening"

# Update the state file
echo "active" > "$STATE_FILE"

if command -v /opt/homebrew/bin/play >/dev/null 2>&1; then
    /opt/homebrew/bin/play -n synth 0.3 sin 800:1200 gain -5 fade 0.05 0.3 0.05
fi

echo "Start listening trigger created." 