import os
import time
import threading
import re
from pathlib import Path

class StateManager:
    """Manages the state of the voice assistant, including trigger files and state tracking."""
    
    def __init__(self, trigger_dir=None):
        """
        Initialize the state manager.
        
        Args:
            trigger_dir (str, optional): Directory for trigger files. If not provided, 
                                         defaults to 'triggers' in the project root.
        """
        # Set up trigger directory path
        if trigger_dir:
            self.trigger_dir = trigger_dir
        else:
            # Default to 'triggers' in the project root
            project_root = Path(__file__).parents[2]
            self.trigger_dir = os.path.join(project_root, 'triggers')
            
        # Define trigger file paths
        self.start_trigger_file = os.path.join(self.trigger_dir, 'start_listening')
        self.stop_trigger_file = os.path.join(self.trigger_dir, 'stop_listening')
        self.abort_trigger_file = os.path.join(self.trigger_dir, 'abort_execution')
        self.state_file = os.path.join(self.trigger_dir, 'listening_state')
        
        # Ensure trigger directory exists
        if not os.path.exists(self.trigger_dir):
            os.makedirs(self.trigger_dir)
            
        # Clear any existing trigger files and initialize state
        self._clear_trigger_files()
        
        # Create abort event flag
        self.abort_event = threading.Event()
        
    def _clear_trigger_files(self):
        """Remove any existing trigger files and initialize state"""
        if os.path.exists(self.start_trigger_file):
            os.remove(self.start_trigger_file)
        if os.path.exists(self.stop_trigger_file):
            os.remove(self.stop_trigger_file)
        if os.path.exists(self.abort_trigger_file):
            os.remove(self.abort_trigger_file)

        # Initialize state to inactive when server starts
        with open(self.state_file, 'w') as f:
            f.write("inactive")
    
    def wait_for_start_trigger(self):
        """Wait for a start trigger file to be created"""
        while not os.path.exists(self.start_trigger_file):
            time.sleep(0.5)

        # Remove the start trigger file once detected
        os.remove(self.start_trigger_file)
        
        # Update state file
        with open(self.state_file, 'w') as f:
            f.write("active")
    
    def check_stop_trigger(self):
        """Check if a stop trigger file exists"""
        if os.path.exists(self.stop_trigger_file):
            # Remove the stop trigger file once detected
            os.remove(self.stop_trigger_file)
            
            # Update state file
            with open(self.state_file, 'w') as f:
                f.write("inactive")
                
            return True
        return False
    
    def check_abort_trigger(self):
        """Check if abort trigger file exists"""
        if os.path.exists(self.abort_trigger_file):
            # Remove the trigger file
            try:
                os.remove(self.abort_trigger_file)
            except Exception:
                pass
            return True
        return False
    
    def abort_current_execution(self, conversation_manager=None):
        """
        Abort current execution by setting the abort event.
        
        Args:
            conversation_manager: Optional conversation manager to stop active conversation
        """
        print("\nAborting current execution...", flush=True)
        self.abort_event.set()
        # Reset the abort event after a short delay to allow tasks to be aborted
        threading.Timer(1.0, self.abort_event.clear).start()
        
        # Stop the current web agent if it exists
        if conversation_manager:
            active_conversation = conversation_manager.get_active_conversation()
            if active_conversation and active_conversation.agent:
                active_conversation.agent.stop()
    
    def set_state(self, state):
        """
        Set the current state in the state file.
        
        Args:
            state (str): The state to set ("active", "inactive", or "processing")
        """
        with open(self.state_file, 'w') as f:
            f.write(state)
    
    def get_state(self):
        """
        Get the current state from the state file.
        
        Returns:
            str: The current state or "inactive" if file doesn't exist
        """
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return f.read().strip()
        return "inactive"
        
    def toggle_state(self):
        """
        Toggle between active and inactive states.
        
        Returns:
            str: The new state after toggling
        """
        current_state = self.get_state()
        
        # If currently recording or processing, set to inactive
        if current_state in ["active", "processing"]:
            self.set_state("inactive")
            with open(self.stop_trigger_file, 'w') as f:
                pass
            return "inactive"
        else:
            # If inactive, set to active
            self.set_state("active")
            with open(self.start_trigger_file, 'w') as f:
                pass
            return "active"


class ConversationStateManager:
    """Manages conversation detection and switching from user utterances."""
    
    def check_for_new_conversation(self, transcript_text):
        """
        Check if the user wants to start a new conversation.
        
        Args:
            transcript_text (str): The transcribed text to check
            
        Returns:
            bool: True if a new conversation request is detected, False otherwise
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

    def check_for_switch_conversation(self, transcript_text):
        """
        Check if the user wants to switch to a specific conversation.
        
        Args:
            transcript_text (str): The transcribed text to check
            
        Returns:
            int or None: The conversation number to switch to, or None if no switch detected
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