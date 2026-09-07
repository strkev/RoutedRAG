import os
import json
from fastapi import APIRouter
from src.schemas import AppSettings
from src.sys_prompt import PERSONALITIES
from src.models import get_connection_config
from src.rag_manager import rag_manager

router = APIRouter(prefix="/api", tags=["settings"])

SETTINGS_FILE = "config/app_settings.json"

def get_current_settings() -> dict:
    defaults = {
        "dynamic_model_enabled": True,
        "active_personality": "default",
        "default_model": get_connection_config().get("default_model", "google/gemma-4-31b-it"),
        "rag_folder": rag_manager.folder_path,
        "custom_prompt": ""
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
                defaults.pop("user_id", None)
                return defaults
        except Exception:
            pass
    return defaults

def save_current_settings(settings: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

@router.get("/settings")
async def get_settings():
    return get_current_settings()

@router.post("/settings")
async def update_settings(settings: AppSettings):
    cur = get_current_settings()
    cur["dynamic_model_enabled"] = settings.dynamic_model_enabled
    cur["active_personality"] = settings.active_personality
    cur["default_model"] = settings.default_model
    cur["custom_prompt"] = settings.custom_prompt
    cur.pop("user_id", None)
    save_current_settings(cur)
    return cur

@router.get("/personalities")
async def get_personalities():
    return list(PERSONALITIES.values())
