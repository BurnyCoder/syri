#!/usr/bin/env python3
import os
import asyncio
import argparse
from dotenv import load_dotenv
from web_agent import WebAgent
from chrome_manager import start_chrome, cleanup

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
        # Get user prompt
        user_prompt = prompt
        
        # If no prompt parameter was passed, check command line args
        if user_prompt is None:
            if not args.prompt:
                print("\nPlease describe the web task you want the agent to perform:")
                user_prompt = input("> ").strip()
            else:
                # Use command line prompt if provided
                user_prompt = args.prompt
        
        # Use URL from parameter if provided, otherwise from command line args
        start_url = url if url is not None else args.url
        
        # Start Chrome with remote debugging and the specified URL
        start_chrome(start_url=start_url)
        
        # Create and run the web agent directly
        web_agent = WebAgent(user_prompt)
        return asyncio.run(web_agent.run())
    
    finally:
        # Ensure Chrome is shut down properly
        cleanup()

if __name__ == "__main__":
    run("Find cutest cats.")