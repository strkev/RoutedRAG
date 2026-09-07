from langchain_core.tools import tool
from src.rag_manager import rag_manager

@tool("knowledge_search", description="Search the local RAG knowledge base for information about loaded documents, products, and notes.", return_direct=False)
def knowledge_search_tool(query: str) -> str:
    return rag_manager.search(query)
