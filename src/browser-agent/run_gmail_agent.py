#!/usr/bin/env python3
import os
import asyncio
from dotenv import load_dotenv
from gmail_agent import GmailAgent
from chrome_manager import start_chrome, cleanup

# Load environment variables
load_dotenv()

async def run_agent(prompt: str):
    """Run the unsubscribe agent with the given prompt"""
    gmail_agent = GmailAgent(prompt)
    return await gmail_agent.run()

def main():
    """Main function to run the entire process"""
    
    try:
        # Start Chrome with remote debugging
        start_chrome()
        
        # Default prompt for the agent
        default_prompt = os.getenv("GMAIL_AGENT_PROMPT", """
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
        
        # """
        # Your task is to help the user summarize the most recent email in Gmail.

        # 1. Open gmail.com and log in if necessary
        # 2. Identify the most recent email in the inbox
        # 3. For this email:
        #    - Open the email
        #    - Extract the following information:
        #      a. Sender name and email address
        #      b. Subject line
        #      c. Date and time received
        #      d. Main content/body of the email (summarized)
        #    - Log a concise summary of the email
        #    - Close the email

        # Important instructions:
        # - Focus only on the most recent email
        # - Create clear, structured summaries that capture the key information
        # - Respect privacy by not sharing sensitive information
        # - Return to the Gmail inbox after summarizing the email
        # - Log the summary after completing it
        # """)
        
        # Run the agent
        asyncio.run(run_agent(default_prompt))
    
    finally:
        # Ensure Chrome is shut down properly
        cleanup()

if __name__ == "__main__":
    main() 