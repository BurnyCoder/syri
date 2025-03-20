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
from src.browser_agent.chrome_manager import start_chrome, cleanup
from src.browser_agent.web_agent import WebAgent

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
        # Start Chrome just once at the beginning
        print("Starting Chrome browser...")
        start_chrome()
        print("Chrome browser started and ready.\n")
        
        # Initialize web agent just once
        print("Initializing web and voice agent...")
        web_agent = WebAgent()
        agent = AIVoiceAgent(web_agent=web_agent)
        print("Web and voice agent initialized and ready.\n")
        
        print("\nStarting voice assistant...\n")
        print("Press Enter to start recording, speak, then press Enter again when done.")
        print("Press Ctrl+C to exit.")
        
        # Create and start the voice agent, passing the web_agent instance
        agent.start_session()
            
    except KeyboardInterrupt:
        print("\n\nGracefully shutting down. Goodbye! 👋")
    except Exception as e:
        print(f"\nError: {e}")
        print("The assistant has encountered an error and needs to exit.")
        return 1
    finally:
        # Ensure Chrome is properly cleaned up when the script exits
        cleanup(exit_process=False)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 