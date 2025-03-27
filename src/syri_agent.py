import os
import sys
import platform
import threading
import asyncio
from dotenv import load_dotenv

# Import restructured components
from src.audio.recorder import AudioRecorder
from src.transcription.transcriber import Transcriber
from src.tts.speech_generator import SpeechGenerator
from src.state.state_manager import StateManager, ConversationStateManager
from src.task_management.task_queue import TaskQueue
from src.utils.system_utils import check_chrome_installed, monitor_abort_during_task

# Load environment variables from .env file
load_dotenv()

# Constants for trigger files
TRIGGER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'triggers')
START_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'start_listening')
STOP_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'stop_listening')
ABORT_TRIGGER_FILE = os.path.join(TRIGGER_DIR, 'abort_execution')
STATE_FILE = os.path.join(TRIGGER_DIR, 'listening_state')

class AIVoiceAgent:
    def __init__(self, conversation_manager=None):
        # Get API keys from environment variables
        assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        portkey_api_key = os.getenv("PORTKEY_API_KEY")
        portkey_virtual_key = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Check if API keys are available
        if not assemblyai_api_key:
            raise ValueError("AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY in your .env file")
        if not openai_api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file")
        if not portkey_api_key:
            raise ValueError("Portkey API key not found. Please set PORTKEY_API_KEY in your .env file")
        if not portkey_virtual_key:
            raise ValueError("Portkey Virtual Key not found. Please set PORTKEY_VIRTUAL_KEY_ANTHROPIC in your .env file")
            
        # Store conversation manager
        self.conversation_manager = conversation_manager
        
        # Initialize state manager
        self.state_manager = StateManager(TRIGGER_DIR)
        
        # Initialize conversation state manager
        self.conversation_state_manager = ConversationStateManager()
        
        # Initialize audio recorder
        self.audio_recorder = AudioRecorder()
        
        # Initialize transcriber
        self.transcriber = Transcriber(api_key=assemblyai_api_key)
        
        # Initialize speech generator
        self.speech_generator = SpeechGenerator(
            api_key=openai_api_key,
            abort_check_func=self.state_manager.check_abort_trigger
        )
        
        # Initialize conversation history - no longer needed for web agent
        # as we're not passing conversation history, but keep for record-keeping
        self.full_transcript = [
            {"role": "system", "content": "You are a helpful web browsing assistant called Syri. Provide concise, friendly responses based on your web browsing capabilities."},
        ]
        
        # Initialize task queue
        self.task_queue = TaskQueue(
            transcribe_func=self.transcriber.transcribe_audio,
            process_func=self.generate_ai_response,
            confirmation_func=self.speech_generator.speak_confirmation_message,
            state_manager=self.state_manager
        )

    def record_audio(self):
        """Record audio until a stop trigger file is created"""
        self.state_manager.wait_for_start_trigger()
        
        print("Recording... Create a stop trigger file to stop.")
        
        # Record audio with stop check function
        return self.audio_recorder.record_audio(
            trigger_check_func=self.state_manager.check_stop_trigger
        )

    async def generate_ai_response(self, transcript_text):
        """Generate AI response using the conversation manager and web agent"""
        self.full_transcript.append({"role": "user", "content": transcript_text})
        print(f"\nUser: {transcript_text}")

        # Reset abort event before starting
        self.state_manager.abort_event.clear()
        
        # Check if the user wants to start a new conversation
        if self.conversation_state_manager.check_for_new_conversation(transcript_text):
            # Create a new conversation
            session_id = self.conversation_manager.create_conversation()
            response_text = f"Created new conversation with ID {session_id}. You are now using this conversation."
            print(f"\nNew conversation: {response_text}")
            
            # Run TTS to confirm the new conversation
            tts_thread = threading.Thread(
                target=self.speech_generator.generate_and_play_tts,
                args=(response_text, self.state_manager.abort_event),
                daemon=True
            )
            tts_thread.start()
            
            self.full_transcript.append({"role": "assistant", "content": response_text})
            return
            
        # Check if the user wants to switch to a specific conversation
        session_num = self.conversation_state_manager.check_for_switch_conversation(transcript_text)
        if session_num is not None:
            # Get all available session IDs
            session_ids = self.conversation_manager.get_conversation_ids()
            
            # Check if the requested session exists
            if session_num <= len(session_ids) and session_num > 0:
                # Switch to the requested conversation (adjust for 0-based indexing)
                target_session_id = session_ids[session_num - 1]
                self.conversation_manager.switch_conversation(target_session_id)
                response_text = f"Switched to conversation {session_num} (ID: {target_session_id})"
            else:
                response_text = f"Could not find conversation {session_num}. Available conversations: {len(session_ids)}"
            
            print(f"\nSwitch conversation: {response_text}")
            
            # Run TTS to confirm the switch
            tts_thread = threading.Thread(
                target=self.speech_generator.generate_and_play_tts,
                args=(response_text, self.state_manager.abort_event),
                daemon=True
            )
            tts_thread.start()
            
            self.full_transcript.append({"role": "assistant", "content": response_text})
            return
            
        # Get the active web agent conversation
        active_conversation = self.conversation_manager.get_active_conversation()
        if not active_conversation:
            response_text = "No active conversation available. Please create a new conversation."
            print(f"\nNo conversation: {response_text}")
            
            # Run TTS to indicate the error
            tts_thread = threading.Thread(
                target=self.speech_generator.generate_and_play_tts,
                args=(response_text, self.state_manager.abort_event),
                daemon=True
            )
            tts_thread.start()
            
            self.full_transcript.append({"role": "assistant", "content": response_text})
            return

        print("\nWeb Agent Response:", flush=True)
        
        # Start a thread to monitor for abort signal during web agent processing
        abort_monitor = threading.Thread(
            target=monitor_abort_during_task,
            args=(self.state_manager.check_abort_trigger,)
        )
        abort_monitor.daemon = True
        abort_monitor.start()
        
        try:
            # Use the active web agent conversation with await
            response_text = await active_conversation.run(transcript_text)
            
            # If task was aborted, return early
            if self.state_manager.abort_event.is_set():
                print("\nTask aborted before TTS generation", flush=True)
                return
            
            print(response_text, flush=True)
            
            # Run TTS in a separate thread
            tts_thread = threading.Thread(
                target=self.speech_generator.generate_and_play_tts,
                args=(response_text, self.state_manager.abort_event),
                daemon=True
            )
            tts_thread.start()
            
            print()  # Add a newline after response
            self.full_transcript.append({"role": "assistant", "content": response_text})
        except Exception as e:
            print(f"\nError during AI response generation: {e}", flush=True)

    async def start_session(self):
        """Start the voice assistant session asynchronously"""
        print("Syri Voice Assistant started and ready to listen 🟢")
        print("  • Press Enter to toggle between start/stop recording")
        print("  • ./scripts/start_listening.sh - Start recording")
        print("  • ./scripts/stop_listening.sh - Stop recording and process request")
        print("  • ./scripts/toggle_listening.sh - Toggle between start/stop")
        print("  • ./scripts/abort_execution.sh - Abort current task or TTS")
        print("  • Say \"new conversation\" to create a new conversation")
        print("  • Say \"switch to conversation X\" to switch between conversations")
        
        # Check if Chrome is installed
        if not check_chrome_installed():
            print("Chrome is required for the web agent functionality.")
            print("Please install Chrome and try again.")
            return
        
        try:
            # Create an event to signal stopping the session
            stop_session = threading.Event()
            
            def handle_keyboard_input():
                while not stop_session.is_set():
                    try:
                        input()  # Wait for Enter key
                        self.state_manager.toggle_state()
                    except EOFError:
                        break
            
            # Start keyboard input thread
            keyboard_thread = threading.Thread(target=handle_keyboard_input)
            keyboard_thread.daemon = True
            keyboard_thread.start()

            # Start task processing thread
            process_thread = threading.Thread(
                target=lambda: asyncio.run(self.task_queue.process_tasks())
            )
            process_thread.daemon = True
            process_thread.start()
            
            while True:
                # Record audio
                audio_file = self.record_audio()
                
                if audio_file:
                    # Add task to queue
                    self.task_queue.add_task(audio_file)
                
                # Reset state to inactive after recording
                self.state_manager.set_state("inactive")
                
        except KeyboardInterrupt:
            print("\nExiting Syri Voice Assistant...")
            stop_session.set()  # Signal the keyboard thread to stop
        except Exception as e:
            print(f"Error: {e}")
            stop_session.set()  # Signal the keyboard thread to stop
        finally:
            # Clean up PyAudio
            self.audio_recorder.cleanup()
            
            # Clean up all conversations
            if self.conversation_manager:
                asyncio.run(self.conversation_manager.cleanup_all())


# Direct execution of the script
if __name__ == "__main__":
    try:
        print("Running Syri agent directly. For a better experience, use: python run.py")
        from src.browser_agent.web_agent import ConversationManager
        
        # Create conversation manager and initialize first conversation
        conversation_manager = ConversationManager()
        conversation_manager.create_conversation()
        
        ai_voice_agent = AIVoiceAgent(conversation_manager=conversation_manager)
        asyncio.run(ai_voice_agent.start_session())
        
    except KeyboardInterrupt:
        print("\nExiting Syri Voice Assistant...")
    except Exception as e:
        print(f"Error: {e}")