import asyncio
import sys
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from browser_use import Agent, Browser, BrowserConfig
from browser_use.agent.views import ActionResult
from browser_use.controller.service import Controller
from browser_use.browser.context import BrowserContext

# Reuse existing browser
browser = Browser()
load_dotenv()

# Initialize the model
llm = ChatOpenAI(
	model='gpt-4o',
	temperature=0.0,
)
controller = Controller()


task = 'Summarize my last gmail'


async def main():
	
	try:
		# Initialize the agent with Chrome browser
		agent = Agent(
			task=task,
			llm=llm,
			controller=controller,
			browser=browser,
		)
		
		await agent.run()

		# new_task = input('Type in a new task: ')
		new_task = 'Search about it on the internet'

		agent.add_new_task(new_task)

		await agent.run()
	finally:
		# Clean up Chrome process when done
		await browser.close()


if __name__ == '__main__':
	asyncio.run(main())