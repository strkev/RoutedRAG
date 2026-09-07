from src.rag_manager import rag_manager
from src.tools.knowledge import knowledge_search_tool

retriever_tool = knowledge_search_tool
vector_store = rag_manager.vector_store
