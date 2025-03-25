#!/usr/bin/env python3
"""
Text-to-Speech Test Script using OpenAI TTS API

This script provides a simple demonstration of converting text to speech
using the OpenAI TTS API. It takes a text input from the command line
or uses a default message, then converts it to speech and plays it using Pygame.

Usage:
    python tts_test.py "Your text to convert to speech"
    python tts_test.py --voice alloy "Text with specific voice"
    python tts_test.py --list-voices

Requirements:
    - An OpenAI API key in .env file (OPENAI_API_KEY)
    - The openai and pygame packages installed
"""

import os
import argparse
import tempfile
import pygame
from dotenv import load_dotenv
from openai import OpenAI

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('text', nargs='?', 
                      default="Hello! This is a test of the OpenAI TTS API.")
    parser.add_argument('--voice', default="coral")
    parser.add_argument('--model', default='gpt-4o-mini-tts')
    parser.add_argument('--speed', type=float, default=1.0)
    parser.add_argument('--list-voices', action='store_true')
    args = parser.parse_args()
    
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if args.list_voices:
        print("Available OpenAI TTS voices:")
        print("- alloy: Versatile, neutral voice")
        print("- echo: Smooth, natural voice")
        print("- fable: Expressive, storytelling voice")
        print("- onyx: Deep, authoritative voice")
        print("- nova: Warm, friendly voice")
        print("- shimmer: Clear, optimistic voice")
        print("- coral: Enthusiastic, upbeat voice")
        return

    print(f"Converting text to speech with voice '{args.voice}'...")
    
    # Create a temporary file for the audio
    temp_audio_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_audio_path = temp_audio_file.name
    temp_audio_file.close()
    
    # Generate TTS
    response = client.audio.speech.create(
        model=args.model,
        voice=args.voice,
        input=args.text,
        speed=args.speed
    )
    
    # Save the audio to the temp file
    response.stream_to_file(temp_audio_path)
    
    # Initialize pygame mixer
    pygame.mixer.init()
    
    try:
        # Play the audio using Pygame
        pygame.mixer.music.load(temp_audio_path)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)  # 10 frames per second, limits CPU usage
    except Exception as e:
        print(f"Error during playback: {e}")
    finally:
        # Clean up
        pygame.quit()
        
        # Delete temp file
        try:
            os.unlink(temp_audio_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file: {e}")

if __name__ == "__main__":
    main() 