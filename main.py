from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from src.models import get_llm, dynamic_model_selection
from src.schemas import Context
from src.tools import get_weather, locate_user
from src.embeddings import retriever_tool
from src.sys_prompt import user_role_prompt

base_llm = get_llm("gemma-4-31b-it")

checkpointer = InMemorySaver()
tools = [locate_user, get_weather, retriever_tool]

agent = create_agent(
    model=base_llm,
    tools=tools,
    middleware=[user_role_prompt, dynamic_model_selection],
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
print("Modell-Metadaten:", response["messages"][-1].response_metadata)

'''
structured_llm = llm.with_structured_output(WeatherResponse)
structured_result = structured_llm.invoke(f"Extract weather info:\n\n{final_text}")
print("Strukturiert:", structured_result)
'''