import assemblyai as aai
import elevenlabs
from elevenlabs import stream, set_api_key
import os
from dotenv import load_dotenv
from src.portkey import claude37sonnet
import time
import tempfile
import wave
import pyaudio
import threading

# Load environment variables from .env file
load_dotenv()


class AIVoiceAgent:
    def __init__(self):
        # Get API keys from environment variables
        assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        portkey_api_key = os.getenv("PORTKEY_API_KEY")
        portkey_virtual_key = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Check if API keys are available
        if not assemblyai_api_key:
            raise ValueError("AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY in your .env file")
        if not elevenlabs_api_key:
            raise ValueError("ElevenLabs API key not found. Please set ELEVENLABS_API_KEY in your .env file")
        if not portkey_api_key:
            raise ValueError("Portkey API key not found. Please set PORTKEY_API_KEY in your .env file")
        if not portkey_virtual_key:
            raise ValueError("Portkey Virtual Key not found. Please set PORTKEY_VIRTUAL_KEY_ANTHROPIC in your .env file")
            
        aai.settings.api_key = assemblyai_api_key
        # Set ElevenLabs API key
        set_api_key(elevenlabs_api_key)
        
        # Audio recording settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100  # Using a standard CD quality rate that's widely supported
        
        # Suppress error messages from ALSA
        import sys
        # No need to reimport os as it's already imported at the top
        errorfile = os.open('/dev/null', os.O_WRONLY)
        old_stderr = os.dup(2)
        sys.stderr.flush()
        os.dup2(errorfile, 2)
        os.close(errorfile)
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
        # Restore stderr
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

        self.full_transcript = [
            {"role": "system", "content": "You are a helpful AI assistant called Syri. Provide concise, friendly responses under 300 characters."},
        ]

    def record_audio(self):
        """Record audio until the user presses Enter"""
        print("\nPress Enter to start recording...")
        input()  # Wait for Enter to start recording
        
        print("Recording... Press Enter to stop.")
        
        # Find the correct input device index
        input_device_index = None
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        # Print available audio devices for debugging
        print("\nAvailable audio devices:")
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:  # if it's an input device
                print(f"Input Device {i}: {device_info.get('name')}")
                # Use the first available input device
                if input_device_index is None:
                    input_device_index = i
                # If we find the hardware device, prefer to use it
                if "hw:1,0" in str(device_info.get('name')):
                    input_device_index = i
                    print(f"Selected hardware device: {device_info.get('name')}")
        
        if input_device_index is None:
            print("No input devices found. Please check your microphone connection.")
            return None
            
        # Get the default rate for the selected device
        device_info = self.p.get_device_info_by_index(input_device_index)
        default_rate = int(device_info.get('defaultSampleRate'))
        
        print(f"Using sample rate: {default_rate} Hz")
        
        # Use callback-based recording which is more reliable
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
                rate=default_rate,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.chunk,
                stream_callback=audio_callback
            )
            
            stream.start_stream()
            
            # Start a non-blocking input thread
            stop_recording = threading.Event()
            
            def wait_for_enter():
                input()  # Wait for Enter to stop recording
                stop_recording.set()
            
            input_thread = threading.Thread(target=wait_for_enter)
            input_thread.daemon = True
            input_thread.start()
            
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
            
        except Exception as e:
            print(f"Error setting up audio stream with callback: {e}")
            print("Falling back to blocking mode...")
            
            # Fallback to blocking mode with overflow handling
            try:
                # Open audio stream with explicit device index and device-specific sample rate
                stream = self.p.open(
                    format=self.format,
                    channels=self.channels,
                    rate=default_rate,
                    input=True,
                    input_device_index=input_device_index,
                    frames_per_buffer=self.chunk
                )
                
                # Start a non-blocking input thread
                stop_recording = threading.Event()
                
                def wait_for_enter():
                    input()  # Wait for Enter to stop recording
                    stop_recording.set()
                
                input_thread = threading.Thread(target=wait_for_enter)
                input_thread.daemon = True
                input_thread.start()
                
                # Record audio using blocking mode but ignore overflow errors
                while not stop_recording.is_set():
                    try:
                        # Set exception_on_overflow=False to prevent the error
                        data = stream.read(self.chunk, exception_on_overflow=False)
                        frames.append(data)
                    except Exception as e:
                        if "overflowed" not in str(e).lower():  # Only print if it's not an overflow error
                            print(f"Error reading from audio stream: {e}")
                        # Continue recording despite errors
                
                # Stop and close the stream
                stream.stop_stream()
                stream.close()
                
            except Exception as fallback_error:
                print(f"Error in fallback recording mode: {fallback_error}")
                # Try standard rates in descending order of quality
                standard_rates = [48000, 44100, 22050, 11025, 8000]
                stream = None
                
                for rate in standard_rates:
                    try:
                        stream = self.p.open(
                            format=self.format,
                            channels=self.channels,
                            rate=rate,
                            input=True,
                            input_device_index=input_device_index,
                            frames_per_buffer=self.chunk
                        )
                        print(f"Successfully opened stream with rate: {rate} Hz")
                        default_rate = rate  # Update rate for WAV file
                        
                        # Start a non-blocking input thread
                        stop_recording = threading.Event()
                        
                        def wait_for_enter():
                            input()  # Wait for Enter to stop recording
                            stop_recording.set()
                        
                        input_thread = threading.Thread(target=wait_for_enter)
                        input_thread.daemon = True
                        input_thread.start()
                        
                        # Record audio using blocking mode but ignore overflow errors
                        while not stop_recording.is_set():
                            try:
                                # Set exception_on_overflow=False to prevent the error
                                data = stream.read(self.chunk, exception_on_overflow=False)
                                frames.append(data)
                            except Exception as e:
                                if "overflowed" not in str(e).lower():
                                    print(f"Error reading from audio stream: {e}")
                                # Continue recording despite errors
                        
                        # Stop and close the stream
                        stream.stop_stream()
                        stream.close()
                        break
                    except Exception as audio_error:
                        print(f"Failed with rate {rate} Hz: {audio_error}")
                
                if stream is None:
                    print("Could not open audio stream with any standard rate. Please check your audio configuration.")
                    return None
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
        
        # Save the recorded audio as a WAV file
        wf = wave.open(temp_filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(default_rate)  # Use the actual rate we recorded with
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"Recorded {len(frames)} audio chunks")
        return temp_filename

    def transcribe_audio(self, audio_file):
        """Transcribe the recorded audio file"""
        print("Transcribing audio...")
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file)
        
        # Delete the temporary file
        try:
            os.unlink(audio_file)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {audio_file}: {e}")
        
        return transcript.text
    
    def generate_ai_response(self, transcript_text):
        self.full_transcript.append({"role": "user", "content": transcript_text})
        print(f"\nUser: {transcript_text}")

        print("\nClaude 3.7 Sonnet:", flush=True)
        
        # Get response from Claude 3.7 Sonnet using the full conversation history
        response_text = claude37sonnet(self.full_transcript)
        
        # Break the response into sentences for streaming audio
        sentences = []
        temp = ""
        for char in response_text:
            temp += char
            if char in ['.', '!', '?'] and len(temp.strip()) > 0:
                sentences.append(temp)
                temp = ""
        
        if temp:  # Add any remaining text
            sentences.append(temp)
        
        full_text = ""
        # Process each sentence
        for sentence in sentences:
            audio_stream = elevenlabs.generate(
                text=sentence,
                model="eleven_turbo_v2",
                stream=True
            )
            print(sentence, end="", flush=True)
            stream(audio_stream)
            full_text += sentence
        
        print()  # Add a newline after response
        self.full_transcript.append({"role": "assistant", "content": full_text})

    def start_session(self):
        """Start the voice assistant session"""
        print("Syri Voice Assistant started. Press Enter to speak, then Enter again when done.")
        
        try:
            while True:
                # Record audio
                audio_file = self.record_audio()
                
                # Transcribe audio
                transcript_text = self.transcribe_audio(audio_file)
                
                if not transcript_text or transcript_text.strip() == "":
                    print("No speech detected. Please try again.")
                    continue
                
                # Generate AI response
                self.generate_ai_response(transcript_text)
                
        except KeyboardInterrupt:
            print("\nExiting Syri Voice Assistant...")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Clean up PyAudio
            self.p.terminate()


# Direct execution of the script
if __name__ == "__main__":
    try:
        print("Running Syri agent directly. For a better experience, use: python run.py")
        ai_voice_agent = AIVoiceAgent()
        ai_voice_agent.start_session()
        
    except KeyboardInterrupt:
        print("\nExiting Syri Voice Assistant...")
    except Exception as e:
        print(f"Error: {e}") 