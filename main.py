from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from src.models import get_llm
from src.schemas import Context
from src.tools import get_weather, locate_user
from src.embeddings import retriever_tool
from src.sys_prompt import user_role_prompt

llm = get_llm()
checkpointer = InMemorySaver()
tools = [locate_user, get_weather, retriever_tool]

agent = create_agent(
    model=llm,
    tools=tools,
    middleware=[user_role_prompt],
    context_schema=Context,
    checkpointer=checkpointer,
)

config = {'configurable': {'thread_id': '1'}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "What is the weather like? And what do you know about Apple?"}]},
    config=config,
    context=Context(userId="ABCD123", user_role="yoda"),
)

final_text = response["messages"][-1].content
print(response["messages"][-1].content)

'''
structured_llm = llm.with_structured_output(WeatherResponse)
structured_result = structured_llm.invoke(f"Extract weather info:\n\n{final_text}")
print("Strukturiert:", structured_result)
'''