import assemblyai as aai
from openai import OpenAI
import os
import sys
import platform
from dotenv import load_dotenv
import time
import tempfile
import wave
import pyaudio
import threading
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Optional
import pygame
import re

# Load environment variables from .env file
load_dotenv()

# Constants for trigger files
TRIGGER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'triggers')
START_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'start_listening')
STOP_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'stop_listening')
ABORT_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'abort_execution')
STATE_FILE = os.path.join(TRIGGER_DIR, 'listening_state')

@dataclass
class Task:
    audio_file: str
    transcript: Optional[str] = None
    is_processing: bool = False

class AIVoiceAgent:
    def __init__(self, conversation_manager=None):
        # Get API keys from environment variables
        assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        portkey_api_key = os.getenv("PORTKEY_API_KEY")
        portkey_virtual_key = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Check if API keys are available
        if not assemblyai_api_key:
            raise ValueError("AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY in your .env file")
        if not openai_api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        if not portkey_api_key:
            raise ValueError("Portkey API key not found. Please set PORTKEY_API_KEY in your .env file")
        if not portkey_virtual_key:
            raise ValueError("Portkey Virtual Key not found. Please set PORTKEY_VIRTUAL_KEY_ANTHROPIC in your .env file")
            
        aai.settings.api_key = assemblyai_api_key
        # Set OpenAI client
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        # Store conversation manager
        self.conversation_manager = conversation_manager
        
        # Create abort event flag
        self.abort_event = threading.Event()

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

        # Initialize conversation history - no longer needed for web agent
        # as we're not passing conversation history, but keep for record-keeping
        self.full_transcript = [
            {"role": "system", "content": "You are a helpful web browsing assistant called Syri. Provide concise, friendly responses based on your web browsing capabilities."},
        ]

        # Ensure trigger directory exists
        if not os.path.exists(TRIGGER_DIR):
            os.makedirs(TRIGGER_DIR)

        # Clear any existing trigger files
        self._clear_trigger_files()

        # Initialize task queue
        self.task_queue = deque()
        self.queue_lock = threading.Lock()
        self.processing_event = threading.Event()

    def _clear_trigger_files(self):
        """Remove any existing trigger files and initialize state"""
        if os.path.exists(START_TRIGGER_FILE):
            os.remove(START_TRIGGER_FILE)
        if os.path.exists(STOP_TRIGGER_FILE):
            os.remove(STOP_TRIGGER_FILE)
        if os.path.exists(ABORT_TRIGGER_FILE):
            os.remove(ABORT_TRIGGER_FILE)

        # Initialize state to inactive when server starts
        with open(STATE_FILE, 'w') as f:
            f.write("inactive")

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

    def record_audio(self):
        """Record audio until a stop trigger file is created"""
        self._wait_for_start_trigger()
        
        print("Recording... Create a stop trigger file to stop.")
        
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
            return self._record_with_callback(input_device_index, default_rate)
        else:
            # Try callback first, fall back to blocking mode if needed
            result = self._record_with_callback(input_device_index, default_rate)
            if result:
                return result
            else:
                return self._record_with_blocking(input_device_index, default_rate)

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

    def _wait_for_start_trigger(self):
        """Wait for a start trigger file to be created"""
        while not os.path.exists(START_TRIGGER_FILE):
            time.sleep(0.5)

        # Remove the start trigger file once detected
        os.remove(START_TRIGGER_FILE)

    def _check_stop_trigger(self):
        """Check if a stop trigger file exists"""
        if os.path.exists(STOP_TRIGGER_FILE):
            # Remove the stop trigger file once detected
            os.remove(STOP_TRIGGER_FILE)
            return True
        return False

    def _record_with_callback(self, input_device_index, sample_rate):
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
                    if self._check_stop_trigger():
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
                return self._record_with_blocking(input_device_index, sample_rate)
            return None

    def _record_with_blocking(self, input_device_index, sample_rate):
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
                            if self._check_stop_trigger():
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

    def transcribe_audio(self, audio_file):
        """
        Transcribe the recorded audio using AssemblyAI

        Returns:
            str: The transcribed text
        """
        if not audio_file:
            return None

        print("Transcribing audio...")

        # Create a transcriber and set a language model to get formatting
        transcriber = aai.Transcriber()

        # Start the transcription
        try:
            transcript = transcriber.transcribe(audio_file)
            print("Audio transcription successful\n")
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
        
        # Delete the temporary file
        try:
            os.unlink(audio_file)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {audio_file}: {e}")
        
        return transcript.text
    
    def check_abort_trigger(self):
        """Check if abort trigger file exists"""
        if os.path.exists(ABORT_TRIGGER_FILE):
            # Remove the trigger file
            try:
                os.remove(ABORT_TRIGGER_FILE)
            except Exception:
                pass
            return True
        return False

    def abort_current_execution(self):
        """Abort current execution by setting the abort event"""
        print("\nAborting current execution...", flush=True)
        self.abort_event.set()
        # Reset the abort event after a short delay to allow tasks to be aborted
        threading.Timer(1.0, self.abort_event.clear).start()
        
        # Stop the current web agent if it exists
        active_conversation = self.conversation_manager.get_active_conversation()
        if active_conversation and active_conversation.agent:
            active_conversation.agent.stop()

    def _check_for_new_conversation(self, transcript_text):
        """Check if the user wants to start a new conversation"""
        # Check for phrases like "new conversation", "start new conversation", etc.
        new_conversation_patterns = [
            r'\bnew conversation\b',
            r'\bstart (?:a )?new conversation\b',
            r'\bcreate (?:a )?new conversation\b',
            r'\bopen (?:a )?new conversation\b',
            r'\bbegin (?:a )?new conversation\b'
        ]
        
        # Check if any pattern matches
        for pattern in new_conversation_patterns:
            if re.search(pattern, transcript_text.lower()):
                return True
                
        return False

    def _check_for_switch_conversation(self, transcript_text):
        """Check if the user wants to switch to a specific conversation"""
        # Look for patterns like "switch to conversation 1" or "go to session 2"
        switch_patterns = [
            r'switch to (?:conversation|session) (\d+)',
            r'go to (?:conversation|session) (\d+)',
            r'open (?:conversation|session) (\d+)',
            r'use (?:conversation|session) (\d+)'
        ]
        
        # Check if any pattern matches and get the session number from digits
        for pattern in switch_patterns:
            match = re.search(pattern, transcript_text.lower())
            if match:
                try:
                    session_num = int(match.group(1))
                    return session_num
                except (ValueError, IndexError):
                    pass
        
        # Look for patterns with numbers as words
        word_number_patterns = [
            r'switch to (?:conversation|session) (one|two|three|four|five|six|seven|eight|nine|ten)',
            r'go to (?:conversation|session) (one|two|three|four|five|six|seven|eight|nine|ten)',
            r'open (?:conversation|session) (one|two|three|four|five|six|seven|eight|nine|ten)',
            r'use (?:conversation|session) (one|two|three|four|five|six|seven|eight|nine|ten)'
        ]
        
        # Map word numbers to integers
        word_to_number = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }
        
        # Check for word number patterns
        for pattern in word_number_patterns:
            match = re.search(pattern, transcript_text.lower())
            if match:
                try:
                    word_num = match.group(1).lower()
                    if word_num in word_to_number:
                        return word_to_number[word_num]
                except (IndexError):
                    pass
                
        return None

    async def generate_ai_response(self, transcript_text):
        """Generate AI response using the conversation manager and web agent"""
        self.full_transcript.append({"role": "user", "content": transcript_text})
        print(f"\nUser: {transcript_text}")

        # Reset abort event before starting
        self.abort_event.clear()
        
        # Check if the user wants to start a new conversation
        if self._check_for_new_conversation(transcript_text):
            # Create a new conversation
            session_id = self.conversation_manager.create_conversation()
            response_text = f"Created new conversation with ID {session_id}. You are now using this conversation."
            print(f"\nNew conversation: {response_text}")
            
            # Run TTS to confirm the new conversation
            tts_thread = threading.Thread(
                target=self._generate_and_play_tts,
                args=(response_text,),
                daemon=True
            )
            tts_thread.start()
            
            self.full_transcript.append({"role": "assistant", "content": response_text})
            return
            
        # Check if the user wants to switch to a specific conversation
        session_num = self._check_for_switch_conversation(transcript_text)
        if session_num is not None:
            # Get all available session IDs
            session_ids = self.conversation_manager.get_conversation_ids()
            
            # Check if the requested session exists
            if session_num <= len(session_ids) and session_num > 0:
                # Switch to the requested conversation (adjust for 0-based indexing)
                target_session_id = session_ids[session_num - 1]
                self.conversation_manager.switch_conversation(target_session_id)
                response_text = f"Switched to conversation {session_num} (ID: {target_session_id})"
            else:
                response_text = f"Could not find conversation {session_num}. Available conversations: {len(session_ids)}"
            
            print(f"\nSwitch conversation: {response_text}")
            
            # Run TTS to confirm the switch
            tts_thread = threading.Thread(
                target=self._generate_and_play_tts,
                args=(response_text,),
                daemon=True
            )
            tts_thread.start()
            
            self.full_transcript.append({"role": "assistant", "content": response_text})
            return
            
        # Get the active web agent conversation
        active_conversation = self.conversation_manager.get_active_conversation()
        if not active_conversation:
            response_text = "No active conversation available. Please create a new conversation."
            print(f"\nNo conversation: {response_text}")
            
            # Run TTS to indicate the error
            tts_thread = threading.Thread(
                target=self._generate_and_play_tts,
                args=(response_text,),
                daemon=True
            )
            tts_thread.start()
            
            self.full_transcript.append({"role": "assistant", "content": response_text})
            return

        print("\nWeb Agent Response:", flush=True)
        
        # Start a thread to monitor for abort signal during web agent processing
        abort_monitor = threading.Thread(target=self._monitor_abort_during_task)
        abort_monitor.daemon = True
        abort_monitor.start()
        
        try:
            # Use the active web agent conversation with await
            response_text = await active_conversation.run(transcript_text)
            
            # If task was aborted, return early
            if self.abort_event.is_set():
                print("\nTask aborted before TTS generation", flush=True)
                return
            
            print(response_text, flush=True)
            
            # Run TTS in a separate thread
            tts_thread = threading.Thread(
                target=self._generate_and_play_tts,
                args=(response_text,),
                daemon=True
            )
            tts_thread.start()
            
            print()  # Add a newline after response
            self.full_transcript.append({"role": "assistant", "content": response_text})
        except Exception as e:
            print(f"\nError during AI response generation: {e}", flush=True)

    def _generate_and_play_tts(self, text):
        """Generate and play TTS in a separate thread"""
        try:
            # Get speech speed from environment variable (default to 1.2 if not set)
            speech_speed = float(os.getenv("SYRI_TTS_SPEED", 1.2))
            print(f"Using speech speed: {speech_speed}x", flush=True)
            
            # Get TTS voice from environment variable (default to "coral")
            tts_voice = os.getenv("SYRI_TTS_VOICE", "coral")
            print(f"Using voice: {tts_voice}", flush=True)
            
            # Create a temporary file for the audio
            temp_audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_audio_path = temp_audio_file.name
            temp_audio_file.close()
            
            # Generate TTS using OpenAI's TTS API
            response = self.openai_client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=tts_voice,
                input=text,
                speed=speech_speed
            )
            
            # Save the audio to the temp file
            response.stream_to_file(temp_audio_path)
            
            # Play the audio with abort check capability
            self._play_audio_with_abort_check(temp_audio_path)
            
            # Clean up temp file after playback
            try:
                os.unlink(temp_audio_path)
            except Exception as e:
                print(f"\nWarning: Could not delete temporary audio file: {e}", flush=True)
            
        except Exception as e:
            print(f"\nError during TTS generation and playback: {e}", flush=True)

    def _play_audio_with_abort_check(self, audio_file_path):
        """Play audio file with periodic checks for abort signal using pygame"""
        try:
            # Load the audio file
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play()
            
            # Check for abort while playing
            while pygame.mixer.music.get_busy():
                if self.abort_event.is_set() or self.check_abort_trigger():
                    # If abort signal detected, stop playback
                    if not self.abort_event.is_set():
                        self.abort_current_execution()
                    pygame.mixer.music.stop()
                    print("\nTTS playback aborted", flush=True)
                    break
                # Small delay to prevent high CPU usage
                time.sleep(0.1)
            
        except Exception as e:
            print(f"\nError during audio playback: {e}", flush=True)

    def _monitor_abort_during_task(self):
        """Monitor for abort signal during task execution"""
        while not self.abort_event.is_set():
            if self.check_abort_trigger():
                self.abort_current_execution()
                break
            time.sleep(0.2)  # Check every 200ms

    def _stream_with_abort_check(self, audio_stream):
        """
        Legacy method maintained for compatibility.
        This redirects to the new audio playback method.
        """
        print("\nWarning: Using legacy streaming method. This is no longer active with OpenAI TTS.", flush=True)

    def _check_chrome_installed(self):
        """Check if Chrome is installed and available"""
        import shutil
        
        chrome_paths = {
            'Darwin': ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'],
            'Linux': ['google-chrome', 'chrome', 'chromium', 'chromium-browser'],
            'Windows': ['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 
                       'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe']
        }
        
        if self.system in chrome_paths:
            if self.system == 'Darwin' or self.system == 'Windows':  # Direct path check for Mac/Windows
                for path in chrome_paths[self.system]:
                    if os.path.exists(path):
                        return True
            else:  # Linux - use which to find in PATH
                for browser in chrome_paths[self.system]:
                    if shutil.which(browser):
                        return True
                        
        print("Warning: Chrome browser not found. The web agent requires Chrome to be installed.")
        return False

    async def start_session(self):
        """Start the voice assistant session asynchronously"""
        print("Syri Voice Assistant started and ready to listen 🟢")
        print("  • Press Enter to toggle between start/stop recording")
        print("  • ./scripts/start_listening.sh - Start recording")
        print("  • ./scripts/stop_listening.sh - Stop recording and process request")
        print("  • ./scripts/toggle_listening.sh - Toggle between start/stop")
        print("  • ./scripts/abort_execution.sh - Abort current task or TTS")
        print("  • Say \"new conversation\" to create a new conversation")
        print("  • Say \"switch to conversation X\" to switch between conversations")
        print("  • Numbers can be digits (1, 2, 3) or words (one, two, three)")
        
        # Check if Chrome is installed
        if not self._check_chrome_installed():
            print("Chrome is required for the web agent functionality.")
            print("Please install Chrome and try again.")
            return
        
        try:
            # Create an event to signal stopping the session
            stop_session = threading.Event()
            
            def handle_keyboard_input():
                while not stop_session.is_set():
                    try:
                        input()  # Wait for Enter key
                        if os.path.exists(STATE_FILE):
                            with open(STATE_FILE, 'r') as f:
                                current_state = f.read().strip()
                            
                            # If already running a task, abort it
                            if self.abort_event.is_set():
                                print("Already aborting a task. Please wait...")
                                continue
                            
                            # Check if we're currently recording
                            if current_state == "active":
                                # Stop recording
                                with open(STATE_FILE, 'w') as f:
                                    f.write("inactive")
                                touch_file = os.path.join(TRIGGER_DIR, "stop_listening")
                            else:
                                # Start recording (regardless of processing state)
                                with open(STATE_FILE, 'w') as f:
                                    f.write("active")
                                touch_file = os.path.join(TRIGGER_DIR, "start_listening")
                                
                            # Create the appropriate trigger file
                            with open(touch_file, 'w') as f:
                                pass
                    except EOFError:
                        break
            
            # Start keyboard input thread
            keyboard_thread = threading.Thread(target=handle_keyboard_input)
            keyboard_thread.daemon = True
            keyboard_thread.start()

            # Start task processing thread
            process_thread = threading.Thread(target=lambda: asyncio.run(self._process_tasks()))
            process_thread.daemon = True
            process_thread.start()
            
            while True:
                # Record audio
                audio_file = self.record_audio()
                
                if audio_file:
                    # Add task to queue
                    with self.queue_lock:
                        task = Task(audio_file=audio_file)
                        self.task_queue.append(task)
                        print(f"\nTask added to queue. Queue length: {len(self.task_queue)}")
                    
                    # Signal that there's a new task to process
                    self.processing_event.set()
                
                # Reset state to inactive after recording
                with open(STATE_FILE, 'w') as f:
                    f.write("inactive")
                
        except KeyboardInterrupt:
            print("\nExiting Syri Voice Assistant...")
            stop_session.set()  # Signal the keyboard thread to stop
        except Exception as e:
            print(f"Error: {e}")
            stop_session.set()  # Signal the keyboard thread to stop
        finally:
            # Clean up PyAudio
            self.p.terminate()
            
            # Clean up all conversations
            if self.conversation_manager:
                asyncio.run(self.conversation_manager.cleanup_all())

    async def _process_tasks(self):
        """Process tasks from the queue"""
        while True:
            # Wait for tasks to be available
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
            
            if not self.task_queue:
                self.processing_event.clear()
                await asyncio.to_thread(self.processing_event.wait)
                continue
            
            # Get next task
            with self.queue_lock:
                task = self.task_queue[0]
                task.is_processing = True
            
            try:
                # Set state to processing
                with open(STATE_FILE, 'w') as f:
                    f.write("processing")
                
                # Monitor for abort during transcription and processing
                abort_monitor = threading.Thread(target=self._monitor_abort_during_task)
                abort_monitor.daemon = True
                abort_monitor.start()
                
                # Transcribe audio
                transcript_text = self.transcribe_audio(task.audio_file)
                task.transcript = transcript_text
                
                # Check if aborted during transcription
                if self.abort_event.is_set():
                    print("\nAborted during transcription", flush=True)
                    self.abort_event.clear()
                    with self.queue_lock:
                        self.task_queue.popleft()
                    continue
                
                if not transcript_text or transcript_text.strip() == "":
                    print("No speech detected. Skipping task.")
                    with self.queue_lock:
                        self.task_queue.popleft()
                    continue
                
                # Speak confirmation message with transcript in a separate thread
                threading.Thread(
                    target=self._speak_confirmation_message,
                    args=(transcript_text,),
                    daemon=True
                ).start()
                
                # Generate AI response asynchronously
                await self.generate_ai_response(transcript_text)
                
                # Remove completed task from queue
                with self.queue_lock:
                    self.task_queue.popleft()
                
            except Exception as e:
                print(f"Error processing task: {e}")
                with self.queue_lock:
                    self.task_queue.popleft()
            finally:
                # Reset state to inactive after processing
                with open(STATE_FILE, 'w') as f:
                    f.write("inactive")

    def _speak_confirmation_message(self, transcript_text):
        """Speak a confirmation message with the transcript in a separate thread"""
        print("Speaking confirmation message...", flush=True)
        confirmation_text = f"Message received: {transcript_text}"
        
        # Run TTS in a separate thread
        self._generate_and_play_tts(confirmation_text)


# Direct execution of the script
if __name__ == "__main__":
    try:
        print("Running Syri agent directly. For a better experience, use: python run.py")
        from src.browser_agent.web_agent import ConversationManager
        
        # Create conversation manager and initialize first conversation
        conversation_manager = ConversationManager()
        conversation_manager.create_conversation()
        
        ai_voice_agent = AIVoiceAgent(conversation_manager=conversation_manager)
        asyncio.run(ai_voice_agent.start_session())
        
    except KeyboardInterrupt:
        print("\nExiting Syri Voice Assistant...")
    except Exception as e:
        print(f"Error: {e}")