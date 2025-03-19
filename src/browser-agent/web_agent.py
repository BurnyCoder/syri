from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL
import os

from browser_use import Agent, BrowserConfig, Browser
import asyncio
from dotenv import load_dotenv
from browser_use import Controller, ActionResult

# Create a controller instance
controller = Controller()

# We can remove the ask_human action since we won't be asking for confirmation
# But we'll keep a logging action to track progress

@controller.action('Log progress')
def log_progress(message: str) -> str:
    """Log the progress of web tasks"""
    print(f"\n[LOG] {message}")
    return ActionResult(extracted_content="Logged successfully")


class WebAgent:
    def __init__(self, prompt=None):
        # Load environment variables
        load_dotenv()
        
        # Get Portkey configuration from environment variables
        self.portkey_api_base = os.getenv("PORTKEY_API_BASE")
        self.portkey_api_key = os.getenv("PORTKEY_API_KEY")
        self.portkey_virtual_key_anthropic = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Default general-purpose web agent prompt
        self.default_prompt = os.getenv("WEB_AGENT_PROMPT", """
You are a helpful web automation assistant. You can navigate websites, interact with elements, 
and perform tasks on behalf of the user. Follow the user's instructions carefully and use your 
browser control abilities to complete the requested task.

Guidelines:
1. Navigate to the requested websites
2. Interact with elements (click, type, scroll) as needed
3. Read and extract information when asked
4. Complete multi-step processes by breaking them down
5. Log your progress at each significant step
6. Be thorough and detailed in your actions

Remember to:
- Look for the most efficient path to complete tasks
- Handle login forms and authentication when necessary 
- Handle popups, modals, and other interactive elements
- Wait for pages to load completely before proceeding
- Return to previous pages when needed
- Log any errors or obstacles encountered
""")
        # Set the prompt if provided during initialization
        self.prompt = prompt if prompt is not None else self.default_prompt

    async def run(self, prompt=None):
        """Run the web agent with the given prompt or default prompt"""
        # Use the prompt passed to run() method, or the one set during initialization, or the default
        if prompt is not None:
            self.prompt = prompt
            
        # Set up Portkey headers for Anthropic/Claude
        portkey_headers = createHeaders(
            api_key=self.portkey_api_key, 
            provider="anthropic",
            virtual_key=self.portkey_virtual_key_anthropic
        )
        
        # Create LLM with Portkey configuration using Claude
        llm = ChatAnthropic(
            model="claude-3-7-sonnet-latest",
            api_key=self.portkey_virtual_key_anthropic,  # Using the virtual key as the API key
            base_url=self.portkey_api_base,  # Using the custom API base
            default_headers=portkey_headers
        )
        
        agent = Agent(
            browser=Browser(
                config=BrowserConfig(
                    disable_security=True,
                    cdp_url="http://localhost:9222",
                ),
            ),
            task=self.prompt,
            llm=llm,  # Use the Portkey-configured Claude LLM
            controller=controller
        )
        result = await agent.run()
        # Access the final result
        final_answer = result.final_result()
        print(final_answer)
        return final_answer


if __name__ == "__main__":
    web_agent = WebAgent()
    result = asyncio.run(web_agent.run())
