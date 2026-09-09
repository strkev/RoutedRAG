import httpx
from fastapi import APIRouter
from src.schemas import ConnectionConfig, MultiConnectionConfig
from src.models import get_connections_data, save_connections_data, get_connection_config
from src.logger import logger

router = APIRouter(prefix="/api", tags=["connections"])

@router.get("/connections")
async def get_connections():
    data = get_connections_data()
    def_conn = get_connection_config(data.get("default_connection"))
    return {
        "default_connection": data.get("default_connection") or "",
        "connections": data.get("connections", []),
        "base_url": def_conn.get("base_url", ""),
        "api_key": def_conn.get("api_key", ""),
        "default_model": def_conn.get("default_model", "")
    }

@router.post("/connections")
async def update_connections(payload: dict):
    if "connections" in payload:
        save_connections_data(payload)
    else:
        api_key = payload.get("api_key", "")
        base_url = payload.get("base_url", "")
        default_model = payload.get("default_model", "")
        data = get_connections_data()
        def_id = data.get("default_connection") or "default"
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
                "name": "Standard Provider",
                "base_url": base_url,
                "api_key": api_key,
                "default_model": default_model
            })
            data["default_connection"] = def_id
        save_connections_data(data)

    logger.info("Provider-Verbindungseinstellungen aktualisiert.")
    return {"status": "success", "message": "Verbindungseinstellungen aktualisiert"}

@router.post("/connections/test")
async def test_connection(conn: ConnectionConfig):
    clean_base = conn.base_url.rstrip('/')
    url = f"{clean_base}/models"
    headers = {"Authorization": f"Bearer {conn.api_key.strip()}"} if conn.api_key and conn.api_key.strip() else {}
    
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                models = []
                if isinstance(data, dict) and "data" in data:
                    models = [m.get("id") for m in data["data"] if isinstance(m, dict)]
                elif isinstance(data, list):
                    models = [m.get("id") if isinstance(m, dict) else str(m) for m in data]
                return {"status": "success", "reachable": True, "status_code": res.status_code, "models": models}

            if "localhost:11434" in clean_base or "127.0.0.1:11434" in clean_base:
                ollama_url = clean_base.replace("/v1", "") + "/api/tags"
                ores = await client.get(ollama_url)
                if ores.status_code == 200:
                    odata = ores.json()
                    models = [m.get("name") for m in odata.get("models", []) if isinstance(m, dict)]
                    return {"status": "success", "reachable": True, "status_code": 200, "models": models}

            return {"status": "warning", "reachable": True, "status_code": res.status_code, "detail": res.text[:200]}
    except Exception as e:
        logger.warning(f"Verbindungstest fehlgeschlagen fuer {conn.base_url}: {e}")
        return {"status": "error", "reachable": False, "error": str(e)}
