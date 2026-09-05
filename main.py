from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from src.models import get_llm
from src.schemas import Context, WeatherResponse
from src.tools import get_weather, locate_user

llm = get_llm()
checkpointer = InMemorySaver()
tools = [locate_user, get_weather]

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt = 'You are a helpful weather assistant, who always jokes and is humorous while remaining helpful',
    context_schema=Context,
    checkpointer=checkpointer,
)

config = {'configurable': {'thread_id': '1'}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "What is the weather like?"}]},
    config=config,
    context=Context(userId="ABCD123"),
)

print(response["messages"][-1].content)