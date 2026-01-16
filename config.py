"""
Configuration management for HPPS system.
Supports environment-based configuration for dev/staging/prod.
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Application configuration."""
    
    # Base settings
    PROJECT_NAME: str = "HPPS System"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./hpps.db"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "False").lower() == "true"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    
    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    
    # File paths
    BASE_DIR: Path = Path(__file__).parent.resolve()
    REPO_STORAGE_PATH: Path = Path(os.getenv(
        "REPO_STORAGE_PATH",
        str(BASE_DIR / "repositories")
    ))
    LOG_DIR: Path = Path(os.getenv(
        "LOG_DIR",
        str(BASE_DIR / "logs")
    ))
    
    # Celery configuration
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    
    # API configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "True").lower() == "true"
    
    # CORS configuration
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8000"
    ).split(",")
    
    # Analysis configuration
    ANALYSIS_TIMEOUT: int = int(os.getenv("ANALYSIS_TIMEOUT", "600"))  # 10 minutes
    MAX_REPO_SIZE_MB: int = int(os.getenv("MAX_REPO_SIZE_MB", "500"))
    CLEANUP_OLD_REPOS_DAYS: int = int(os.getenv("CLEANUP_OLD_REPOS_DAYS", "30"))
    
    # Job matching configuration
    MIN_MATCH_THRESHOLD: float = float(os.getenv("MIN_MATCH_THRESHOLD", "0.75"))
    MAX_KEYWORDS: int = int(os.getenv("MAX_KEYWORDS", "25"))
    MAX_MANDATORY_KEYWORDS: int = int(os.getenv("MAX_MANDATORY_KEYWORDS", "10"))
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "hpps.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.REPO_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production."""
        return not cls.DEBUG and "postgres" in cls.DATABASE_URL.lower()
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL, converting SQLite path if needed."""
        if cls.DATABASE_URL.startswith("sqlite"):
            # Ensure SQLite directory exists
            db_path = Path(cls.DATABASE_URL.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        return cls.DATABASE_URL


# Ensure directories exist on import
Config.ensure_directories()
