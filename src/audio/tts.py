"""
Text-to-Speech module for the Syri Voice Assistant.
"""
import os
import tempfile
import time
import threading
import pygame

from ..utils import trigger_helpers


class TextToSpeech:
    """Handles text-to-speech conversion and playback."""
    
    def __init__(self, openai_client, abort_event):
        """Initialize the TextToSpeech module.
        
        Args:
            openai_client: The OpenAI client to use for TTS
            abort_event: The event to set when aborting playback
        """
        self.openai_client = openai_client
        self.abort_event = abort_event
        
        # Initialize pygame mixer for audio playback if not already done
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    
    def generate_and_play_tts(self, text):
        """Generate and play TTS.
        
        Args:
            text (str): The text to convert to speech
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
                if self.abort_event.is_set() or trigger_helpers.check_abort_trigger():
                    if not self.abort_event.is_set():
                        self.abort_current_execution()
                    print("\nWaiting for audio playback aborted", flush=True)
                    try:
                        os.unlink(temp_audio_path)  # Clean up the file since we won't play it
                    except Exception:
                        pass
                    return
                time.sleep(0.1)
            
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
        """Play audio file with periodic checks for abort signal.
        
        Args:
            audio_file_path (str): The path to the audio file to play
        """
        try:
            # Load the audio file
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play()
            
            # Check for abort while playing
            while pygame.mixer.music.get_busy():
                if self.abort_event.is_set() or trigger_helpers.check_abort_trigger():
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
    
    def abort_current_execution(self):
        """Set the abort event flag."""
        print("\nAborting current TTS playback...", flush=True)
        self.abort_event.set()
        # Reset the abort event after a short delay
        threading.Timer(1.0, self.abort_event.clear).start()