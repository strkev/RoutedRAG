import requests
from fastapi import APIRouter
from src.schemas import ConnectionConfig
from src.models import get_connection_config, save_connection_config

router = APIRouter(prefix="/api", tags=["connections"])

@router.get("/connections")
async def get_connections():
    cfg = get_connection_config()
    return {
        "base_url": cfg.get("base_url", ""),
        "api_key": cfg.get("api_key", ""),
        "default_model": cfg.get("default_model", "google/gemma-4-31b-it")
    }

@router.post("/connections")
async def update_connections(conn: ConnectionConfig):
    save_connection_config(conn.api_key, conn.base_url, conn.default_model)
    return {"status": "success", "message": "Verbindungseinstellungen aktualisiert"}

@router.post("/connections/test")
async def test_connection(conn: ConnectionConfig):
    url = f"{conn.base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {conn.api_key}"} if conn.api_key else {}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            models = []
            if isinstance(data, dict) and "data" in data:
                models = [m.get("id") for m in data["data"] if isinstance(m, dict)]
            return {"status": "success", "reachable": True, "status_code": res.status_code, "models": models}
        return {"status": "warning", "reachable": True, "status_code": res.status_code, "detail": res.text[:200]}
    except Exception as e:
        return {"status": "error", "reachable": False, "error": str(e)}
