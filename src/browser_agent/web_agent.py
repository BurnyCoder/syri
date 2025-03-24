import os
import logging
import time
import asyncio
import uuid

from langchain_anthropic import ChatAnthropic
from portkey_ai import createHeaders
from dotenv import load_dotenv

from browser_use import Agent, BrowserConfig, Browser
from browser_use.agent.views import ActionResult
from browser_use.controller.service import Controller
from browser_use.browser.context import BrowserContext

# Import Chrome manager
from .chrome_manager import start_chrome, cleanup

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a controller instance
controller = Controller()

@controller.action('Log progress')
def log_progress(message: str) -> str:
    """Log the progress of web tasks"""
    logger.info(f"[LOG] {message}")
    return ActionResult(extracted_content="Logged successfully")


class WebAgent:
    """Class to manage browser-based agent interactions."""
    
    def __init__(self, initial_task="Summarize my last gmail", port: int = 9222):
        """Initialize the WebAgent with configuration."""
        self.task = initial_task
        self.port = port
        self.conversation_id = str(uuid.uuid4())
        
        # Get Portkey configuration from environment variables
        self.portkey_api_base = os.getenv("PORTKEY_API_BASE")
        self.portkey_api_key = os.getenv("PORTKEY_API_KEY")
        self.portkey_virtual_key_anthropic = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Additional instructions to append to the web agent prompt
        self.additional_prompt = os.getenv("WEB_AGENT_PROMPT", "")
        
        # Set up Portkey headers for Anthropic/Claude
        portkey_headers = createHeaders(
            api_key=self.portkey_api_key, 
            provider="anthropic",
            virtual_key=self.portkey_virtual_key_anthropic
        )
        
        # Initialize the model with Claude
        self.llm = ChatAnthropic(
            model="claude-3-7-sonnet-latest",
            api_key=self.portkey_virtual_key_anthropic,
            base_url=self.portkey_api_base,
            default_headers=portkey_headers
        )
        
        self.controller = Controller()
        self.browser = None
        self.agent = None
        self.browser_context = None
        
        self.setup_browser()
    
    def setup_browser(self, start_url="https://google.com"):
        """Set up a browser instance with remote debugging."""
        start_chrome(start_url, port=self.port)
        
        self.browser = Browser(
            config=BrowserConfig(
                disable_security=True,
                cdp_url=f"http://localhost:{self.port}",
            ),
        )
        
        # Create a browser context to be reused
        self.browser_context = BrowserContext(browser=self.browser)
        return self.browser
    
    async def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            logger.info(f"Cleaning up browser instance on port {self.port}...")
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
            await self.browser.close()
            self.browser = None
            cleanup(port=self.port, exit_process=False)
            # Wait to ensure browser is fully closed
            await asyncio.sleep(3)
    
    async def run(self, task):
        """Run a single task using the browser instance."""
        try:
            # If user provided additional prompt instructions, add them
            if self.additional_prompt:
                task = f"{task} {self.additional_prompt}"
                
            if self.agent is None:
                # Create the agent with injected browser and browser context to prevent auto-closing
                self.agent = Agent(
                    task=task,
                    llm=self.llm,
                    controller=self.controller,
                    browser=self.browser,
                    browser_context=self.browser_context,
                )
            else:
                # For subsequent tasks, add a new task to the existing agent
                logger.info(f"Starting next task: {task}")
                self.agent.add_new_task(task)
            
            # Run the agent
            result = await self.agent.run()
            # Handle case where agent.run() returns None (after consecutive failures)
            if result is None:
                logger.warning("There was an error with the agent. Please try again.")
                return "There was an error with the agent. Please try again?"
            final_answer = result.final_result()
            return final_answer
                
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Don't clean up browser here to allow for subsequent tasks
            return f"Error: {str(e)}"
            
    async def run_tasks(self, tasks, cleanup_after=True):
        """
        Run multiple tasks sequentially using the same browser instance.
        
        Args:
            tasks (list): List of task strings to run in sequence
            cleanup_after (bool): Whether to clean up the browser after execution
            
        Returns:
            list: List of results for each task
        """
        results = []
        
        try:
            # Initialize browser if not already done
            if not self.browser:
                await self.setup_browser()
                
            # Run each task in sequence
            for task in tasks:
                logger.info(f"Running task: {task}")
                result = await self.run(task)
                results.append(result)
                
            return results
            
        finally:
            # Clean up if requested
            if cleanup_after:
                await self.cleanup()


class ConversationManager:
    """Manages multiple concurrent web agent conversations."""
    
    def __init__(self):
        self.conversations = {}
        self.next_port = 9222  # Starting port number
    
    def create_conversation(self, initial_task: str = "Summarize my last gmail") -> str:
        """Create a new conversation with a unique port."""
        port = self.next_port
        self.next_port += 1
        
        conversation_id = str(uuid.uuid4())
        web_agent = WebAgent(initial_task=initial_task, port=port)
        self.conversations[conversation_id] = web_agent
        
        return conversation_id
    
    async def run_task(self, conversation_id: str, task: str) -> str:
        """Run a task in a specific conversation."""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        web_agent = self.conversations[conversation_id]
        return await web_agent.run(task)
    
    async def cleanup_conversation(self, conversation_id: str):
        """Clean up a specific conversation."""
        if conversation_id in self.conversations:
            web_agent = self.conversations[conversation_id]
            await web_agent.cleanup()
            del self.conversations[conversation_id]
    
    async def cleanup_all(self):
        """Clean up all conversations."""
        for conversation_id in list(self.conversations.keys()):
            await self.cleanup_conversation(conversation_id)


async def main():
    # Example usage of multiple conversations
    manager = ConversationManager()
    
    try:
        # Create two conversations
        conv1_id = manager.create_conversation("Summarize my last gmail")
        conv2_id = manager.create_conversation("Search for recent AI news")
        
        # Run tasks in parallel
        results = await asyncio.gather(
            manager.run_task(conv1_id, "Summarize my last gmail"),
            manager.run_task(conv2_id, "Search for recent AI news")
        )
        
        print("Results:", results)
        
    finally:
        # Clean up all conversations
        await manager.cleanup_all()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())