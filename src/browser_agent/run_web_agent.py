#!/usr/bin/env python3
import argparse
from dotenv import load_dotenv
from .web_agent import WebAgent

# Load environment variables
load_dotenv()

def run(prompt=None, url=None, cleanup_after=False, skip_chrome_start=False):
    """Main function to run the web automation agent
    
    Args:
        prompt (str): The prompt to send to the web agent
        url (str): Starting URL for the browser
        cleanup_after (bool): Whether to clean up Chrome after this call (default: False)
        skip_chrome_start (bool): Whether to skip starting Chrome (assumes it's already running)
    
    Returns:
        str: The result from the web agent
    """
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Run a web automation agent")
    parser.add_argument("--prompt", type=str, help="Custom prompt for the web agent")
    parser.add_argument("--url", type=str, default="https://google.com", 
                       help="Starting URL for the browser (default: https://google.com)")
    args = parser.parse_args()
    
    try:
        # Use URL from parameter if provided, otherwise from command line args
        start_url = url if url is not None else args.url
        
        # Create the web agent with the initial task if provided
        web_agent = WebAgent(initial_task=prompt if prompt else "")
        
        # If skip_chrome_start is True, don't start Chrome manually
        if not skip_chrome_start:
            # Setup browser with the specified URL
            web_agent.setup_browser(start_url=start_url)
        
        # Run the agent with the prompt
        result = web_agent.run(prompt if prompt else "Summarize my last gmail")
        return result
    
    finally:
        # Only clean up Chrome if specifically requested
        if cleanup_after and web_agent is not None:
            web_agent.cleanup()

if __name__ == "__main__":
    # result = run("Summarize AI according to wiki.")
    result = run("Tell me a joke, don't search or click anything.", cleanup_after=True)
    print(result)
