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
    """Log the progress of the unsubscribe process"""
    print(f"\n[LOG] {message}")
    return ActionResult(extracted_content="Logged successfully")


class GmailAgent:
    def __init__(self, prompt=None):
        # Load environment variables
        load_dotenv()
        
        # Get Portkey configuration from environment variables
        self.portkey_api_base = os.getenv("PORTKEY_API_BASE")
        self.portkey_api_key = os.getenv("PORTKEY_API_KEY")
        self.portkey_virtual_key_anthropic = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Default unsubscribe prompt
        self.default_prompt = os.getenv("GMAIL_AGENT_PROMPT", """
Your task is to help the user unsubscribe from unwanted emails in Gmail.

1. Open gmail.com and log in if necessary
2. Go through the emails in the inbox one by one
3. For each email:
   - Open the email
   - Look for an "unsubscribe" link somewhere in the email (usually at the bottom)
   - If an unsubscribe link is found:
     a. Click on the unsubscribe link
     b. Complete any unsubscribe process - this might open a new tab or show a dialog
     c. If it opens a new tab, confirm the unsubscription on that website or page
     d. Close any new tabs opened during the process and return to Gmail
     e. Log the name of the sender you've unsubscribed from
   - If no unsubscribe link is found, just close the email and move to the next one
4. Continue this process for all visible emails in the inbox

Important instructions:
- Be thorough in finding unsubscribe links - they might be labeled as "manage subscriptions" or similar
- Look for unsubscribe text in small font at the bottom of emails
- After unsubscribing, make sure to come back to the Gmail inbox
- Keep track of which senders you've unsubscribed from
""")
        # Set the prompt if provided during initialization
        self.prompt = prompt if prompt is not None else self.default_prompt

    async def run(self, prompt=None):
        """Run the Gmail agent with the given prompt or default prompt"""
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
        # Access the final result's extracted_content which contains the email summaries
        final_answer = result.final_result()
        print(final_answer)
        return final_answer


if __name__ == "__main__":
    gmail_agent = GmailAgent()
    result = asyncio.run(gmail_agent.run())
