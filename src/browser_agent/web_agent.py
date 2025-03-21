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
    
    def __init__(self, initial_task="Summarize my last gmail"):
        """Initialize the WebAgent with configuration."""
        self.task = initial_task
        
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
        start_chrome(start_url)
        
        self.browser = Browser(
            config=BrowserConfig(
                disable_security=True,
                cdp_url="http://localhost:9222",
            ),
        )
        
        # Create a browser context to be reused
        self.browser_context = BrowserContext(browser=self.browser)
        return self.browser
    
    async def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            logger.info("Cleaning up browser instance...")
            if self.browser_context:
                await self.browser_context.close()
                self.browser_context = None
            await self.browser.close()
            self.browser = None
            cleanup(exit_process=False)
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