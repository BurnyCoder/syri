#!/usr/bin/env python3
import os
import platform
import subprocess
import sys
import time
import signal
import requests
from typing import Optional

# Global variable to track the Chrome process
chrome_process = None

def is_chrome_debugging_available(port: int = 9222) -> bool:
    """Check if Chrome is already running with remote debugging on specified port"""
    try:
        response = requests.get(f"http://localhost:{port}/json/version")
        return response.status_code == 200
    except requests.RequestException:
        return False

def start_chrome(start_url="https://google.com"):
    """
    Start Chrome with remote debugging enabled
    
    Args:
        start_url (str): The URL to open when Chrome starts. Defaults to Google.
    """
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    global chrome_process
    
    # Check if Chrome is already running with remote debugging
    if is_chrome_debugging_available():
        print("Chrome already running with remote debugging on port 9222, using that instead of starting a new instance")
        return

    # Close any existing Chrome instances with the debug profile
    try:
        subprocess.run(
            "pkill -f \"chrome.*--remote-debugging-port=9222\"", 
            shell=True, 
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass  # Ignore errors if no matching process found
    
    # Determine which Chrome binary to use
    chrome_bin = None

    system = platform.system()
    if system == "Darwin":  # macOS
        mac_chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(mac_chrome_path):
            chrome_bin = mac_chrome_path

    for binary in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
        try:
            if subprocess.run(["which", binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                chrome_bin = binary
                break
        except Exception:
            continue
    
    if not chrome_bin:
        print("Error: Chrome or Chromium browser not found")
        sys.exit(1)
    
    print(f"Starting {chrome_bin} with remote debugging...")
    
    # Start Chrome with remote debugging
    chrome_process = subprocess.Popen(
        [
            chrome_bin,
            "--remote-debugging-port=9222",
            "--user-data-dir=/tmp/chrome-debug-profile",
            start_url
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Give Chrome time to start and fully load
    print(f"Waiting for Chrome to start and load {start_url}...")
    time.sleep(5)

def cleanup(signum=None, frame=None, exit_process=True):
    """
    Cleanup function to kill Chrome process. Also serves as a signal handler.
    
    Args:
        signum: Signal number (when used as signal handler)
        frame: Current stack frame (when used as signal handler)
        exit_process (bool): Whether to exit the Python process after cleanup.
                            Set to False when called programmatically.
    """
    global chrome_process
    if chrome_process:
        print("Shutting down Chrome...")
        chrome_process.terminate()
        try:
            chrome_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chrome_process.kill() 
    
    if exit_process:
        sys.exit(0)
    
if __name__ == "__main__":
    start_chrome()