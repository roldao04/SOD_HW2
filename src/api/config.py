"""
Configuration management for the NLP Chatbot API.
Loads settings from environment variables with defaults.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_TITLE: str = "E-Procurement Chatbot API"
    API_VERSION: str = "1.0.0"

    # Dremio Connection
    DREMIO_HOST: str = "localhost"
    DREMIO_PORT: int = 32010  # Arrow Flight port
    DREMIO_USERNAME: str = "admin"
    DREMIO_PASSWORD: str = "password123"
    DREMIO_TLS: bool = False
    DREMIO_TIMEOUT: int = 30  # seconds

    # LLM Configuration - Gemini API for both bots
    GEMINI_API_KEY: Optional[str] = None

    # Query Creator Bot (Gemini) - Fast model for SQL generation
    QUERY_CREATOR_MODEL: str = "models/gemini-2.0-flash"
    QUERY_CREATOR_TEMPERATURE: float = 0.1  # Low temperature for deterministic SQL
    QUERY_CREATOR_MAX_TOKENS: int = 1024

    # Analytics Bot (Gemini) - Advanced model for complex analysis
    ANALYTICS_MODEL: str = "models/gemini-2.5-pro"
    ANALYTICS_TEMPERATURE: float = 0.7
    ANALYTICS_MAX_TOKENS: int = 4096  # Increased for complete analysis

    # Query Execution Limits
    MAX_QUERY_TIMEOUT: int = 30  # seconds
    MAX_RESULT_ROWS: int = 10000
    MAX_JOINS: int = 5
    MAX_SUBQUERY_DEPTH: int = 3

    # Schema Cache
    SCHEMA_CACHE_TTL: int = 3600  # 1 hour in seconds

    # CORS Settings
    CORS_ORIGINS: list = [
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra env vars (shared .env with other services)


# Singleton instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings
