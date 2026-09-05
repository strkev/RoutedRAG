from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import retriever, create_retriever_tool
from src.models import get_embeddings

load_dotenv()

embeddings = get_embeddings()

texts = [
    'Apple is a cool company',
    'Apple produces Computers',
    'I believe Apple is innovative',
    'I am a fan of MacBooks',
    'I enjoy Oranges.'
]

vector_store = FAISS.from_texts(texts=texts, embedding=embeddings)

retriever = vector_store.as_retriever(search_kwargs={'k': 3})
retriever_tool = create_retriever_tool(retriever, name="knowledge_search", description="Search the small Product / Fruit knowledgebase for information")