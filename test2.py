import asyncio
import sys
import os
import logging
import time

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

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
        
        # Initialize the model
        self.llm = ChatOpenAI(
            model='gpt-4o',
            temperature=0.0,
        )
        self.controller = Controller()
        self.browser = None
        self.agent = None
    
    async def setup_browser(self, start_url="https://google.com"):
        """Set up a browser instance with remote debugging."""
        start_chrome(start_url)
        
        self.browser = Browser(
            config=BrowserConfig(
                disable_security=True,
                cdp_url="http://localhost:9222",
            ),
        )
        return self.browser
    
    async def setup_agent(self):
        """Initialize the agent with the current browser."""
        if not self.browser:
            await self.setup_browser()
            
        self.agent = Agent(
            task=self.task,
            llm=self.llm,
            controller=self.controller,
            browser=self.browser,
        )
        return self.agent
    
    async def run_task(self):
        """Run the current task with the agent."""            
        logger.info("Running task: %s", self.task)
        await self.agent.run()
    
    async def cleanup_browser(self):
        """Clean up browser resources."""
        if self.browser:
            logger.info("Cleaning up browser instance...")
            await self.browser.close()
            self.browser = None
            cleanup(exit_process=False)
            # Wait to ensure browser is fully closed
            await asyncio.sleep(3)
    
    def add_new_task(self, new_task):
        """Add a new task to the agent."""
        self.task = new_task
        if self.agent:
            self.agent.add_new_task(new_task)
    
    async def run_sequential_tasks(self, tasks):
        """Run multiple tasks sequentially, creating a new browser for each."""
        try:
            await self.setup_agent()
            for i, task in enumerate(tasks):
                if i > 0:
                    # Clean up previous browser before starting a new one
                    await self.cleanup_browser()
                    
                    # Set up a fresh browser for the next task
                    logger.info(f"Starting fresh Chrome browser for task {i+1}...")
                    await self.setup_browser()
                    
                # Set the current task
                self.task = task
                
                # Set up and run the agent
                await self.run_task()
                
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # Final cleanup
            await self.cleanup_browser()
            logger.info("Cleanup complete")


async def main():
    browser_agent = BrowserAgent()
    try:
        # Define tasks to run sequentially
        tasks = [
            'Summarize my last gmail',
            'Search what you just found on the internet'
        ]
        
        await browser_agent.run_sequential_tasks(tasks)
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Ensure cleanup happens
        await browser_agent.cleanup_browser()


if __name__ == '__main__':
    asyncio.run(main())