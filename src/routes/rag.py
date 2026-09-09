import os
from fastapi import APIRouter, UploadFile, File
from src.schemas import RagConfig
from src.rag_manager import rag_manager
from src.routes.settings import get_current_settings, save_current_settings
from src.logger import logger

router = APIRouter(prefix="/api/rag", tags=["rag"])

@router.get("/status")
async def get_rag_status():
    return rag_manager.get_status()

@router.post("/folder")
async def update_rag_folder(req: RagConfig):
    res = rag_manager.set_folder_path(req.folder_path)
    cur = get_current_settings()
    cur["rag_folder"] = rag_manager.folder_path
    save_current_settings(cur)
    return res

@router.post("/reindex")
async def reindex_rag():
    return rag_manager.reindex()

@router.post("/upload")
async def upload_rag_file(file: UploadFile = File(...)):
    target_path = os.path.join(rag_manager.folder_path, file.filename)
    os.makedirs(rag_manager.folder_path, exist_ok=True)
    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)
    rag_manager.reindex()
    return {"status": "success", "filename": file.filename, "rag_status": rag_manager.get_status()}
