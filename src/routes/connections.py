import requests
from fastapi import APIRouter
from src.schemas import ConnectionConfig, MultiConnectionConfig
from src.models import get_connections_data, save_connections_data, get_connection_config

router = APIRouter(prefix="/api", tags=["connections"])

@router.get("/connections")
async def get_connections():
    data = get_connections_data()
    # Rückgabe des Multi-Connection-Formats sowie Top-Level-Felder für Abwärtskompatibilität
    def_conn = get_connection_config(data.get("default_connection"))
    return {
        "default_connection": data.get("default_connection", "uni"),
        "connections": data.get("connections", []),
        "base_url": def_conn.get("base_url", ""),
        "api_key": def_conn.get("api_key", ""),
        "default_model": def_conn.get("default_model", "google/gemma-4-31b-it")
    }

@router.post("/connections")
async def update_connections(payload: dict):
    # Unterstützt sowohl MultiConnectionConfig als auch altes Single-Format
    if "connections" in payload:
        save_connections_data(payload)
    else:
        # Einzelne Verbindung -> Update oder Hinzufügen
        api_key = payload.get("api_key", "")
        base_url = payload.get("base_url", "")
        default_model = payload.get("default_model", "google/gemma-4-31b-it")
        data = get_connections_data()
        def_id = data.get("default_connection", "uni")
        found = False
        for c in data.get("connections", []):
            if c.get("id") == def_id:
                c["api_key"] = api_key
                c["base_url"] = base_url
                c["default_model"] = default_model
                found = True
                break
        if not found:
            data.setdefault("connections", []).append({
                "id": def_id,
                "name": "Standard",
                "base_url": base_url,
                "api_key": api_key,
                "default_model": default_model
            })
        save_connections_data(data)

    return {"status": "success", "message": "Verbindungseinstellungen aktualisiert"}

@router.post("/connections/test")
async def test_connection(conn: ConnectionConfig):
    clean_base = conn.base_url.rstrip('/')
    url = f"{clean_base}/models"
    headers = {"Authorization": f"Bearer {conn.api_key.strip()}"} if conn.api_key and conn.api_key.strip() else {}
    
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            models = []
            if isinstance(data, dict) and "data" in data:
                models = [m.get("id") for m in data["data"] if isinstance(m, dict)]
            elif isinstance(data, list):
                models = [m.get("id") if isinstance(m, dict) else str(m) for m in data]
            return {"status": "success", "reachable": True, "status_code": res.status_code, "models": models}

        # Fallback für Ollama /api/tags falls /v1/models 404 liefert
        if "localhost:11434" in clean_base or "127.0.0.1:11434" in clean_base:
            ollama_url = clean_base.replace("/v1", "") + "/api/tags"
            ores = requests.get(ollama_url, timeout=4)
            if ores.status_code == 200:
                odata = ores.json()
                models = [m.get("name") for m in odata.get("models", []) if isinstance(m, dict)]
                return {"status": "success", "reachable": True, "status_code": 200, "models": models}

        return {"status": "warning", "reachable": True, "status_code": res.status_code, "detail": res.text[:200]}
    except Exception as e:
        return {"status": "error", "reachable": False, "error": str(e)}
