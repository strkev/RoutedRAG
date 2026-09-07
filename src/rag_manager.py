import os
import glob
from datetime import datetime
from typing import List, Dict, Any, Optional
from threading import Lock

from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool, BaseTool
from langchain_core.documents import Document
from src.models import get_embeddings

DEFAULT_DOCS_DIR = "data/documents"

DEFAULT_TEXTS = [
    "Apple is a technology company headquartered in Cupertino, California.",
    "Apple produces Mac computers, iPhone smartphones, iPad tablets, and watches.",
    "The MacBook M3 is an Apple Silicon computer with high efficiency and unified memory architecture.",
    "Oranges and Apples are both fruits, rich in vitamins and dietary fiber.",
    "LangChain and LangGraph are frameworks for building stateful agentic AI applications with tool calling and routing."
]

class RagManager:
    def __init__(self, folder_path: str = DEFAULT_DOCS_DIR):
        self.folder_path = folder_path
        self.lock = Lock()
        self.vector_store: Optional[FAISS] = None
        self.last_indexed: Optional[str] = None
        self.total_docs: int = 0
        self.total_chunks: int = 0
        self.indexed_files: List[str] = []
        
        os.makedirs(self.folder_path, exist_ok=True)
        sample_file = os.path.join(self.folder_path, "apple_products.txt")
        if not os.path.exists(sample_file) and not os.listdir(self.folder_path):
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write("\n\n".join(DEFAULT_TEXTS))

    def load_documents_from_folder(self) -> List[Document]:
        docs: List[Document] = []
        if not os.path.exists(self.folder_path):
            return docs

        supported_extensions = ("*.txt", "*.md", "*.markdown", "*.json", "*.csv", "*.py")
        files = []
        for ext in supported_extensions:
            files.extend(glob.glob(os.path.join(self.folder_path, "**", ext), recursive=True))

        self.indexed_files = [os.path.relpath(f, self.folder_path) for f in files]

        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    if content:
                        chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 5]
                        if not chunks:
                            chunks = [content]
                        for i, chunk in enumerate(chunks):
                            docs.append(Document(
                                page_content=chunk,
                                metadata={
                                    "source": os.path.basename(filepath),
                                    "chunk": i,
                                    "path": filepath
                                }
                            ))
            except Exception as e:
                print(f"[RAG] Error reading file {filepath}: {e}")

        return docs

    def reindex(self) -> Dict[str, Any]:
        with self.lock:
            try:
                print("[RAG] Starte Indexierung der Wissensdokumente...")
                embeddings = get_embeddings()
                docs = self.load_documents_from_folder()

                if not docs:
                    self.vector_store = FAISS.from_texts(texts=DEFAULT_TEXTS, embedding=embeddings)
                    self.total_docs = len(DEFAULT_TEXTS)
                    self.total_chunks = len(DEFAULT_TEXTS)
                    self.indexed_files = ["default_in_memory_knowledge"]
                else:
                    self.vector_store = FAISS.from_documents(documents=docs, embedding=embeddings)
                    self.total_docs = len(set(d.metadata.get("source", "") for d in docs))
                    self.total_chunks = len(docs)

                self.last_indexed = datetime.utcnow().isoformat()
                print(f"[RAG] Indexierung erfolgreich: {self.total_docs} Dokumente, {self.total_chunks} Chunks.")

                return {
                    "status": "success",
                    "total_documents": self.total_docs,
                    "total_chunks": self.total_chunks,
                    "files": self.indexed_files,
                    "folder_path": self.folder_path,
                    "last_indexed": self.last_indexed
                }
            except Exception as e:
                print(f"[RAG] Fehler während der Indexierung: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "folder_path": self.folder_path
                }

    def search(self, query: str) -> str:
        if self.vector_store is None:
            self.reindex()

        if self.vector_store is not None:
            try:
                results = self.vector_store.similarity_search(query, k=3)
                if results:
                    return "\n\n".join([f"[{d.metadata.get('source', 'Wissen')}]: {d.page_content}" for d in results])
            except Exception as e:
                print(f"[RAG] Vector search error: {e}")

        docs = self.load_documents_from_folder()
        q_lower = query.lower()
        matched = [d.page_content for d in docs if any(word in d.page_content.lower() for word in q_lower.split())]
        if matched:
            return "\n\n".join(matched[:3])
        return "Keine spezifischen Dokumente in der Wissensdatenbank gefunden."

    def get_tool(self) -> BaseTool:
        from src.tools.knowledge import knowledge_search_tool
        return knowledge_search_tool

    def set_folder_path(self, new_path: str) -> Dict[str, Any]:
        abs_path = os.path.abspath(new_path)
        os.makedirs(abs_path, exist_ok=True)
        self.folder_path = abs_path
        return self.reindex()

    def get_status(self) -> Dict[str, Any]:
        if not self.indexed_files:
            docs = self.load_documents_from_folder()
            self.total_docs = len(set(d.metadata.get("source", "") for d in docs))
            self.total_chunks = len(docs)
            
        return {
            "folder_path": os.path.abspath(self.folder_path),
            "total_documents": self.total_docs,
            "total_chunks": self.total_chunks,
            "last_indexed": self.last_indexed,
            "files": self.indexed_files
        }

rag_manager = RagManager()

def __getattr__(name: str):
    if name == "knowledge_search_tool":
        from src.tools.knowledge import knowledge_search_tool
        return knowledge_search_tool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
