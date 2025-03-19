# Gmail Unsubscribe Agent

This is an automated agent that helps you manage your Gmail inbox by either:
- Unsubscribing from unwanted emails (default functionality)
- Summarizing your most recent emails

The agent uses Chrome browser automation and LLM-powered browsing to navigate through Gmail.

This project leverages browser-use and Anthropic Claude via Portkey API gateway using Langchain.

## Prerequisites

- Python 3.11 or higher
- Chrome or Chromium browser
- API keys for Anthropic Claude (via Portkey)

## Setup

1. Make sure you have all dependencies installed:
   ```
   pip install -r requirements.txt
   ```

2. Copy the environment template to create your own `.env` file:
   ```
   cp .envtemplate .env
   ```

3. Edit the `.env` file to add your API keys:
   ```
   PORTKEY_API_BASE=your_portkey_api_base_here
   PORTKEY_API_KEY=your_portkey_api_key_here
   PORTKEY_VIRTUAL_KEY_ANTHROPIC=your_portkey_virtual_key_here
   # Optional: You can customize the agent's behavior by setting a custom prompt
   GMAIL_AGENT_PROMPT="Your custom prompt here"
   ```

## Running the Agent

There are two ways to run the agent:

### Option 1: Manual two-step process, good for first time

1. First, start Chrome with remote debugging enabled:
   ```
   python chrome_manager.py
   ```
   This will open Chrome to Gmail. You may need to log in to your Gmail account.

2. Once Chrome is running with remote debugging, run the agent:
   ```
   python gmail_agent.py
   ```

### Option 2: Using the integrated script (when you're logged in already)

Run the all-in-one script that handles both Chrome startup and the agent:

```
python run_gmail_agent.py
```

This script will:
- Start Chrome with remote debugging enabled
- Navigate to Gmail 
- Run the agent to process your emails
- Properly clean up when finished or interrupted
