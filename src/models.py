import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

load_dotenv()

def get_llm(model_name: str = "gemma-4-31b-it", temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=model_name,
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        temperature=temperature,
    )

def get_embeddings(model_name: str = "mxbai-embed-large:latest") -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=model_name,
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        check_embedding_ctx_length=False
    )