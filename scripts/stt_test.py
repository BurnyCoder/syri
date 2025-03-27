#!/usr/bin/env python3
"""
Speech-to-Text Test Script using AssemblyAI

This script provides a simple demonstration of converting speech to text
using the AssemblyAI API. It records audio from your microphone and
then transcribes it.

Usage:
    python stt_test.py

Requirements:
    - An AssemblyAI API key in .env file (ASSEMBLYAI_API_KEY)
    - assemblyai, pyaudio packages installed
"""

import os
import sys
import tempfile
import argparse
from dotenv import load_dotenv
import assemblyai as aai
sys.path.append('.')
from src.syri_agent import AIVoiceAgent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=None)
    parser.add_argument('--keep-audio', action='store_true')
    args = parser.parse_args()
    
    load_dotenv()
    agent = AIVoiceAgent()
    
    audio_file = agent.record_audio()
    
    try:
        transcript_text = agent.transcribe_audio(audio_file)
        print(transcript_text)
    finally:
        if not args.keep_audio and audio_file:
            try:
                os.unlink(audio_file)
            except:
                pass
        elif audio_file:
            print(f"Audio saved: {audio_file}")

if __name__ == "__main__":
    main() 