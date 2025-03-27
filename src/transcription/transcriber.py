import os
import assemblyai as aai

class Transcriber:
    """Handles speech-to-text transcription using AssemblyAI."""
    
    def __init__(self, api_key=None):
        """Initialize the transcriber with the AssemblyAI API key."""
        # Get API key from environment variable if not provided
        if not api_key:
            api_key = os.getenv("ASSEMBLYAI_API_KEY")
            
        if not api_key:
            raise ValueError("AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY in your .env file")
            
        # Set up AssemblyAI with the API key
        aai.settings.api_key = api_key
        
    def transcribe_audio(self, audio_file):
        """
        Transcribe the recorded audio using AssemblyAI

        Args:
            audio_file (str): Path to the audio file to transcribe

        Returns:
            str: The transcribed text, or None if transcription failed
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