#!/bin/bash
#
# Abort Execution Script
#
# This script aborts the current execution of a task or TTS
# by creating a trigger file that the Syri assistant checks for.
#
# Usage:
#   ./abort_execution.sh
#

# Get the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Go up one directory to the project root
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Define trigger directory and files
TRIGGER_DIR="$PROJECT_ROOT/triggers"
ABORT_TRIGGER_FILE="$TRIGGER_DIR/abort_execution"
STATE_FILE="$TRIGGER_DIR/listening_state"

# Ensure trigger directory exists
mkdir -p "$TRIGGER_DIR"

# Create the abort trigger file
touch "$ABORT_TRIGGER_FILE"
echo "Abort signal sent."

# If available, also update the state file to indicate abortion
if [ -f "$STATE_FILE" ]; then
    # Only update if it's not already in inactive state
    if [ "$(cat "$STATE_FILE")" != "inactive" ]; then
        echo "abort_requested" > "$STATE_FILE"
    fi
fi

# Play a distinctive abort sound (if the play command is available)
if command -v /opt/homebrew/bin/play >/dev/null 2>&1; then
    # Play a distinctive abort sound - two short descending tones
    /opt/homebrew/bin/play -n synth 0.15 sin 1400:900 gain -4 fade 0.02 0.15 0.02 : synth 0.15 sin 1400:900 gain -4 fade 0.02 0.15 0.02
fi

exit 0 