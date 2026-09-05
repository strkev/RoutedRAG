import os
import requests
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

llm = ChatOpenAI(
    model = 'gemma-4-31b-it',
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL")
)

conversation = [
    SystemMessage('You are a helpful weather assistant, who always jokes and is humorous while remaining helpful'),
    HumanMessage('What is Python?'),
    AIMessage('A paper and sissors game'),
    HumanMessage('Really?')
]

@tool('get_weather', description="Return weather information for a giben city", return_direct=False)
def get_weather(city: str):
    return f"It's always sunny in {city}!"

agent = create_agent(
    model = llm,
    tools = [get_weather],
    system_prompt = 'You are a helpful weather assistant, who always jokes and is humorous while remaining helpful'
)

for chunk, _ in agent.stream({"messages": conversation}, stream_mode="messages"):
    if chunk.content:
        print(chunk.content, end="", flush=True)