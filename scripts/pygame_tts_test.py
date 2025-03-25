#!/usr/bin/env python3
"""
OpenAI TTS with Pygame Playback Test Script

This script demonstrates TTS generation using OpenAI's API and audio playback
with Pygame instead of platform-specific audio players.

Usage:
    python pygame_tts_test.py [text]
    python pygame_tts_test.py --voice alloy "Text with specific voice"
    
    If no text is provided, a default message will be used.
"""

import os
import sys
import time
import argparse
import tempfile
import pygame
from dotenv import load_dotenv
from openai import OpenAI

def main():
    parser = argparse.ArgumentParser(description="Test OpenAI TTS with Pygame playback")
    parser.add_argument("text", nargs="?", default="Hello! This is a test of OpenAI TTS with Pygame playback.")
    parser.add_argument("--voice", default="coral", help="Voice to use (alloy, echo, fable, onyx, nova, shimmer, coral)")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier")
    parser.add_argument("--model", default="gpt-4o-mini-tts", help="TTS model to use")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        print("Please set this in your .env file")
        return
    
    # Initialize pygame mixer
    pygame.mixer.init()
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    print(f"Generating TTS with voice '{args.voice}' and speed {args.speed}x")
    
    try:
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        # Generate TTS with OpenAI
        response = client.audio.speech.create(
            model=args.model,
            voice=args.voice,
            input=args.text,
            speed=args.speed
        )
        
        # Save the audio to the temporary file
        response.stream_to_file(temp_filename)
        
        print(f"Audio generated and saved to: {temp_filename}")
        print("Playing audio with Pygame...")
        
        # Play the audio using Pygame
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            # Allow user to press Ctrl+C to stop playback
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                pygame.mixer.music.stop()
                print("\nPlayback aborted by user")
                break
        
        # Clean up the temporary file
        try:
            os.unlink(temp_filename)
            print("Temporary audio file deleted")
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_filename}: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Quit pygame
        pygame.quit()

if __name__ == "__main__":
    main() 