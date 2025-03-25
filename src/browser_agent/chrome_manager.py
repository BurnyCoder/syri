#!/usr/bin/env python3
import os
import platform
import subprocess
import sys
import time
import signal
import requests
from typing import Optional, Dict

# Dictionary to track Chrome processes by port
chrome_processes = {}

def is_chrome_debugging_available(port: int = 9222) -> bool:
    """Check if Chrome is already running with remote debugging on specified port"""
    try:
        response = requests.get(f"http://localhost:{port}/json/version")
        return response.status_code == 200
    except requests.RequestException:
        return False

def start_chrome(start_url="https://google.com", port=9222, user_data_dir="/tmp/chrome-debug-profile"):
    """
    Start Chrome with remote debugging enabled
    
    Args:
        start_url (str): The URL to open when Chrome starts. Defaults to Google.
        port (int): Port for Chrome remote debugging.
        user_data_dir (str): Directory for Chrome user data profile.
    """
    global chrome_processes
    
    # Register signal handlers for graceful shutdown if this is the first process
    if not chrome_processes:
        signal.signal(signal.SIGINT, lambda signum, frame: cleanup(signum, frame, exit_process=True))
        signal.signal(signal.SIGTERM, lambda signum, frame: cleanup(signum, frame, exit_process=True))
    
    # Check if Chrome is already running with remote debugging on this port
    if is_chrome_debugging_available(port):
        print(f"Chrome already running with remote debugging on port {port}, using that instead of starting a new instance")
        return
    
    # Close any existing Chrome instances with the debug profile for this port
    try:
        subprocess.run(
            f"pkill -f \"chrome.*--remote-debugging-port={port}\"", 
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
    
    print(f"Starting {chrome_bin} with remote debugging on port {port}...")
    
    # Start Chrome with remote debugging
    chrome_process = subprocess.Popen(
        [
            chrome_bin,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            start_url
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Store the process in our dictionary
    chrome_processes[port] = chrome_process
    
    # Give Chrome time to start and fully load
    print(f"Waiting for Chrome to start and load {start_url} on port {port}...")
    time.sleep(5)

def cleanup(signum=None, frame=None, exit_process=True, port=None):
    """
    Cleanup function to kill Chrome processes. Also serves as a signal handler.
    
    Args:
        signum: Signal number (when used as signal handler)
        frame: Current stack frame (when used as signal handler)
        exit_process (bool): Whether to exit the Python process after cleanup.
                            Set to False when called programmatically.
        port (int): Optional port to specify which Chrome instance to clean up.
                   If None, all Chrome instances will be cleaned up.
    """
    global chrome_processes
    
    # If port is specified, only clean up the specific process
    if port is not None and port in chrome_processes:
        print(f"Shutting down Chrome on port {port}...")
        chrome_process = chrome_processes[port]
        chrome_process.terminate()
        try:
            chrome_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chrome_process.kill()
        # Remove from dictionary after cleanup
        del chrome_processes[port]
    # Otherwise clean up all processes
    elif port is None:
        for port, process in list(chrome_processes.items()):
            print(f"Shutting down Chrome on port {port}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        # Clear the dictionary
        chrome_processes.clear()
    
    # Exit process if requested (typically for signal handlers)
    if exit_process and not chrome_processes:
        sys.exit(0)
    
if __name__ == "__main__":
    start_chrome()