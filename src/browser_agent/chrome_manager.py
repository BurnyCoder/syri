#!/usr/bin/env python3
import os
import subprocess
import sys
import time
import signal
# Global variable to track the Chrome process
chrome_process = None

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

def cleanup(exit_process=True):
    """
    Cleanup function to kill Chrome process
    
    Args:
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