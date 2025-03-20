#!/usr/bin/env python3
"""
Text-to-Speech Test Script using ElevenLabs API

This script provides a simple demonstration of converting text to speech
using the ElevenLabs API. It takes a text input from the command line
or uses a default message, then converts it to speech and plays it.

Usage:
    python tts_test.py "Your text to convert to speech"

Requirements:
    - An ElevenLabs API key in .env file (ELEVENLABS_API_KEY)
    - The elevenlabs package installed
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from elevenlabs import stream
from elevenlabs.client import ElevenLabs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('text', nargs='?', 
                      default="Hello! This is a test of the ElevenLabs API.")
    parser.add_argument('--voice', default=None)
    parser.add_argument('--model', default='eleven_multilingual_v2')
    parser.add_argument('--list-voices', action='store_true')
    args = parser.parse_args()
    
    load_dotenv()
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    if args.list_voices:
        voices = client.voices.get_all()
        for v in voices.voices:
            print(f"{v.name}: {v.voice_id}")
        return

    voice_id = args.voice
    if not voice_id:
        voice_id = client.voices.get_all().voices[0].voice_id

    audio = client.text_to_speech.convert_as_stream(
        text=args.text,
        voice_id=voice_id,
        model_id=args.model
    )
    
    stream(audio)

if __name__ == "__main__":
    main() 