"""Dream OS - 配置管理"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 项目
    project_name: str = "Dream OS"
    version: str = "1.0.0"
    debug: bool = False

    # 数据库
    database_url: str = "postgresql+asyncpg://dream:dream123@postgres:5432/dreamos"
    database_url_sync: str = "postgresql+psycopg2://dream:dream123@postgres:5432/dreamos"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # AI Provider
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 1024

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: list[str] = ["*"]

    # 日志
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
