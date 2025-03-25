#!/usr/bin/env python3
"""
Syri Voice Assistant - Runner Script

This script provides a clean entry point to start the Syri Voice Assistant.
It imports the AIVoiceAgent from syri_agent.py and handles setup and error conditions.
"""
import os
import time
import sys
import asyncio
from src.syri_agent_simpler import AIVoiceAgent, TRIGGER_DIR, STATE_FILE, ABORT_TRIGGER_FILE
from src.browser_agent.web_agent import ConversationManager

def display_welcome():
    """Display welcome message and instructions."""
    print("\n" + "=" * 50)
    print(" 🎤  Syri Voice Assistant 🔊")
    print("=" * 50)
    print("\nThis assistant uses:")
    print("  • AssemblyAI for speech-to-text")
    print("  • Web browser agent (with Claude 3.7 Sonnet) for AI processing")
    print("  • OpenAI TTS for text-to-speech")
    print("\nStarting up...")
    time.sleep(1)


async def main():
    """Main entry point for the voice assistant."""
    display_welcome()

    # Ensure trigger directory exists
    if not os.path.exists(TRIGGER_DIR):
        os.makedirs(TRIGGER_DIR)

    # Remove any existing abort trigger file from previous runs
    if os.path.exists(ABORT_TRIGGER_FILE):
        os.remove(ABORT_TRIGGER_FILE)

    try:
        # Initialize conversation manager and create first conversation
        print("Initializing conversation manager...")
        conversation_manager = ConversationManager()
        conversation_manager.create_conversation()
        print("Conversation manager initialized and ready 🟢")
        print("To create additional conversations, say 'new conversation'")
        print("To switch between conversations, say 'switch to conversation [number]'")

        # Create the voice agent, passing the conversation manager
        agent = AIVoiceAgent(conversation_manager=conversation_manager)
        
        # Start the voice agent session
        await agent.start_session()
            
    except KeyboardInterrupt:
        print("\n\nGracefully shutting down. Goodbye! 👋")
    except Exception as e:
        print(f"\nError: {e}")
        print("The assistant has encountered an error and needs to exit.")
        return 1
    finally:
        # Ensure all browser instances are properly cleaned up when the script exits
        if 'conversation_manager' in locals():
            await conversation_manager.cleanup_all()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))