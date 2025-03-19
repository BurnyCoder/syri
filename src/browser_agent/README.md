# Web Agent

This is a flexible, general-purpose web agent that can perform various tasks on the web based on user prompts. The agent uses Chrome browser automation and LLM-powered browsing to navigate and interact with websites.

This project leverages browser-use and Anthropic Claude via Portkey API gateway using Langchain.

## Features

- Execute any web automation task specified by the user
- Navigate websites, interact with elements, and extract information
- Complete multi-step processes by breaking them down
- Handle login forms, popups, and authentication when necessary
- Log progress at each significant step

## Example Use Cases

- Unsubscribing from unwanted emails in Gmail
- Summarizing emails in your inbox
- Product research and price comparison
- Filling out forms and applications
- Data extraction from websites
- Automated testing of web applications
- Content creation and publishing

## Prerequisites

- Python 3.11 or higher
- Chrome or Chromium browser
- API keys for Anthropic Claude (via Portkey)

## Running the Agent

### Basic Usage

Run the agent with the default prompt and starting URL (Google):

```
python run_web_agent.py
```

The agent will prompt you to enter your task and then execute it.

### Custom Instructions

You can provide a custom prompt and starting URL:

```
python run_web_agent.py --prompt "Your task is to search for recent news about AI and summarize the top 3 articles" --url "https://news.google.com"
```

### Manual Two-Step Process

For more control, you can start the Chrome browser separately:

1. First, start Chrome with remote debugging enabled:
   ```
   python chrome_manager.py
   ```

2. Once Chrome is running with remote debugging, run the agent:
   ```
   python gmail_agent.py  # Using the original file
   ```
