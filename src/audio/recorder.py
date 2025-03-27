import os
import sys
import time
import platform
import tempfile
import wave
import threading
import pyaudio

class AudioRecorder:
    """Handles audio recording with platform-specific optimizations."""
    def __init__(self):
        # Detect operating system
        self.system = platform.system()
        print(f"Detected operating system: {self.system}")
        
        # Audio recording settings (OS-specific defaults)
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        
        # Mac typically works better with 44100 Hz, Linux depends on hardware
        if self.system == 'Darwin':  # macOS
            self.rate = 44100
        else:  # Linux and others
            self.rate = 44100  # Default, will be adjusted based on device
        
        # Suppress error messages from audio backends
        self._suppress_audio_errors()
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
        # Restore stderr
        self._restore_stderr()

    def _suppress_audio_errors(self):
        """Suppress error messages from audio backends in a platform-appropriate way"""
        if self.system == 'Linux':
            # Linux-specific error suppression
            errorfile = os.open('/dev/null', os.O_WRONLY)
            self.old_stderr = os.dup(2)
            sys.stderr.flush()
            os.dup2(errorfile, 2)
            os.close(errorfile)
        else:
            # For Mac/Windows, we use a different approach
            # Store the old stderr
            self.old_stderr_target = sys.stderr
            sys.stderr = open(os.devnull, 'w')
    
    def _restore_stderr(self):
        """Restore stderr to its original state"""
        if self.system == 'Linux' and hasattr(self, 'old_stderr'):
            # Linux-specific restoration
            os.dup2(self.old_stderr, 2)
            os.close(self.old_stderr)
        elif hasattr(self, 'old_stderr_target'):
            # Mac/Windows restoration
            sys.stderr.close()  # Close the null device
            sys.stderr = self.old_stderr_target

    def record_audio(self, trigger_check_func=None):
        """Record audio until a stop trigger is detected"""
        # Find the correct input device index and optimal configuration
        # based on detected operating system
        input_device_index = self._select_best_audio_device()
        
        if input_device_index is None:
            print("No suitable input devices found. Please check your microphone connection.")
            return None
        
        # Get the default rate for the selected device
        device_info = self.p.get_device_info_by_index(input_device_index)
        default_rate = int(device_info.get('defaultSampleRate'))
        print(f"Using sample rate: {default_rate} Hz")
        
        # For Mac, the callback method usually works better
        # For Linux, we'll try callback first, then fall back to blocking mode if needed
        if self.system == 'Darwin':  # macOS
            return self._record_with_callback(input_device_index, default_rate, trigger_check_func)
        else:
            # Try callback first, fall back to blocking mode if needed
            result = self._record_with_callback(input_device_index, default_rate, trigger_check_func)
            if result:
                return result
            else:
                return self._record_with_blocking(input_device_index, default_rate, trigger_check_func)

    def _select_best_audio_device(self):
        """Select the best audio input device based on the platform"""
        input_device_index = None
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        # Print available audio devices for debugging
        print("\nAvailable audio devices:")
        preferred_keywords = []
        
        # Platform-specific preferred devices
        if self.system == 'Darwin':  # macOS
            preferred_keywords = ['built-in', 'microphone', 'input']
        else:  # Linux
            preferred_keywords = ['hw', 'mic', 'pulse', 'default']
        
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:  # if it's an input device
                device_name = str(device_info.get('name')).lower()
                print(f"Input Device {i}: {device_info.get('name')}")
                
                # Set first found device as fallback
                if input_device_index is None:
                    input_device_index = i
                
                # Check for platform-specific preferred devices
                if self.system == 'Linux' and "hw:1,0" in device_name:
                    input_device_index = i
                    print(f"Selected Linux hardware device: {device_info.get('name')}")
                    break
                elif self.system == 'Darwin':  # macOS
                    for keyword in preferred_keywords:
                        if keyword in device_name:
                            input_device_index = i
                            print(f"Selected Mac input device: {device_info.get('name')}")
                            return input_device_index
                
                # For Linux, check other preferences if hw device not found
                if self.system == 'Linux':
                    for keyword in preferred_keywords:
                        if keyword in device_name:
                            input_device_index = i
                            print(f"Selected input device: {device_info.get('name')}")
        
        return input_device_index

    def _record_with_callback(self, input_device_index, sample_rate, trigger_check_func):
        """Record audio using callback method (preferred for Mac)"""
        frames = []
        is_recording = True
        
        # Callback function for audio recording
        def audio_callback(in_data, frame_count, time_info, status):
            if is_recording:
                frames.append(in_data)
            return (None, pyaudio.paContinue)
        
        try:
            # Open audio stream with callback
            stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=sample_rate,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.chunk,
                stream_callback=audio_callback
            )
            
            stream.start_stream()
            
            # Start a thread to check for stop trigger
            stop_recording = threading.Event()
            
            def check_for_stop():
                while not stop_recording.is_set():
                    if trigger_check_func and trigger_check_func():
                        stop_recording.set()
                        break
                    time.sleep(0.5)
            
            stop_thread = threading.Thread(target=check_for_stop)
            stop_thread.daemon = True
            stop_thread.start()
            
            # Wait for stop signal
            while stream.is_active() and not stop_recording.is_set():
                time.sleep(0.1)
            
            # Set recording flag to False to stop capturing in callback
            is_recording = False
            
            # Give a small delay to allow callback to finish any in-progress operations
            time.sleep(0.5)
            
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            
            # Check if we captured any audio
            if not frames:
                print("No audio captured with callback method")
                return None
                
            # Create and return temporary audio file
            return self._save_audio_to_file(frames, sample_rate)
            
        except Exception as e:
            print(f"Error with callback recording: {e}")
            if self.system == 'Darwin':  # For Mac, try the blocking method as fallback
                print("Falling back to blocking mode...")
                return self._record_with_blocking(input_device_index, sample_rate, trigger_check_func)
            return None

    def _record_with_blocking(self, input_device_index, sample_rate, trigger_check_func):
        """Record audio using blocking method (fallback method)"""
        frames = []
        
        try:
            # Try different sample rates if needed
            rates_to_try = [sample_rate]
            if sample_rate != 44100:
                rates_to_try.append(44100)
            if sample_rate != 16000:
                rates_to_try.append(16000)
            
            # Try each rate until one works
            for rate in rates_to_try:
                try:
                    print(f"Trying with sample rate: {rate} Hz")

                    # Open audio stream in blocking mode
                    stream = self.p.open(
                        format=self.format,
                        channels=self.channels,
                        rate=rate,
                        input=True,
                        input_device_index=input_device_index,
                        frames_per_buffer=self.chunk
                    )
                    
                    # Start a thread to check for stop trigger
                    stop_recording = threading.Event()
                    
                    def check_for_stop():
                        while not stop_recording.is_set():
                            if trigger_check_func and trigger_check_func():
                                stop_recording.set()
                                break
                            time.sleep(0.5)
                    
                    stop_thread = threading.Thread(target=check_for_stop)
                    stop_thread.daemon = True
                    stop_thread.start()
                    
                    # Clear frames array
                    frames = []

                    # Recording loop
                    while not stop_recording.is_set():
                        try:
                            data = stream.read(self.chunk, exception_on_overflow=False)
                            frames.append(data)
                        except Exception as e:
                            print(f"Error reading from audio stream: {e}")
                            break
                    
                    # Stop and close the stream
                    stream.stop_stream()
                    stream.close()
                    
                    # If we captured any audio, break out of the rate testing loop
                    if frames:
                        return self._save_audio_to_file(frames, rate)

                except Exception as e:
                    print(f"Error with sample rate {rate} Hz: {e}")

            # If we get here, none of the sample rates worked
            print("Could not record audio with any sample rate")
            return None
            
        except Exception as e:
            print(f"Error with blocking recording: {e}")
            return None

    def _save_audio_to_file(self, frames, sample_rate):
        """Save recorded audio frames to a temporary WAV file"""
        if not frames:
            print("No audio frames to save")
            return None
            
        # Create a temporary file with a proper extension
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        # Write the audio data to the temporary file
        with wave.open(temp_filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))
        
        print(f"Audio recorded and saved to temporary file: {temp_filename}")
        return temp_filename
        
    def cleanup(self):
        """Clean up PyAudio resources"""
        if hasattr(self, 'p'):
            self.p.terminate()