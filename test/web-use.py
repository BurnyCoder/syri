import asyncio
import sys
import os
import logging
import time

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from portkey_ai import createHeaders

from browser_use import Agent, BrowserConfig, Browser
from browser_use.agent.views import ActionResult
from browser_use.controller.service import Controller
from browser_use.browser.context import BrowserContext

# Import Chrome manager
from src.browser_agent.chrome_manager import start_chrome, cleanup

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrowserAgent:
    """Class to manage browser-based agent interactions."""
    
    def __init__(self, initial_task="Summarize my last gmail"):
        """Initialize the BrowserAgent with configuration."""
        self.task = initial_task
        
        # Get Portkey configuration from environment variables
        self.portkey_api_base = os.getenv("PORTKEY_API_BASE")
        self.portkey_api_key = os.getenv("PORTKEY_API_KEY")
        self.portkey_virtual_key_anthropic = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Set up Portkey headers for Anthropic/Claude
        portkey_headers = createHeaders(
            api_key=self.portkey_api_key, 
            provider="anthropic",
            virtual_key=self.portkey_virtual_key_anthropic
        )
        
        # Initialize the model with Claude instead of GPT-4o
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
    
    async def setup_browser(self, start_url="https://google.com"):
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
            # Set up the browser first if not already done
            if not self.browser:
                await self.setup_browser()
                
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
            await self.agent.run()
                
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # We don't clean up browser here to allow for subsequent tasks


async def main():
    browser_agent = BrowserAgent()
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
    asyncio.run(main())