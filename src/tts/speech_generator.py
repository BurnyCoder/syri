import os
import tempfile
import time
import threading
import pygame
from openai import OpenAI

class SpeechGenerator:
    """Handles text-to-speech generation and playback using OpenAI's TTS API."""
    
    def __init__(self, api_key=None, abort_check_func=None):
        """
        Initialize the speech generator with OpenAI API key.
        
        Args:
            api_key (str, optional): OpenAI API key. If not provided, fetched from environment.
            abort_check_func (callable, optional): Function to check for abort signal.
        """
        # Get API key from environment variable if not provided
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
            
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
            
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=api_key)
        
        # Initialize pygame mixer for audio playback if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        # Store abort check function
        self.abort_check_func = abort_check_func
        
    def generate_and_play_tts(self, text, abort_event=None):
        """
        Generate and play text-to-speech audio.
        
        Args:
            text (str): The text to convert to speech
            abort_event (threading.Event, optional): Event to signal abortion
        """
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
            
            # Wait for any currently playing audio to finish before playing new audio
            while pygame.mixer.music.get_busy():
                # Check for abort while waiting
                if (abort_event and abort_event.is_set()) or (self.abort_check_func and self.abort_check_func()):
                    print("\nWaiting for audio playback aborted", flush=True)
                    try:
                        os.unlink(temp_audio_path)  # Clean up the file since we won't play it
                    except Exception:
                        pass
                    return
                time.sleep(0.1)
            
            # Play the audio with abort check capability
            self._play_audio_with_abort_check(temp_audio_path, abort_event)
            
            # Clean up temp file after playback
            try:
                os.unlink(temp_audio_path)
            except Exception as e:
                print(f"\nWarning: Could not delete temporary audio file: {e}", flush=True)
            
        except Exception as e:
            print(f"\nError during TTS generation and playback: {e}", flush=True)

    def _play_audio_with_abort_check(self, audio_file_path, abort_event=None):
        """
        Play audio file with periodic checks for abort signal.
        
        Args:
            audio_file_path (str): Path to the audio file to play
            abort_event (threading.Event, optional): Event to signal abortion
        """
        try:
            # Load the audio file
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play()
            
            # Check for abort while playing
            while pygame.mixer.music.get_busy():
                if (abort_event and abort_event.is_set()) or (self.abort_check_func and self.abort_check_func()):
                    # If abort signal detected, stop playback
                    pygame.mixer.music.stop()
                    print("\nTTS playback aborted", flush=True)
                    break
                # Small delay to prevent high CPU usage
                time.sleep(0.1)
            
        except Exception as e:
            print(f"\nError during audio playback: {e}", flush=True)
            
    def speak_confirmation_message(self, transcript_text):
        """
        Speak a confirmation message with the transcript.
        
        Args:
            transcript_text (str): The transcribed text to confirm
        """
        print("Speaking confirmation message...", flush=True)
        confirmation_text = f"Message received: {transcript_text}"
        
        # Generate and play TTS
        self.generate_and_play_tts(confirmation_text)