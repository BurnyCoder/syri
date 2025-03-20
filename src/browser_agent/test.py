import os
from dotenv import load_dotenv
from .web_agent import WebAgent
from .chrome_manager import start_chrome, cleanup

# Load environment variables
load_dotenv()

def run_browser_agent(prompt):
    """
    Run a browser agent with the given prompt.
    
    Args:
        prompt (str): The task prompt for the agent
        
    Returns:
        str: The final result from the agent
    """
    try:
        # Start Chrome
        start_chrome()
        
        # Create a WebAgent instance
        web_agent = WebAgent()
        
        # Run the task
        result = web_agent.run(prompt)
        
        print(result)
        return result
    finally:
        # Make sure to clean up
        if 'web_agent' in locals() and web_agent is not None:
            web_agent.cleanup()


if __name__ == "__main__":
    default_prompt = """
    Your task is to find cats on wikipedia and tell me which one is the cutest.
    """
    result = run_browser_agent(default_prompt)
