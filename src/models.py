import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call

RULES_FILE = "config/routing_rules.json"
CONNECTIONS_FILE = "config/connections.json"

load_dotenv()

def get_connection_config() -> dict:
    if os.path.exists(CONNECTIONS_FILE):
        try:
            with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Error reading connections file: {e}")
    
    return {
        "api_key": os.getenv("API_KEY", ""),
        "base_url": os.getenv("BASE_URL", "").strip().strip('"').strip("'"),
        "default_model": os.getenv("DEFAULT_MODEL", "google/gemma-4-31b-it")
    }

def save_connection_config(api_key: str, base_url: str, default_model: str = "google/gemma-4-31b-it") -> bool:
    os.makedirs(os.path.dirname(CONNECTIONS_FILE), exist_ok=True)
    try:
        with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "api_key": api_key,
                "base_url": base_url.strip().strip('"').strip("'"),
                "default_model": default_model
            }, f, indent=2)
        os.environ["API_KEY"] = api_key
        os.environ["BASE_URL"] = base_url.strip().strip('"').strip("'")
        return True
    except Exception as e:
        print(f"[Config] Error saving connection: {e}")
        return False

def evaluate_rules(user_msg: str, user_role: str | None) -> str:
    if not os.path.exists(RULES_FILE):
        return get_connection_config().get("default_model", "google/gemma-4-31b-it")

    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception:
        return "google/gemma-4-31b-it"

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
                if isinstance(val, list):
                    if any(str(keyword).lower() in msg_lower for keyword in val):
                        return target
                elif isinstance(val, str):
                    keywords = [k.strip().lower() for k in val.split(",") if k.strip()]
                    if any(k in msg_lower for k in keywords):
                        return target

            case "role_equals":
                if user_role and user_role.lower() == str(val).lower():
                    return target

            case "min_length":
                if len(user_msg) >= int(val):
                    return target

    return fallback_model

def get_llm(model_name: str = "google/gemma-4-31b-it", temperature: float = 0.3) -> ChatOpenAI:
    conn = get_connection_config()
    api_key = conn.get("api_key") or os.getenv("API_KEY")
    base_url = conn.get("base_url") or os.getenv("BASE_URL", "").strip().strip('"').strip("'")
    
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        timeout=30.0,
    )

def get_embeddings(model_name: str = "mxbai-embed-large:latest") -> OpenAIEmbeddings:
    conn = get_connection_config()
    api_key = conn.get("api_key") or os.getenv("API_KEY")
    base_url = conn.get("base_url") or os.getenv("BASE_URL", "").strip().strip('"').strip("'")

    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        check_embedding_ctx_length=False,
        timeout=15.0,
    )

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    context = getattr(request.runtime, "context", None)
    dynamic_enabled = getattr(context, "dynamic_model", True) if context else True
    
    if not dynamic_enabled:
        selected_model = getattr(context, "selected_model", None) or get_connection_config().get("default_model", "google/gemma-4-31b-it")
        print(f"[Model-Selector] Manuelles Modell gewählt (Dynamic AUS): {selected_model}")
    else:
        last_user_msg = ""
        for msg in reversed(request.state["messages"]):
            if msg.type == "human" or getattr(msg, "role", "") == "user":
                last_user_msg = str(msg.content)
                break

        user_role = getattr(context, "user_role", None) if context else None
        selected_model = evaluate_rules(last_user_msg, user_role)
        print(f"[Rule-Engine] Dynamisch gewähltes Modell (Dynamic AN): {selected_model}")

    if context:
        setattr(context, "selected_model", selected_model)

    request.model = get_llm(model_name=selected_model)
    return handler(request)
