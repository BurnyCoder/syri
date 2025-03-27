"""
Main module for the Syri Voice Assistant.

This module provides the main AIVoiceAgent class that coordinates all the
components of the Syri Voice Assistant.
"""
import os
import sys
import time
import threading
import asyncio
import pygame
from openai import OpenAI
from dotenv import load_dotenv

from .audio.recorder import AudioRecorder
from .audio.transcriber import Transcriber
from .audio.tts import TextToSpeech
from .task_management.task_processor import TaskProcessor
from .utils import config, trigger_helpers, system_helpers

# Load environment variables from .env file
load_dotenv()

# Import constants from config
from .utils.config import (
    TRIGGER_DIR, START_TRIGGER_FILE, STOP_TRIGGER_FILE, 
    ABORT_TRIGGER_FILE, STATE_FILE
)


class AIVoiceAgent:
    """Main voice assistant agent that coordinates all components."""
    
    def __init__(self, conversation_manager=None):
        """Initialize the AI Voice Agent with all necessary components.
        
        Args:
            conversation_manager: The browser-based conversation manager to use
        """
        # Get API keys from environment variables
        openai_api_key = os.getenv("OPENAI_API_KEY")
        portkey_api_key = os.getenv("PORTKEY_API_KEY")
        portkey_virtual_key = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Check if API keys are available
        if not openai_api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        if not portkey_api_key:
            raise ValueError("Portkey API key not found. Please set PORTKEY_API_KEY in your .env file")
        if not portkey_virtual_key:
            raise ValueError("Portkey Virtual Key not found. Please set PORTKEY_VIRTUAL_KEY_ANTHROPIC in your .env file")
            
        # Set OpenAI client
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        # Store conversation manager
        self.conversation_manager = conversation_manager
        
        # Create abort event flag
        self.abort_event = threading.Event()
        
        # Initialize components
        self._init_components()
        
        # Ensure trigger directory exists
        if not os.path.exists(TRIGGER_DIR):
            os.makedirs(TRIGGER_DIR)

        # Clear any existing trigger files
        trigger_helpers.clear_trigger_files()
    
    def _init_components(self):
        """Initialize all component modules."""
        # Initialize audio components
        self.audio_recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.tts_engine = TextToSpeech(self.openai_client, self.abort_event)
        
        # Initialize task processor
        self.task_processor = TaskProcessor(
            self.transcriber, 
            self.tts_engine, 
            self.conversation_manager, 
            self.abort_event
        )
    
    def abort_current_execution(self):
        """Abort current execution by setting the abort event."""
        print("\nAborting current execution...", flush=True)
        self.abort_event.set()
        # Reset the abort event after a short delay to allow tasks to be aborted
        threading.Timer(1.0, self.abort_event.clear).start()
        
        # Stop the current web agent if it exists
        active_conversation = self.conversation_manager.get_active_conversation()
        if active_conversation and active_conversation.agent:
            active_conversation.agent.stop()
    
    async def start_session(self):
        """Start the voice assistant session asynchronously."""
        print("Syri Voice Assistant started and ready to listen 🟢")
        print("  • Press Enter to toggle between start/stop recording")
        print("  • ./scripts/start_listening.sh - Start recording")
        print("  • ./scripts/stop_listening.sh - Stop recording and process request")
        print("  • ./scripts/toggle_listening.sh - Toggle between start/stop")
        print("  • ./scripts/abort_execution.sh - Abort current task or TTS")
        print("  • Say \"new conversation\" to create a new conversation")
        print("  • Say \"switch to conversation X\" to switch between conversations")
        
        # Check if Chrome is installed
        if not system_helpers.check_chrome_installed():
            print("Chrome is required for the web agent functionality.")
            print("Please install Chrome and try again.")
            return
        
        try:
            # Create an event to signal stopping the session
            stop_session = threading.Event()
            
            # Set up keyboard input handling
            keyboard_thread = self._start_keyboard_input_thread(stop_session)
            
            # Start task processing thread
            process_thread = threading.Thread(
                target=lambda: asyncio.run(self.task_processor.process_tasks())
            )
            process_thread.daemon = True
            process_thread.start()
            
            while True:
                # Record audio
                audio_file = self.audio_recorder.record_audio()
                
                if audio_file:
                    # Add task to queue
                    self.task_processor.add_task(audio_file)
                
                # Reset state to inactive after recording
                trigger_helpers.set_state("inactive")
                
        except KeyboardInterrupt:
            print("\nExiting Syri Voice Assistant...")
            stop_session.set()  # Signal the keyboard thread to stop
        except Exception as e:
            print(f"Error: {e}")
            stop_session.set()  # Signal the keyboard thread to stop
        finally:
            # Clean up audio recorder
            self.audio_recorder.cleanup()
            
            # Clean up all conversations
            if self.conversation_manager:
                await self.conversation_manager.cleanup_all()
    
    def _start_keyboard_input_thread(self, stop_session):
        """Start a thread to handle keyboard input for controlling the assistant.
        
        Args:
            stop_session: Event to signal when the session should stop
            
        Returns:
            thread: The started keyboard thread
        """
        def handle_keyboard_input():
            while not stop_session.is_set():
                try:
                    input()  # Wait for Enter key
                    if os.path.exists(STATE_FILE):
                        with open(STATE_FILE, 'r') as f:
                            current_state = f.read().strip()
                        
                        # If already running a task, abort it
                        if self.abort_event.is_set():
                            print("Already aborting a task. Please wait...")
                            continue
                        
                        # Check if we're currently recording
                        if current_state == "active":
                            # Stop recording
                            trigger_helpers.set_state("inactive")
                            touch_file = os.path.join(TRIGGER_DIR, "stop_listening")
                        else:
                            # Start recording (regardless of processing state)
                            trigger_helpers.set_state("active")
                            touch_file = os.path.join(TRIGGER_DIR, "start_listening")
                            
                        # Create the appropriate trigger file
                        with open(touch_file, 'w') as f:
                            pass
                except EOFError:
                    break
        
        # Start keyboard input thread
        keyboard_thread = threading.Thread(target=handle_keyboard_input)
        keyboard_thread.daemon = True
        keyboard_thread.start()
        
        return keyboard_thread


# Direct execution of the script
if __name__ == "__main__":
    try:
        print("Running Syri agent directly. For a better experience, use: python run.py")
        from .browser_agent.web_agent import ConversationManager
        
        # Create conversation manager and initialize first conversation
        conversation_manager = ConversationManager()
        conversation_manager.create_conversation()
        
        ai_voice_agent = AIVoiceAgent(conversation_manager=conversation_manager)
        asyncio.run(ai_voice_agent.start_session())
        
    except KeyboardInterrupt:
        print("\nExiting Syri Voice Assistant...")
    except Exception as e:
        print(f"Error: {e}")