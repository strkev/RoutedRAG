import os
import requests
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool

load_dotenv()

llm = ChatOpenAI(
    model = 'gemma-4-31b-it',
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL")
)

@tool('get_weather', description="Return weather information for a giben city", return_direct=False)
def get_weather(city: str):
    return f"It's always sunny in {city}!"

agent = create_agent(
    model = llm,
    tools = [get_weather],
    system_prompt = 'You are a helpful weather assistant, who always jokes and is humorous while remaining helpful'
)

response = agent.invoke({
    'messages':[
        {'role': 'user', 'content':'What is the weather like in Oberursel?'}
    ]
})

print(response["messages"][-1].content_blocks)