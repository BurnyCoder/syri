"""
System-specific helper functions for the Syri Voice Assistant.
"""
import os
import sys
import platform


def suppress_audio_errors():
    """Suppress error messages from audio backends in a platform-appropriate way.
    
    Returns:
        tuple: Information needed to restore stderr later
    """
    system = platform.system()
    
    if system == 'Linux':
        # Linux-specific error suppression
        errorfile = os.open('/dev/null', os.O_WRONLY)
        old_stderr = os.dup(2)
        sys.stderr.flush()
        os.dup2(errorfile, 2)
        os.close(errorfile)
        return {'system': system, 'old_stderr': old_stderr}
    else:
        # For Mac/Windows, we use a different approach
        # Store the old stderr
        old_stderr_target = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        return {'system': system, 'old_stderr_target': old_stderr_target}


def restore_stderr(stderr_info):
    """Restore stderr to its original state.
    
    Args:
        stderr_info (dict): Information returned from suppress_audio_errors
    """
    system = stderr_info.get('system')
    
    if system == 'Linux' and 'old_stderr' in stderr_info:
        # Linux-specific restoration
        os.dup2(stderr_info['old_stderr'], 2)
        os.close(stderr_info['old_stderr'])
    elif 'old_stderr_target' in stderr_info:
        # Mac/Windows restoration
        sys.stderr.close()  # Close the null device
        sys.stderr = stderr_info['old_stderr_target']


def detect_platform():
    """Detect the operating system.
    
    Returns:
        str: The name of the operating system
    """
    return platform.system()


def check_chrome_installed():
    """Check if Chrome is installed and available.
    
    Returns:
        bool: True if Chrome is installed, False otherwise
    """
    import shutil
    
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
                    
    return False