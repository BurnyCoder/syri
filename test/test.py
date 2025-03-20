import asyncio
import logging
import os
from dotenv import load_dotenv

from src.browser_agent.web_agent import WebAgent

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    web_agent = WebAgent()
    try:
        # Run tasks from the example
        result1 = asyncio.run(web_agent.run("Summarize last email in my gmail"))
        print(f"Result 1: {result1}")
        
        result2 = asyncio.run(web_agent.run("Search what you just found from the gmail on the internet. Do not go to gmail, just use your memory."))
        print(f"Result 2: {result2}")
        # Clean up the browser after all tasks are completed
        asyncio.run(web_agent.cleanup())
        logger.info("Cleanup complete")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        # Cleanup if exception occurs
        asyncio.run(web_agent.cleanup())


if __name__ == '__main__':
    main()
