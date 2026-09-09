import os
import importlib
from typing import Dict, List, Any, Callable
from langchain_core.tools import BaseTool

from src.logger import logger

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._active_status: Dict[str, bool] = {}
        self.auto_discover()
    
    def register(self, tool_item: BaseTool | Callable, name: str | None = None, active: bool = True):
        tool_name = name or getattr(tool_item, "name", getattr(tool_item, "__name__", "unknown_tool"))
        self._tools[tool_name] = tool_item
        if tool_name not in self._active_status:
            self._active_status[tool_name] = active

    def auto_discover(self):
        tools_dir = os.path.dirname(__file__)
        if not os.path.exists(tools_dir):
            return

        for filename in sorted(os.listdir(tools_dir)):
            if filename.endswith(".py") and filename not in ("__init__.py", "registry.py"):
                module_name = f"src.tools.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, BaseTool):
                            self.register(attr, active=True)
                except Exception as e:
                    logger.error(f"Fehler beim Laden von {module_name}: {e}")

    def get_all_tools(self) -> List[BaseTool]:
        active_tools = []
        for name, tool_obj in self._tools.items():
            if self._active_status.get(name, True):
                active_tools.append(tool_obj)
        return active_tools

    def list_metadata(self) -> List[Dict[str, Any]]:
        result = []
        for name, tool_obj in self._tools.items():
            desc = getattr(tool_obj, "description", "") or (tool_obj.__doc__ or "")
            result.append({
                "name": name,
                "description": desc.strip(),
                "active": self._active_status.get(name, True)
            })
        return result

registry = ToolRegistry()
