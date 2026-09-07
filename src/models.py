import os
import json
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call

RULES_FILE = "config/routing_rules.json"
CONNECTIONS_FILE = "config/connections.json"

load_dotenv()

def get_connections_data() -> Dict[str, Any]:
    """Liefert das vollständige Konfigurationsobjekt aller Provider-Verbindungen."""
    if os.path.exists(CONNECTIONS_FILE):
        try:
            with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                # Falls altes Format: { "base_url": ..., "api_key": ..., "default_model": ... }
                if "connections" not in raw and "base_url" in raw:
                    migrated = {
                        "default_connection": "uni",
                        "connections": [
                            {
                                "id": "uni",
                                "name": "Standard (Uni / Cloud)",
                                "base_url": raw.get("base_url", ""),
                                "api_key": raw.get("api_key", ""),
                                "default_model": raw.get("default_model", "google/gemma-4-31b-it")
                            }
                        ]
                    }
                    save_connections_data(migrated)
                    return migrated
                return raw
        except Exception as e:
            print(f"[Config] Error reading connections file: {e}")

    default_conn = {
        "id": "uni",
        "name": "Uni Open-WebUI",
        "base_url": os.getenv("BASE_URL", "https://open-webui.lc.users.h-da.cloud/api").strip().strip('"').strip("'"),
        "api_key": os.getenv("API_KEY", ""),
        "default_model": os.getenv("DEFAULT_MODEL", "google/gemma-4-31b-it")
    }
    return {
        "default_connection": "uni",
        "connections": [default_conn]
    }

def save_connections_data(data: Dict[str, Any]) -> bool:
    """Speichert die Multi-Provider-Verbindungsliste ab."""
    os.makedirs(os.path.dirname(CONNECTIONS_FILE), exist_ok=True)
    try:
        with open(CONNECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Aktive Standard-Verbindung auch in ENV spiegeln
        def_conn = get_connection_config(data.get("default_connection"))
        if def_conn:
            os.environ["API_KEY"] = def_conn.get("api_key", "")
            os.environ["BASE_URL"] = def_conn.get("base_url", "")
        return True
    except Exception as e:
        print(f"[Config] Error saving connections: {e}")
        return False

def get_connection_config(conn_id: Optional[str] = None) -> Dict[str, Any]:
    """Liefert die Konfiguration für eine bestimmte Verbindung oder die Standard-Verbindung."""
    data = get_connections_data()
    conns: List[Dict[str, Any]] = data.get("connections", [])
    
    if conn_id:
        for c in conns:
            if c.get("id") == conn_id:
                return c
                
    default_id = data.get("default_connection")
    for c in conns:
        if c.get("id") == default_id:
            return c
            
    if conns:
        return conns[0]

    return {
        "id": "default",
        "name": "Standard",
        "base_url": os.getenv("BASE_URL", "").strip().strip('"').strip("'"),
        "api_key": os.getenv("API_KEY", ""),
        "default_model": os.getenv("DEFAULT_MODEL", "google/gemma-4-31b-it")
    }

def save_connection_config(api_key: str, base_url: str, default_model: str = "google/gemma-4-31b-it") -> bool:
    """Kompatibilitätsfunktion zum Aktualisieren der Standard-Verbindung."""
    data = get_connections_data()
    def_id = data.get("default_connection", "uni")
    updated = False
    for c in data.get("connections", []):
        if c.get("id") == def_id:
            c["api_key"] = api_key
            c["base_url"] = base_url.strip().strip('"').strip("'")
            c["default_model"] = default_model
            updated = True
            break
    if not updated:
        data.setdefault("connections", []).append({
            "id": def_id,
            "name": "Standard",
            "base_url": base_url.strip().strip('"').strip("'"),
            "api_key": api_key,
            "default_model": default_model
        })
    return save_connections_data(data)

def evaluate_rules(user_msg: str, user_role: str | None = None) -> Tuple[str, str]:
    """
    Vereinfachtes Themen- und Schlüsselwort-Matching (Topic Keyword Matching).
    Prüft, ob Wörter im Benutzerprompt vorkommen und wählt (target_model, target_connection).
    """
    def_conn_cfg = get_connection_config()
    fallback_model = def_conn_cfg.get("default_model", "google/gemma-4-31b-it")
    fallback_conn = def_conn_cfg.get("id", "uni")

    if not os.path.exists(RULES_FILE):
        return fallback_model, fallback_conn

    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception:
        return fallback_model, fallback_conn

    fallback_model = config_data.get("default_model") or fallback_model
    fallback_conn = config_data.get("default_connection") or fallback_conn
    rules = config_data.get("rules", [])

    msg_lower = user_msg.lower()

    for rule in rules:
        if not rule.get("active", True):
            continue

        target_model = rule.get("target_model") or fallback_model
        target_conn = rule.get("target_connection") or fallback_conn

        # 1. Neue vereinfachte Struktur: "keywords": ["python", "sql", "code"]
        keywords = rule.get("keywords")
        if keywords:
            if any(str(kw).strip().lower() in msg_lower for kw in keywords if str(kw).strip()):
                return target_model, target_conn

        # 2. Abwärtskompatibilität mit condition_type
        cond_type = rule.get("condition_type")
        val = rule.get("condition_value")
        if cond_type == "contains_any":
            if isinstance(val, list):
                if any(str(kw).strip().lower() in msg_lower for kw in val if str(kw).strip()):
                    return target_model, target_conn
            elif isinstance(val, str):
                kws = [k.strip().lower() for k in val.split(",") if k.strip()]
                if any(k in msg_lower for k in kws):
                    return target_model, target_conn

    return fallback_model, fallback_conn

def get_llm(model_name: Optional[str] = None, connection_id: Optional[str] = None, temperature: float = 0.3) -> ChatOpenAI:
    conn = get_connection_config(connection_id)
    final_model = model_name or conn.get("default_model", "google/gemma-4-31b-it")
    raw_base_url = conn.get("base_url") or os.getenv("BASE_URL", "").strip().strip('"').strip("'")
    base_url = raw_base_url.strip()

    # Für lokale Provider wie Ollama ist kein API-Key erforderlich,
    # der OpenAI-Client verlangt jedoch einen nicht-leeren String:
    raw_api_key = conn.get("api_key")
    api_key = raw_api_key.strip() if raw_api_key and raw_api_key.strip() else "ollama"

    return ChatOpenAI(
        model=final_model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        timeout=60.0,
    )

def get_embeddings(model_name: str = "mxbai-embed-large:latest") -> OpenAIEmbeddings:
    conn = get_connection_config()
    raw_api_key = conn.get("api_key")
    api_key = raw_api_key.strip() if raw_api_key and raw_api_key.strip() else "ollama"
    raw_base_url = conn.get("base_url") or os.getenv("BASE_URL", "").strip().strip('"').strip("'")
    base_url = raw_base_url.strip()
    if "11434" in base_url:
        if base_url.endswith("/api"):
            base_url = base_url[:-4] + "/v1"
        elif not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"

    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        check_embedding_ctx_length=False,
        timeout=20.0,
    )

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    context = getattr(request.runtime, "context", None)
    dynamic_enabled = getattr(context, "dynamic_model", True) if context else True
    
    if not dynamic_enabled:
        selected_model = getattr(context, "selected_model", None)
        selected_conn = getattr(context, "selected_connection", None)
        def_conn = get_connection_config(selected_conn)
        selected_model = selected_model or def_conn.get("default_model", "google/gemma-4-31b-it")
        selected_conn = selected_conn or def_conn.get("id", "uni")
        print(f"[Model-Selector] Manuelles Modell: {selected_model} (Provider: {selected_conn})")
    else:
        # 1. Bevorzuge user_message direkt aus dem Context
        user_msg = getattr(context, "user_message", "")
        # 2. Fallback: Nachrichten im State durchsuchen
        if not user_msg and hasattr(request, "state") and "messages" in request.state:
            for msg in reversed(request.state["messages"]):
                msg_role = getattr(msg, "type", None) or getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
                if msg_role in ("human", "user"):
                    content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
                    if content:
                        user_msg = str(content)
                        break

        selected_model, selected_conn = evaluate_rules(user_msg)
        print(f"[Rule-Engine] Dynamisch gewählt: {selected_model} (Provider: {selected_conn}) für User-Prompt: {user_msg[:50]}")

    if context:
        setattr(context, "selected_model", selected_model)
        setattr(context, "selected_connection", selected_conn)

    new_model = get_llm(model_name=selected_model, connection_id=selected_conn)
    if hasattr(request, "tools") and request.tools:
        request.model = new_model.bind_tools(request.tools)
    else:
        request.model = new_model

    return handler(request)
