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
        
        # Additional instructions to append to the web agent prompt
        self.additional_prompt = os.getenv("WEB_AGENT_PROMPT", "")
        # Set the prompt if provided during initialization, or use the additional prompt
        if prompt is not None:
            self.prompt = prompt + " " + self.additional_prompt if self.additional_prompt else prompt
        else:
            self.prompt = self.additional_prompt

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
