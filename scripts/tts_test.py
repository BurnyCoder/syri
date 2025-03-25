#!/usr/bin/env python3
"""
Text-to-Speech Test Script using OpenAI API

This script demonstrates text-to-speech functionality
using the OpenAI API. It takes a text input from the command line
and converts it to speech that is played immediately.

Requirements:
- Python 3.12+
- An OpenAI API key in .env file (OPENAI_API_KEY)
- The openai and pygame packages installed
"""

import os
import sys
import argparse
import pygame
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test OpenAI TTS functionality')
    parser.add_argument('--text', type=str, help='Text to convert to speech',
                        default="Hello! This is a test of the OpenAI TTS API.")
    parser.add_argument('--voice', type=str, help='Voice to use',
                        default="coral", choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer", "coral"])
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        sys.exit(1)

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Initialize pygame for audio playback
    pygame.mixer.init()

    print(f"Converting text to speech using voice: {args.voice}")
    print(f"Text: {args.text}")

    # Create temporary file for audio
    temp_file = Path(__file__).parent / "tts_test.mp3"
    
    try:
        # Generate speech
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=args.voice,
            input=args.text,
            instructions="Speak in a cheerful and positive tone.",
        )
        
        # Save to file
        response.stream_to_file(temp_file)
        
        print(f"Audio saved to {temp_file}")
        
        # Play the audio
        print("Playing audio...")
        pygame.mixer.music.load(str(temp_file))
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        print("Playback complete")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Clean up
        if temp_file.exists():
            os.unlink(temp_file)

if __name__ == "__main__":
    main() 