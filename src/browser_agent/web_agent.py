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
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get Portkey configuration from environment variables
        self.portkey_api_base = os.getenv("PORTKEY_API_BASE")
        self.portkey_api_key = os.getenv("PORTKEY_API_KEY")
        self.portkey_virtual_key_anthropic = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Additional instructions to append to the web agent prompt
        self.additional_prompt = os.getenv("WEB_AGENT_PROMPT", "")
            
        # Set up Portkey headers for Anthropic/Claude
        portkey_headers = createHeaders(
            api_key=self.portkey_api_key, 
            provider="anthropic",
            virtual_key=self.portkey_virtual_key_anthropic
        )
        
        # Create LLM with Portkey configuration using Claude
        self.llm = ChatAnthropic(
            model="claude-3-7-sonnet-latest",
            api_key=self.portkey_virtual_key_anthropic,  # Using the virtual key as the API key
            base_url=self.portkey_api_base,  # Using the custom API base
            default_headers=portkey_headers
        )
        
        self.initialized = False
        

    async def run(self, prompt=None):
        """Run the web agent with the given prompt or current task"""
        # If prompt is provided, add it as a new task
        if prompt is not None:
            # Apply additional instructions if available
            full_prompt = prompt + " " + self.additional_prompt if self.additional_prompt else prompt
            
            if not self.initialized:
                # For the first task, set it directly
                        # Initialize the agent with a default empty task - this fixes the missing 'task' parameter error
                self.agent = Agent(
                    browser=Browser(
                        config=BrowserConfig(
                            disable_security=True,
                            cdp_url="http://localhost:9222",
                        ),
                    ),
                    llm=self.llm,  # Use the Portkey-configured Claude LLM
                    controller=controller,
                    task=full_prompt
                )
                self.initialized = True
            else:
                # For subsequent tasks, use add_new_task
                self.agent.add_new_task(full_prompt)
                
        result = await self.agent.run()
        
        # Access the final result
        final_answer = result.final_result()
        print(final_answer)
        return final_answer
        

if __name__ == "__main__":
    async def main():
        web_agent = WebAgent()
        
        result = await web_agent.run("Find information about browser automation tools")
        
    asyncio.run(main())
