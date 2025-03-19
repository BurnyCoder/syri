#!/usr/bin/env python3
"""
Syri Voice Assistant - Runner Script

This script provides a clean entry point to start the Syri Voice Assistant.
It imports the AIVoiceAgent from syri_agent.py and handles setup and error conditions.
"""
import os
import time
import sys
from src.syri_agent_simpler import AIVoiceAgent

def display_welcome():
    """Display welcome message and instructions."""
    print("\n" + "=" * 50)
    print(" 🎤  Syri Voice Assistant 🔊")
    print("=" * 50)
    print("\nThis assistant uses:")
    print("  • AssemblyAI for speech-to-text")
    print("  • Web browser agent (with Claude 3.7 Sonnet) for AI processing")
    print("  • ElevenLabs for text-to-speech")
    print("\nStarting up...\n")
    time.sleep(1)


def main():
    """Main entry point for the voice assistant."""
    display_welcome()

    try:
        print("\nStarting voice assistant...\n")
        print("Press Enter to start recording, speak, then press Enter again when done.")
        print("Press Ctrl+C to exit.")
        time.sleep(1)
        
        # Create and start the voice agent
        agent = AIVoiceAgent()
        agent.start_session()
            
    except KeyboardInterrupt:
        print("\n\nGracefully shutting down. Goodbye! 👋")
    except Exception as e:
        print(f"\nError: {e}")
        print("The assistant has encountered an error and needs to exit.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 