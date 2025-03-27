"""
Helper functions for handling trigger files and state management.
"""
import os
import time
from .config import START_TRIGGER_FILE, STOP_TRIGGER_FILE, ABORT_TRIGGER_FILE, STATE_FILE


def clear_trigger_files():
    """Remove any existing trigger files and initialize state."""
    if os.path.exists(START_TRIGGER_FILE):
        os.remove(START_TRIGGER_FILE)
    if os.path.exists(STOP_TRIGGER_FILE):
        os.remove(STOP_TRIGGER_FILE)
    if os.path.exists(ABORT_TRIGGER_FILE):
        os.remove(ABORT_TRIGGER_FILE)

    # Initialize state to inactive when server starts
    with open(STATE_FILE, 'w') as f:
        f.write("inactive")


def wait_for_start_trigger():
    """Wait for a start trigger file to be created.
    
    Blocks until the start trigger file is detected.
    """
    while not os.path.exists(START_TRIGGER_FILE):
        time.sleep(0.5)

    # Remove the start trigger file once detected
    os.remove(START_TRIGGER_FILE)


def check_stop_trigger():
    """Check if a stop trigger file exists.
    
    Returns:
        bool: True if a stop trigger file exists, False otherwise
    """
    if os.path.exists(STOP_TRIGGER_FILE):
        # Remove the stop trigger file once detected
        os.remove(STOP_TRIGGER_FILE)
        return True
    return False


def check_abort_trigger():
    """Check if abort trigger file exists.
    
    Returns:
        bool: True if abort trigger file exists, False otherwise
    """
    if os.path.exists(ABORT_TRIGGER_FILE):
        # Remove the trigger file
        try:
            os.remove(ABORT_TRIGGER_FILE)
        except Exception:
            pass
        return True
    return False


def set_state(state):
    """Update the state file with the current state.
    
    Args:
        state (str): The state to set, typically 'active', 'inactive', or 'processing'
    """
    with open(STATE_FILE, 'w') as f:
        f.write(state)


def get_state():
    """Get the current state from the state file.
    
    Returns:
        str: The current state, or 'inactive' if the file doesn't exist
    """
    try:
        with open(STATE_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "inactive"