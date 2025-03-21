#!/usr/bin/env python3
"""
Text-to-Speech Speed Test Script

This script demonstrates the adjustable speech speed feature using the SYRI_TTS_SPEED
environment variable. It speaks the same text at different speeds for comparison.

Usage:
    python tts_speed_test.py [text]
    
    If no text is provided, a default message will be used.
"""

import os
import sys
import time
from dotenv import load_dotenv
from elevenlabs import stream
from elevenlabs.client import ElevenLabs
from elevenlabs.types import VoiceSettings

def main():
    # Get text from command line or use default
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "This is a test of the adjustable speech speed feature."
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY not found in environment variables")
        print("Please set this in your .env file")
        return
    
    # Initialize ElevenLabs client
    client = ElevenLabs(api_key=api_key)
    
    # Get voice ID (using the first available voice)
    voice_id = client.voices.get_all().voices[0].voice_id
    
    # Test different speech speeds
    speeds = [0.8, 1.0, 1.2]
    
    for speed in speeds:
        print(f"\n\nTesting speech speed: {speed}x")
        print("-" * 40)
        
        # Create voice settings with the specified speed
        voice_settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True,
            speed=speed
        )
        
        # Convert text to speech with the specified speed
        audio = client.text_to_speech.convert_as_stream(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=voice_settings
        )
        
        # Stream the audio
        stream(audio)
        
        # Pause between speeds
        if speed != speeds[-1]:
            time.sleep(1)

if __name__ == "__main__":
    main()
