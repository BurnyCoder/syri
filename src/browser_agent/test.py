from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL
import os

from browser_use import Agent, BrowserConfig, Browser
import asyncio
from dotenv import load_dotenv
from browser_use import Controller, ActionResult
controller = Controller()

load_dotenv()

# Get Portkey configuration from environment variables
PORTKEY_API_BASE = os.getenv("PORTKEY_API_BASE")
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
PORTKEY_VIRTUAL_KEY_ANTHROPIC = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")

async def run_browser_agent(prompt):
    """
    Run a browser agent with the given prompt.
    
    Args:
        prompt (str): The task prompt for the agent
        
    Returns:
        str: The final result from the agent
    """
    # Set up Portkey headers for Anthropic/Claude
    portkey_headers = createHeaders(
        api_key=PORTKEY_API_KEY, 
        provider="anthropic",
        virtual_key=PORTKEY_VIRTUAL_KEY_ANTHROPIC
    )
    
    # Create LLM with Portkey configuration using Claude
    llm = ChatAnthropic(
        model="claude-3-7-sonnet-latest",
        api_key=PORTKEY_VIRTUAL_KEY_ANTHROPIC,  # Using the virtual key as the API key
        base_url=PORTKEY_API_BASE,  # Using the custom API base
        default_headers=portkey_headers
    )
    
    agent = Agent(
        browser=Browser(
            config=BrowserConfig(
                disable_security=True,
                cdp_url="http://localhost:9222",
            ),
        ),
        task=prompt,
        llm=llm,  # Use the Portkey-configured Claude LLM
        controller=controller
    )
    result = await agent.run()
    # Access the final result's extracted_content which contains the email summaries
    final_answer = result.final_result()
    print(final_answer)
    return final_answer


if __name__ == "__main__":
    default_prompt = """
    Your task is to find cats on wikipedia and tell me which one is the cutest.
    """
    result = asyncio.run(run_browser_agent(default_prompt))
