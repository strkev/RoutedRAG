from dataclasses import dataclass
from pydantic import BaseModel
from typing import Literal, Union, Optional, List, Dict, Any

@dataclass
class Context:
    """Runtime context passed to agent and middlewares."""
    user_role: str = "default"
    dynamic_model: bool = True
    selected_model: Optional[str] = None
    custom_prompt: Optional[str] = None

class RoutingRule(BaseModel):
    id: str
    name: str
    target_model: str
    condition_type: Literal["role_equals", "contains_any", "min_length"]
    condition_value: Union[str, List[str], int]
    active: bool = True

class RoutingConfig(BaseModel):
    default_model: str
    rules: List[RoutingRule]

class ChatMessageRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    personality: Optional[str] = "default"
    dynamic_model: Optional[bool] = None
    selected_model: Optional[str] = None
    custom_prompt: Optional[str] = None

class ChatRenameRequest(BaseModel):
    title: str

class ConnectionConfig(BaseModel):
    api_key: str
    base_url: str
    default_model: Optional[str] = "google/gemma-4-31b-it"

class AppSettings(BaseModel):
    dynamic_model_enabled: bool = True
    active_personality: str = "default"
    default_model: str = "google/gemma-4-31b-it"
    rag_folder: str = "data/documents"
    custom_prompt: str = ""

class RagConfig(BaseModel):
    folder_path: str

class RagStatus(BaseModel):
    folder_path: str
    total_documents: int
    total_chunks: int
    last_indexed: Optional[str] = None
    files: List[str] = []

class ToolInfo(BaseModel):
    name: str
    description: str
    active: bool = True
