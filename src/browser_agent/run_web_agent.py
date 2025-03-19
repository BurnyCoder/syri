#!/usr/bin/env python3
import asyncio
import argparse
from dotenv import load_dotenv
from .web_agent import WebAgent
from .chrome_manager import start_chrome, cleanup

# Load environment variables
load_dotenv()

def run(prompt=None, url=None):
    """Main function to run the web automation agent"""
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Run a web automation agent")
    parser.add_argument("--prompt", type=str, help="Custom prompt for the web agent")
    parser.add_argument("--url", type=str, default="https://google.com", 
                       help="Starting URL for the browser (default: https://google.com)")
    args = parser.parse_args()
    
    try:
        # Use URL from parameter if provided, otherwise from command line args
        start_url = url if url is not None else args.url
        
        # Start Chrome with remote debugging and the specified URL
        start_chrome(start_url=start_url)
        
        # Create and run the web agent directly
        web_agent = WebAgent()
        result = asyncio.run(web_agent.run(prompt))
        return result
    
    finally:
        # Ensure Chrome is shut down properly
        cleanup()

if __name__ == "__main__":
    # result = run("Summarize AI according to wiki.")
    result = run("Tell me a joke, don't search or click anything.")
