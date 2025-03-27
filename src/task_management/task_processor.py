"""
Task processor module for the Syri Voice Assistant.
"""
import asyncio
import threading
import re
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from collections import deque

from ..utils import trigger_helpers


@dataclass
class Task:
    """Represents a single voice processing task."""
    audio_file: str
    transcript: Optional[str] = None
    is_processing: bool = False


class TaskProcessor:
    """Manages a queue of tasks and processes them asynchronously."""
    
    def __init__(self, transcriber, tts_engine, conversation_manager, abort_event):
        """Initialize the task processor.
        
        Args:
            transcriber: The transcriber to use for STT
            tts_engine: The TTS engine to use
            conversation_manager: The conversation manager to use
            abort_event: Threading event to signal task abortion
        """
        self.transcriber = transcriber
        self.tts_engine = tts_engine
        self.conversation_manager = conversation_manager
        self.abort_event = abort_event
        
        # Initialize task queue
        self.task_queue = deque()
        self.queue_lock = threading.Lock()
        self.processing_event = threading.Event()
        
        # Store conversation history - no longer needed for web agent
        # but kept for record-keeping
        self.full_transcript = [
            {"role": "system", "content": "You are a helpful web browsing assistant called Syri. Provide concise, friendly responses based on your web browsing capabilities."},
        ]
    
    def add_task(self, audio_file):
        """Add a new task to the queue.
        
        Args:
            audio_file (str): Path to the audio file for the task
            
        Returns:
            int: The current number of tasks in the queue
        """
        with self.queue_lock:
            task = Task(audio_file=audio_file)
            self.task_queue.append(task)
            queue_length = len(self.task_queue)
            print(f"\nTask added to queue. Queue length: {queue_length}")
        
        # Signal that there's a new task to process
        self.processing_event.set()
        
        return queue_length
    
    async def process_tasks(self):
        """Process tasks from the queue asynchronously."""
        while True:
            # Wait for tasks to be available
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
            
            if not self.task_queue:
                self.processing_event.clear()
                await asyncio.to_thread(self.processing_event.wait)
                continue
            
            # Get next task
            with self.queue_lock:
                task = self.task_queue[0]
                task.is_processing = True
            
            try:
                # Set state to processing
                trigger_helpers.set_state("processing")
                
                # Monitor for abort during transcription and processing
                abort_monitor = threading.Thread(target=self._monitor_abort_during_task)
                abort_monitor.daemon = True
                abort_monitor.start()
                
                # Transcribe audio
                transcript_text = self.transcriber.transcribe_audio(task.audio_file)
                task.transcript = transcript_text
                
                # Check if aborted during transcription
                if self.abort_event.is_set():
                    print("\nAborted during transcription", flush=True)
                    self.abort_event.clear()
                    with self.queue_lock:
                        self.task_queue.popleft()
                    continue
                
                if not transcript_text or transcript_text.strip() == "":
                    print("No speech detected. Skipping task.")
                    with self.queue_lock:
                        self.task_queue.popleft()
                    continue
                
                # Speak confirmation message with transcript in a separate thread
                threading.Thread(
                    target=self._speak_confirmation_message,
                    args=(transcript_text,),
                    daemon=True
                ).start()
                
                # Process user input for conversation commands or generate AI response
                await self._process_user_input(transcript_text)
                
                # Remove completed task from queue
                with self.queue_lock:
                    self.task_queue.popleft()
                
            except Exception as e:
                print(f"Error processing task: {e}")
                with self.queue_lock:
                    self.task_queue.popleft()
            finally:
                # Reset state to inactive after processing
                trigger_helpers.set_state("inactive")
    
    def _speak_confirmation_message(self, transcript_text):
        """Speak a confirmation message with the transcript.
        
        Args:
            transcript_text (str): The transcribed text to confirm
        """
        print("Speaking confirmation message...", flush=True)
        confirmation_text = f"Message received: {transcript_text}"
        
        # Run TTS in a separate thread
        self.tts_engine.generate_and_play_tts(confirmation_text)
    
    def _monitor_abort_during_task(self):
        """Monitor for abort signal during task execution."""
        while not self.abort_event.is_set():
            if trigger_helpers.check_abort_trigger():
                self.abort_current_execution()
                break
            time.sleep(0.2)  # Check every 200ms
    
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
    
    async def _process_user_input(self, transcript_text):
        """Process user input for conversation commands or generate AI response.
        
        Args:
            transcript_text (str): The transcribed user input to process
        """
        self.full_transcript.append({"role": "user", "content": transcript_text})
        print(f"\nUser: {transcript_text}")

        # Reset abort event before starting
        self.abort_event.clear()
        
        # Check if the user wants to start a new conversation
        if self._check_for_new_conversation(transcript_text):
            # Create a new conversation
            session_id = self.conversation_manager.create_conversation()
            response_text = f"Created new conversation with ID {session_id}. You are now using this conversation."
            print(f"\nNew conversation: {response_text}")
            
            # Run TTS to confirm the new conversation
            tts_thread = threading.Thread(
                target=self.tts_engine.generate_and_play_tts,
                args=(response_text,),
                daemon=True
            )
            tts_thread.start()
            
            self.full_transcript.append({"role": "assistant", "content": response_text})
            return
            
        # Check if the user wants to switch to a specific conversation
        session_num = self._check_for_switch_conversation(transcript_text)
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
                target=self.tts_engine.generate_and_play_tts,
                args=(response_text,),
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
                target=self.tts_engine.generate_and_play_tts,
                args=(response_text,),
                daemon=True
            )
            tts_thread.start()
            
            self.full_transcript.append({"role": "assistant", "content": response_text})
            return

        print("\nWeb Agent Response:", flush=True)
        
        # Start a thread to monitor for abort signal during web agent processing
        abort_monitor = threading.Thread(target=self._monitor_abort_during_task)
        abort_monitor.daemon = True
        abort_monitor.start()
        
        try:
            # Use the active web agent conversation with await
            response_text = await active_conversation.run(transcript_text)
            
            # If task was aborted, return early
            if self.abort_event.is_set():
                print("\nTask aborted before TTS generation", flush=True)
                return
            
            print(response_text, flush=True)
            
            # Run TTS in a separate thread
            tts_thread = threading.Thread(
                target=self.tts_engine.generate_and_play_tts,
                args=(response_text,),
                daemon=True
            )
            tts_thread.start()
            
            print()  # Add a newline after response
            self.full_transcript.append({"role": "assistant", "content": response_text})
        except Exception as e:
            print(f"\nError during AI response generation: {e}", flush=True)
    
    def _check_for_new_conversation(self, transcript_text):
        """Check if the user wants to start a new conversation.
        
        Args:
            transcript_text (str): The user's input to check
            
        Returns:
            bool: True if the user wants a new conversation, False otherwise
        """
        # Check for phrases like "new conversation", "start new conversation", etc.
        new_conversation_patterns = [
            r'\bnew conversation\b',
            r'\bstart (?:a )?new conversation\b',
            r'\bcreate (?:a )?new conversation\b',
            r'\bopen (?:a )?new conversation\b',
            r'\bbegin (?:a )?new conversation\b'
        ]
        
        # Check if any pattern matches
        for pattern in new_conversation_patterns:
            if re.search(pattern, transcript_text.lower()):
                return True
                
        return False
    
    def _check_for_switch_conversation(self, transcript_text):
        """Check if the user wants to switch to a specific conversation.
        
        Args:
            transcript_text (str): The user's input to check
            
        Returns:
            int or None: The conversation number to switch to, or None if no switch requested
        """
        # Look for patterns like "switch to conversation 1" or "go to session 2"
        switch_patterns = [
            r'switch to (?:conversation|session) (\d+)',
            r'go to (?:conversation|session) (\d+)',
            r'open (?:conversation|session) (\d+)',
            r'use (?:conversation|session) (\d+)'
        ]
        
        # Check if any pattern matches and get the session number from digits
        for pattern in switch_patterns:
            match = re.search(pattern, transcript_text.lower())
            if match:
                try:
                    session_num = int(match.group(1))
                    return session_num
                except (ValueError, IndexError):
                    pass
        
        # Look for patterns with numbers as words
        word_number_patterns = [
            r'switch to (?:conversation|session) (one|two|three|four|five|six|seven|eight|nine|ten)',
            r'go to (?:conversation|session) (one|two|three|four|five|six|seven|eight|nine|ten)',
            r'open (?:conversation|session) (one|two|three|four|five|six|seven|eight|nine|ten)',
            r'use (?:conversation|session) (one|two|three|four|five|six|seven|eight|nine|ten)'
        ]
        
        # Map word numbers to integers
        word_to_number = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }
        
        # Check for word number patterns
        for pattern in word_number_patterns:
            match = re.search(pattern, transcript_text.lower())
            if match:
                try:
                    word_num = match.group(1).lower()
                    if word_num in word_to_number:
                        return word_to_number[word_num]
                except (IndexError):
                    pass
                
        return None