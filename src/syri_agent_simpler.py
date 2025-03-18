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
        self.rate = 16000  # Sample rate
        self.p = pyaudio.PyAudio()

        self.full_transcript = [
            {"role": "system", "content": "You are a helpful AI assistant called Syri. Provide concise, friendly responses under 300 characters."},
        ]

    def record_audio(self):
        """Record audio until the user presses Enter"""
        print("\nPress Enter to start recording...")
        input()  # Wait for Enter to start recording
        
        print("Recording... Press Enter to stop.")
        
        # Open audio stream
        stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        frames = []
        
        # Start a non-blocking input thread
        import threading
        stop_recording = threading.Event()
        
        def wait_for_enter():
            input()  # Wait for Enter to stop recording
            stop_recording.set()
        
        input_thread = threading.Thread(target=wait_for_enter)
        input_thread.daemon = True
        input_thread.start()
        
        # Record audio
        while not stop_recording.is_set():
            data = stream.read(self.chunk)
            frames.append(data)
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
        
        # Save the recorded audio as a WAV file
        wf = wave.open(temp_filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
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