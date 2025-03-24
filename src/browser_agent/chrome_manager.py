#!/usr/bin/env python3
import os
import platform
import subprocess
import sys
import time
import signal
import requests
from typing import Optional, Dict

# Global variable to track Chrome processes
chrome_processes: Dict[int, subprocess.Popen] = {}

def is_chrome_debugging_available(port: int = 9222) -> bool:
    """Check if Chrome is already running with remote debugging on specified port"""
    try:
        response = requests.get(f"http://localhost:{port}/json/version")
        return response.status_code == 200
    except requests.RequestException:
        return False

def start_chrome(start_url="https://google.com", port: int = 9222):
    """
    Start Chrome with remote debugging enabled
    
    Args:
        start_url (str): The URL to open when Chrome starts. Defaults to Google.
        port (int): The port to use for remote debugging. Defaults to 9222.
    """
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Check if Chrome is already running with remote debugging on this port
    if is_chrome_debugging_available(port):
        print(f"Chrome already running with remote debugging on port {port}, using that instead of starting a new instance")
        return

    # Close any existing Chrome instances with this debug port
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
            f"--user-data-dir=/tmp/chrome-debug-profile-{port}",
            start_url
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Store the process in our global dictionary
    chrome_processes[port] = chrome_process
    
    # Give Chrome time to start and fully load
    print(f"Waiting for Chrome to start and load {start_url}...")
    time.sleep(5)

def cleanup(signum=None, frame=None, exit_process=True, port: Optional[int] = None):
    """
    Cleanup function to kill Chrome process(es). Also serves as a signal handler.
    
    Args:
        signum: Signal number (when used as signal handler)
        frame: Current stack frame (when used as signal handler)
        exit_process (bool): Whether to exit the Python process after cleanup.
                            Set to False when called programmatically.
        port (int, optional): Specific port to clean up. If None, cleans up all ports.
    """
    global chrome_processes
    
    if port is not None:
        # Clean up specific port
        if port in chrome_processes:
            print(f"Shutting down Chrome on port {port}...")
            chrome_processes[port].terminate()
            try:
                chrome_processes[port].wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome_processes[port].kill()
            del chrome_processes[port]
    else:
        # Clean up all ports
        for port, process in chrome_processes.items():
            print(f"Shutting down Chrome on port {port}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        chrome_processes.clear()
    
    if exit_process:
        sys.exit(0)

if __name__ == "__main__":
    start_chrome()