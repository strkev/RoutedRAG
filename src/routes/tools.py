from fastapi import APIRouter
from src.tools.registry import registry

router = APIRouter(prefix="/api", tags=["tools"])

@router.get("/tools")
async def get_tools():
    return registry.list_metadata()
