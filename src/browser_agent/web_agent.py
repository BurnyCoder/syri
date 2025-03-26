import os
import logging
import time
import asyncio

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
    
    def __init__(self, initial_task="Summarize my last gmail", port=9222, session_id=None):
        """Initialize the WebAgent with configuration."""
        self.task = initial_task
        self.port = port
        self.session_id = session_id or "default"
        
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
        # Use session-specific CDP port and profile
        user_data_dir = f"/tmp/chrome-debug-profile-{self.session_id}"
        start_chrome(start_url, port=self.port, user_data_dir=user_data_dir)
        
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
            logger.info(f"Cleaning up browser instance for session {self.session_id}...")
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
                logger.warning("The web agent encountered failures. Resetting and trying again...")
                
                # Reset the agent instance to recover from the error
                try:
                    # Clean up the existing agent and reset browser context
                    if self.agent:
                        self.agent = None
                    
                    # Reinitialize the agent with a new instance
                    logger.info("Creating a new agent instance after failure...")
                    self.agent = Agent(
                        task=task,
                        llm=self.llm,
                        controller=self.controller,
                        browser=self.browser,
                        browser_context=self.browser_context,
                    )
                    
                    # Run the agent again with the same task
                    logger.info("Retrying the task with the fresh agent...")
                    result = await self.agent.run()
                    
                    # If it still fails, return a more detailed error message
                    if result is None:
                        logger.error("Web agent failed again after reset attempt.")
                        return "The browser agent couldn't complete this task after multiple attempts. Could you please try a different request or simplify your current one?"
                except Exception as reset_error:
                    logger.error(f"Error while trying to reset agent: {reset_error}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return f"There was an error with the web agent that couldn't be recovered from. Please try a different request."
            
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

async def main():
    browser_agent = WebAgent()
    try:
        
        await browser_agent.run("Summarize my last gmail")
        await browser_agent.run("Search what you just found from the gmail on the internet. Do not go to gmail, just use your memory.")
            
        # Clean up the browser after all tasks are completed
        await browser_agent.cleanup()
        logger.info("Cleanup complete")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        # Cleanup if exception occurs
        await browser_agent.cleanup()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())