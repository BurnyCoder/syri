import os
import threading
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable, Any

@dataclass
class Task:
    """Represents a voice processing task in the queue."""
    audio_file: str
    transcript: Optional[str] = None
    is_processing: bool = False

class TaskQueue:
    """Manages asynchronous processing of audio tasks."""
    
    def __init__(self, 
                 transcribe_func: Callable[[str], str],
                 process_func: Callable[[str], Any],
                 confirmation_func: Callable[[str], Any] = None,
                 state_manager=None):
        """
        Initialize the task queue.
        
        Args:
            transcribe_func: Function to transcribe audio files
            process_func: Function to process transcribed text
            confirmation_func: Optional function to send confirmation
            state_manager: Optional state manager to update state
        """
        # Store processing functions
        self.transcribe_func = transcribe_func
        self.process_func = process_func
        self.confirmation_func = confirmation_func
        self.state_manager = state_manager
        
        # Initialize task queue
        self.task_queue = deque()
        self.queue_lock = threading.Lock()
        self.processing_event = threading.Event()
        
    def add_task(self, audio_file: str) -> None:
        """
        Add a new task to the queue.
        
        Args:
            audio_file: Path to the audio file to process
        """
        with self.queue_lock:
            task = Task(audio_file=audio_file)
            self.task_queue.append(task)
            print(f"\nTask added to queue. Queue length: {len(self.task_queue)}")
        
        # Signal that there's a new task to process
        self.processing_event.set()
        
    async def process_tasks(self):
        """Process tasks from the queue."""
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
                # Set state to processing if state manager available
                if self.state_manager:
                    self.state_manager.set_state("processing")
                
                # Transcribe audio
                transcript_text = self.transcribe_func(task.audio_file)
                task.transcript = transcript_text
                
                # Check for empty transcript
                if not transcript_text or transcript_text.strip() == "":
                    print("No speech detected. Skipping task.")
                    with self.queue_lock:
                        self.task_queue.popleft()
                    continue
                
                # Speak confirmation if confirmation function is provided
                if self.confirmation_func:
                    threading.Thread(
                        target=self.confirmation_func,
                        args=(transcript_text,),
                        daemon=True
                    ).start()
                
                # Process the transcript
                await self.process_func(transcript_text)
                
                # Remove completed task from queue
                with self.queue_lock:
                    self.task_queue.popleft()
                
            except Exception as e:
                print(f"Error processing task: {e}")
                with self.queue_lock:
                    self.task_queue.popleft()
            finally:
                # Reset state to inactive after processing
                if self.state_manager:
                    self.state_manager.set_state("inactive")