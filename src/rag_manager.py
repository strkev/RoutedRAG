import os
import glob
from datetime import datetime
from typing import List, Dict, Any, Optional
from threading import Lock

from langchain_community.vectorstores import FAISS
from langchain_core.tools import BaseTool
from langchain_core.documents import Document

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.models import get_embeddings, SetupRequiredException
from src.logger import logger

DEFAULT_DOCS_DIR = "data/documents"
DEFAULT_INDEX_DIR = "data/faiss_index"

DEFAULT_TEXTS = [
    "Apple is a technology company headquartered in Cupertino, California.",
    "Apple produces Mac computers, iPhone smartphones, iPad tablets, and watches.",
    "The MacBook M3 is an Apple Silicon computer with high efficiency and unified memory architecture.",
    "Oranges and Apples are both fruits, rich in vitamins and dietary fiber.",
    "LangChain and LangGraph are frameworks for building stateful agentic AI applications with tool calling and routing."
]

class RagManager:
    def __init__(self, folder_path: str = DEFAULT_DOCS_DIR, index_dir: str = DEFAULT_INDEX_DIR):
        self.folder_path = folder_path
        self.index_dir = index_dir
        self.lock = Lock()
        self.vector_store: Optional[FAISS] = None
        self.last_indexed: Optional[str] = None
        self.total_docs: int = 0
        self.total_chunks: int = 0
        self.indexed_files: List[str] = []
        
        os.makedirs(self.folder_path, exist_ok=True)
        os.makedirs(self.index_dir, exist_ok=True)
        
        sample_file = os.path.join(self.folder_path, "apple_products.txt")
        if not os.path.exists(sample_file) and not os.listdir(self.folder_path):
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write("\n\n".join(DEFAULT_TEXTS))

        self.try_load_persisted_index()

    def try_load_persisted_index(self):
        faiss_file = os.path.join(self.index_dir, "index.faiss")
        if os.path.exists(faiss_file):
            try:
                embeddings = get_embeddings()
                self.vector_store = FAISS.load_local(
                    self.index_dir,
                    embeddings,
                    allow_dangerous_deserialization=True
                )
                self.last_indexed = datetime.fromtimestamp(os.path.getmtime(faiss_file)).isoformat()
                logger.info(f"Persistierter FAISS-Index aus {self.index_dir} geladen.")
            except SetupRequiredException:
                logger.info("Keine Provider-Konfiguration fuer Embeddings vorhanden. Index-Laden zurueckgestellt.")
            except Exception as e:
                logger.warning(f"Konnte existierenden FAISS-Index nicht laden: {e}")

    def load_documents_from_folder(self) -> List[Document]:
        docs: List[Document] = []
        if not os.path.exists(self.folder_path):
            return docs

        supported_extensions = ("*.txt", "*.md", "*.markdown", "*.json", "*.csv", "*.py")
        files = []
        for ext in supported_extensions:
            files.extend(glob.glob(os.path.join(self.folder_path, "**", ext), recursive=True))

        self.indexed_files = [os.path.relpath(f, self.folder_path) for f in files]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )

        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    if content:
                        chunks = splitter.split_text(content)
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
                logger.error(f"Fehler beim Einlesen von {filepath}: {e}")

        return docs

    def reindex(self) -> Dict[str, Any]:
        with self.lock:
            try:
                logger.info("Starte Indizierung der Wissensdokumente...")
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

                self.vector_store.save_local(self.index_dir)
                self.last_indexed = datetime.utcnow().isoformat()
                logger.info(f"Indexierung erfolgreich und unter {self.index_dir} gespeichert ({self.total_docs} Dokumente, {self.total_chunks} Chunks).")

                return {
                    "status": "success",
                    "total_documents": self.total_docs,
                    "total_chunks": self.total_chunks,
                    "files": self.indexed_files,
                    "folder_path": self.folder_path,
                    "last_indexed": self.last_indexed
                }
            except SetupRequiredException as se:
                logger.warning(f"Reindexierung nicht moeglich: {se}")
                return {
                    "status": "setup_required",
                    "error": str(se),
                    "folder_path": self.folder_path
                }
            except Exception as e:
                logger.error(f"Fehler waehrend der Indizierung: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "folder_path": self.folder_path
                }

    def search(self, query: str) -> str:
        if self.vector_store is None:
            self.try_load_persisted_index()
            if self.vector_store is None:
                res = self.reindex()
                if res.get("status") != "success":
                    return f"Suche nicht moeglich: {res.get('error', 'Kein Index verfuegbar')}"

        if self.vector_store is not None:
            try:
                results = self.vector_store.similarity_search(query, k=3)
                if results:
                    return "\n\n".join([f"[{d.metadata.get('source', 'Wissen')}]: {d.page_content}" for d in results])
            except Exception as e:
                logger.warning(f"Vektorsuche-Fehler: {e}")

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
