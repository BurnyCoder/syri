import os
import platform
import subprocess
import shutil

def check_chrome_installed():
    """Check if Chrome is installed and available"""
    system = platform.system()
    
    chrome_paths = {
        'Darwin': ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'],
        'Linux': ['google-chrome', 'chrome', 'chromium', 'chromium-browser'],
        'Windows': ['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 
                   'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe']
    }
    
    if system in chrome_paths:
        if system == 'Darwin' or system == 'Windows':  # Direct path check for Mac/Windows
            for path in chrome_paths[system]:
                if os.path.exists(path):
                    return True
        else:  # Linux - use which to find in PATH
            for browser in chrome_paths[system]:
                if shutil.which(browser):
                    return True
                    
    print("Warning: Chrome browser not found. The web agent requires Chrome to be installed.")
    return False

def display_welcome():
    """Display welcome message and instructions."""
    print("\n" + "=" * 50)
    print(" 🎤  Syri Voice Assistant 🔊")
    print("=" * 50)
    print("\nThis assistant uses:")
    print("  • AssemblyAI for speech-to-text")
    print("  • Web browser agent (with Claude 3.7 Sonnet) for AI processing")
    print("  • OpenAI TTS for text-to-speech")
    print("\nStarting up...")

def monitor_abort_during_task(abort_check_func):
    """
    Monitor for abort signal during task execution.
    
    Args:
        abort_check_func: Function to check for abort signal
    """
    import threading
    import time
    
    def monitor_thread():
        while True:
            if abort_check_func():
                break
            time.sleep(0.2)  # Check every 200ms
    
    thread = threading.Thread(target=monitor_thread)
    thread.daemon = True
    thread.start()
    return thread