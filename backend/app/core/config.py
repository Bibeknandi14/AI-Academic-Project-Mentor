import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Guided Project Progress Tracking Platform"
    API_V1_STR: str = "/api"
    
    # Secrets & Security
    SECRET_KEY: str = "supersecretjwtkey_change_in_production_32bytes_min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./platform.db"
    
    # LLM Settings
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini" # gemini, openai, mock
    
    # GitHub API
    GITHUB_TOKEN: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = {"env_file": [".env", "../.env", "backend/.env"], "extra": "ignore"}

settings = Settings()
