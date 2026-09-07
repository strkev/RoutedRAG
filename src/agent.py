from typing import Dict, Any
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent

from src.models import get_llm, dynamic_model_selection
from src.schemas import Context
from src.tools.registry import registry
from src.sys_prompt import user_role_prompt

checkpointer = InMemorySaver()

def build_agent():
    base_llm = get_llm()
    tools = registry.get_all_tools()
    return create_agent(
        model=base_llm,
        tools=tools,
        middleware=[user_role_prompt, dynamic_model_selection],
        context_schema=Context,
        checkpointer=checkpointer,
    )

agent_instance = build_agent()

def extract_token_usage(response: dict) -> Dict[str, int]:
    total_input = 0
    total_output = 0

    for msg in response.get("messages", []):
        if hasattr(msg, "usage_metadata") and msg.usage_metadata:
            total_input += msg.usage_metadata.get("input_tokens", 0)
            total_output += msg.usage_metadata.get("output_tokens", 0)
        elif hasattr(msg, "response_metadata") and "token_usage" in msg.response_metadata:
            usage = msg.response_metadata["token_usage"]
            total_input += usage.get("prompt_tokens", 0)
            total_output += usage.get("completion_tokens", 0)

    return {
        "prompt_tokens": total_input,
        "completion_tokens": total_output,
        "total_tokens": total_input + total_output
    }
