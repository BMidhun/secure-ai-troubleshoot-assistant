# backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    AI_PROVIDER: Literal["nvidia", "azure"] = "nvidia"
    
    # NVIDIA Build Credentials
    NVIDIA_API_KEY: str = "nvapi-..."
    NVIDIA_LLM_MODEL: str = "meta/llama-3.1-70b-instruct"
    NVIDIA_EMBED_MODEL: str = "nvidia/nv-embedqa-e5-v5"
    NVIDIA_RERANK_MODEL: str = "nvidia/nv-rerankqa-mistral-4b-v3"
    
    # Azure Target Credentials (for future migration)
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"
    AZURE_CHAT_DEPLOYMENT: str = "gpt-4o"
    AZURE_EMBED_DEPLOYMENT: str = "text-embedding-3-large"
    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_KEY: str = ""

    VECTOR_DB_PATH: str = "./chroma_db"

    class Config:
        env_file = ".env"

settings = Settings()