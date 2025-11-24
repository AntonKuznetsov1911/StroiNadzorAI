"""
Централизованная конфигурация приложения
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения"""

    # Основные настройки
    APP_NAME: str = "StroiNadzorAI"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_URL")
    TELEGRAM_WEBHOOK_PATH: str = Field(default="/webhook/telegram", env="TELEGRAM_WEBHOOK_PATH")
    USE_WEBHOOK: bool = Field(default=False, env="USE_WEBHOOK")

    # Anthropic Claude
    ANTHROPIC_API_KEY: str = Field(..., env="ANTHROPIC_API_KEY")
    CLAUDE_MODEL: str = Field(default="claude-sonnet-4-5-20250929", env="CLAUDE_MODEL")
    CLAUDE_MAX_TOKENS: int = Field(default=4000, env="CLAUDE_MAX_TOKENS")

    # Backwards compatibility (will use ANTHROPIC_API_KEY if OPENAI_API_KEY not set)
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://stroinadzor:stroinadzor@localhost:5432/stroinadzor",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")

    # Redis Cache
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_CACHE_TTL: int = Field(default=3600, env="REDIS_CACHE_TTL")  # 1 час

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=50, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(default=3600, env="RATE_LIMIT_PERIOD")  # 1 час
    RATE_LIMIT_PREMIUM_REQUESTS: int = Field(default=200, env="RATE_LIMIT_PREMIUM_REQUESTS")

    # File Storage
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(default=20 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 20MB

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="./logs/app.log", env="LOG_FILE")
    LOG_ROTATION: str = Field(default="500 MB", env="LOG_ROTATION")
    LOG_RETENTION: str = Field(default="30 days", env="LOG_RETENTION")

    # Sentry (опционально)
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")

    # Email Notifications
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_FROM: Optional[str] = Field(default=None, env="SMTP_FROM")

    # Google Drive Integration
    GOOGLE_DRIVE_CREDENTIALS: Optional[str] = Field(default=None, env="GOOGLE_DRIVE_CREDENTIALS")

    # Jira Integration
    JIRA_URL: Optional[str] = Field(default=None, env="JIRA_URL")
    JIRA_EMAIL: Optional[str] = Field(default=None, env="JIRA_EMAIL")
    JIRA_API_TOKEN: Optional[str] = Field(default=None, env="JIRA_API_TOKEN")

    # Features Flags
    ENABLE_VOICE_MESSAGES: bool = Field(default=True, env="ENABLE_VOICE_MESSAGES")
    ENABLE_PDF_REPORTS: bool = Field(default=True, env="ENABLE_PDF_REPORTS")
    ENABLE_OCR: bool = Field(default=True, env="ENABLE_OCR")
    ENABLE_GEOLOCATION: bool = Field(default=True, env="ENABLE_GEOLOCATION")
    ENABLE_STREAMING: bool = Field(default=True, env="ENABLE_STREAMING")

    # Monitoring
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()
