import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from src.routes import (
    chat_router,
    settings_router,
    rules_router,
    connections_router,
    rag_router,
    tools_router
)

app = FastAPI(
    title="RoutedRAG Agent API",
    version="2.1.0",
    description="Modular Agent API with dynamic routing, RAG and Material UI"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/favicon.ico", include_in_schema=False)
@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "RoutedRAG Agent API running. Frontend index.html not yet found in src/static."}

app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(rules_router)
app.include_router(connections_router)
app.include_router(rag_router)
app.include_router(tools_router)
