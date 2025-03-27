import logging

from .web_agent import WebAgent

# Get logger from module
logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages multiple WebAgent instances for different conversations."""
    
    def __init__(self):
        """Initialize the conversation manager."""
        self.conversations = {}
        self.active_conversation_id = "default"
        self.next_port = 9222
        self.next_session_id = 1
    
    def _get_next_port(self):
        """Get the next available port for a new Chrome instance."""
        port = self.next_port
        self.next_port += 1
        return port
    
    def _get_next_session_id(self):
        """Get the next session ID for a new conversation."""
        session_id = f"session-{self.next_session_id}"
        self.next_session_id += 1
        return session_id
    
    def create_conversation(self, initial_task="Summarize my last gmail"):
        """Create a new conversation with a fresh WebAgent."""
        session_id = self._get_next_session_id()
        port = self._get_next_port()
        
        # Create a new WebAgent for this conversation
        conversation = WebAgent(initial_task=initial_task, port=port, session_id=session_id)
        
        # Store the conversation
        self.conversations[session_id] = conversation
        self.active_conversation_id = session_id
        
        logger.info(f"Created new conversation with ID: {session_id}")
        return session_id
    
    def get_active_conversation(self):
        """Get the currently active WebAgent conversation."""
        return self.conversations.get(self.active_conversation_id)
    
    def switch_conversation(self, conversation_id):
        """Switch to a different conversation."""
        if conversation_id in self.conversations:
            self.active_conversation_id = conversation_id
            logger.info(f"Switched to conversation: {conversation_id}")
            return True
        return False
    
    def get_conversation_ids(self):
        """Get a list of all available conversation IDs."""
        return list(self.conversations.keys())
    
    async def cleanup_all(self):
        """Clean up all conversations."""
        for session_id, conversation in self.conversations.items():
            logger.info(f"Cleaning up conversation: {session_id}")
            await conversation.cleanup() 