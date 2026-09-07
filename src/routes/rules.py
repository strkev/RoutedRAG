import os
import json
from fastapi import APIRouter
from src.models import RULES_FILE
from src.schemas import RoutingConfig

router = APIRouter(prefix="/api", tags=["rules"])

@router.get("/rules")
async def get_rules():
    if not os.path.exists(RULES_FILE):
        return {"default_model": "google/gemma-4-31b-it", "rules": []}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@router.post("/rules")
async def save_rules(config: RoutingConfig):
    os.makedirs(os.path.dirname(RULES_FILE), exist_ok=True)
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)
    return {"status": "success", "data": config.model_dump()}
