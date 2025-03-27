"""
Speech-to-text transcription module for the Syri Voice Assistant.
"""
import os
import assemblyai as aai


class Transcriber:
    """Handles speech-to-text transcription using AssemblyAI."""
    
    def __init__(self):
        """Initialize the transcriber with API key from environment."""
        assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if not assemblyai_api_key:
            raise ValueError("AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY in your .env file")
        
        aai.settings.api_key = assemblyai_api_key
    
    def transcribe_audio(self, audio_file):
        """Transcribe the recorded audio using AssemblyAI.
        
        Args:
            audio_file (str): Path to the audio file to transcribe
            
        Returns:
            str: The transcribed text, or None if transcription failed
        """
        if not audio_file:
            return None

        print("Transcribing audio...")

        # Create a transcriber
        transcriber = aai.Transcriber()

        # Start the transcription
        try:
            transcript = transcriber.transcribe(audio_file)
            print("Audio transcription successful\n")
            
            # Clean up the temporary file
            try:
                os.unlink(audio_file)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {audio_file}: {e}")
                
            return transcript.text
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            
            # Try to clean up the temp file even if transcription failed
            try:
                os.unlink(audio_file)
            except Exception:
                pass
                
            return None