import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call

RULES_FILE = "config/routing_rules.json"

load_dotenv()

def evaluate_rules(user_msg: str, user_role: str | None) -> str:
    if not os.path.exists(RULES_FILE):
        return "google/gemma-4-31b-it"

    with open(RULES_FILE, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    fallback_model = config_data.get("default_model", "google/gemma-4-31b-it")
    rules = config_data.get("rules", [])

    msg_lower = user_msg.lower()

    for rule in rules:
        if not rule.get("active", True):
            continue

        cond_type = rule.get("condition_type")
        val = rule.get("condition_value")
        target = rule.get("target_model")

        match cond_type:
            case "contains_any":
                if any(keyword.lower() in msg_lower for keyword in val):
                    return target

            case "role_equals":
                if user_role and user_role.lower() == str(val).lower():
                    return target

            case "min_length":
                if len(user_msg) >= int(val):
                    return target

    return fallback_model

def get_llm(model_name: str = "gemma-4-31b-it", temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=model_name,
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        temperature=temperature,
    )

def get_embeddings(model_name: str = "mxbai-embed-large:latest") -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=model_name,
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        check_embedding_ctx_length=False
    )


@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    last_user_msg = ""
    for msg in reversed(request.state["messages"]):
        if msg.type == "human" or getattr(msg, "role", "") == "user":
            last_user_msg = str(msg.content)
            break

    user_role = getattr(request.runtime.context, "user_role", None)

    selected_model = evaluate_rules(last_user_msg, user_role)
    print(f"[Rule-Engine] Ausgewähltes Modell: {selected_model}")

    request.model = get_llm(model_name=selected_model)
    return handler(request)