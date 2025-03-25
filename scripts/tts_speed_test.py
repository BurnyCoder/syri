#!/usr/bin/env python3
"""
Text-to-Speech Speed Test Script

This script demonstrates the adjustable speech speed feature using the SYRI_TTS_SPEED
environment variable. It speaks the same text at different speeds for comparison
using Pygame for audio playback.

Usage:
    python tts_speed_test.py [text]
    
    If no text is provided, a default message will be used.
"""

import os
import sys
import time
import tempfile
import pygame
from dotenv import load_dotenv
from openai import OpenAI

def main():
    # Get text from command line or use default
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "This is a test of the adjustable speech speed feature."
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        print("Please set this in your .env file")
        return
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Get voice from environment or use default
    voice = os.getenv("SYRI_TTS_VOICE", "coral")
    
    # Initialize pygame mixer
    pygame.mixer.init()
    
    # Test different speech speeds
    speeds = [0.8, 1.0, 1.2]
    
    try:
        for speed in speeds:
            print(f"\n\nTesting speech speed: {speed}x")
            print("-" * 40)
            
            # Create a temporary file for the audio
            temp_audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_audio_path = temp_audio_file.name
            temp_audio_file.close()
            
            # Generate TTS with the specified speed
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=voice,
                input=text,
                speed=speed
            )
            
            # Save the audio to the temp file
            response.stream_to_file(temp_audio_path)
            
            # Play the audio using Pygame
            pygame.mixer.music.load(temp_audio_path)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)  # 10 FPS to limit CPU usage
            
            # Clean up temp file
            try:
                os.unlink(temp_audio_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file: {e}")
            
            # Pause between speeds
            if speed != speeds[-1]:
                time.sleep(1)
    
    finally:
        # Clean up pygame
        pygame.quit()

if __name__ == "__main__":
    main()
