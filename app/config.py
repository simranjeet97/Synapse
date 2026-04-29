from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    PROJECT_NAME: str = "Production RAG System"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Infrastructure
    CHROMA_COLLECTION_NAME: str = "production-rag"
    CHROMA_PERSIST_DIRECTORY: str = "chroma_db"
    NUM_SHARDS: int = 16
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI Services
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3-flash-preview" 
    
    # Observability
    OPIK_API_KEY: Optional[str] = None
    OPIK_HOST: str = "http://localhost:8080"
    OPIK_PROJECT_NAME: str = "production-rag"
    
    # RAG Tuning
    PAGERANK_ALPHA: float = 0.3
    COHERE_API_KEY: Optional[str] = None

    # Security
    ALLOWED_HOSTS: list[str] = ["*"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
