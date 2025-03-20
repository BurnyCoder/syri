#!/bin/bash
# Script to toggle voice recording (start if stopped, stop if started)

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TRIGGER_DIR="$ROOT_DIR/triggers"
STATE_FILE="$TRIGGER_DIR/listening_state"

# Ensure the trigger directory exists
mkdir -p "$TRIGGER_DIR"

# Check current state
if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE")" == "active" ]; then
    # Currently listening, so stop it
    "$SCRIPT_DIR/stop_listening.sh"
else
    # Not listening, so start it
    "$SCRIPT_DIR/start_listening.sh"
fi 