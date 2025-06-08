from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable loading."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Mistral AI Configuration
    mistral_api_key: Optional[str] = None
    
    # France Travail API
    france_travail_client_id: str
    france_travail_client_secret: str
    france_travail_api_base_url: str = "https://api.francetravail.io/partenaire"
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "france-travail-gpt"
    
    # App Configuration
    app_env: Literal["development", "production"] = "development"
    app_debug: bool = True
    vector_store_type: Literal["chromadb", "faiss"] = "chromadb"
    vector_store_path: Path = Path("./data/vector_store")
    
    # Model Configuration
    model_provider: Literal["openai", "mistral"] = "openai"
    model_name: str = "gpt-4o"
    model_temperature: float = 0.7
    
    # API Tokens Cache
    france_travail_token_cache_ttl: int = 1200  # 20 minutes
    
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


# Singleton instance
settings = Settings()
