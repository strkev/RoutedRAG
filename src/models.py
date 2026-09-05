import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def get_llm(model_name: str = "gemma-4-31b-it", temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=model_name,
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL"),
        temperature=temperature,
    )