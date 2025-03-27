"""
Configuration and constants for the Syri Voice Assistant.
"""
import os

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRIGGER_DIR = os.path.join(BASE_DIR, 'triggers')

# Trigger files
START_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'start_listening')
STOP_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'stop_listening')
ABORT_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'abort_execution')
STATE_FILE = os.path.join(TRIGGER_DIR, 'listening_state')

# Ensure trigger directory exists
os.makedirs(TRIGGER_DIR, exist_ok=True)