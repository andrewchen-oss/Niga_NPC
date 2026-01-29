"""
[INPUT]: 依赖 pydantic_settings 的 BaseSettings
[OUTPUT]: 对外提供 Settings 配置类、get_settings 工厂函数
[POS]: app 的全局配置中心，被所有模块消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ---- Twitter API ----
    twitter_api_key: str
    twitter_api_secret: str
    twitter_access_token: str
    twitter_access_token_secret: str
    twitter_bearer_token: str
    twitter_bot_user_id: str
    twitter_bot_username: str

    # ---- 上游 API ----
    upstream_api_base_url: str = "https://wtf.nuwa.world/api/v1"
    upstream_api_key: str

    # ---- OpenAI ----
    openai_api_key: str

    # ---- Database ----
    database_url: str

    # ---- Bot 配置 ----
    max_concurrent_processing: int = 10

    # ---- Active Roast 配置 ----
    active_roast_enabled: bool = True
    active_roast_interval: int = 600       # 基础间隔秒数 (10分钟)
    active_roast_jitter: int = 60          # 随机抖动 ±秒

    # ---- CORS ----
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://niganpc.nuwa.world",
        "https://niganpc.nuwa.world",
    ]

    # ---- X OAuth 2.0 ----
    x_client_id: str = ""
    x_client_secret: str = ""
    x_callback_url: str = "http://localhost:8000/api/v1/auth/callback"
    frontend_url: str = "http://localhost:5173"
    jwt_secret: str = "change-me-in-production"

    # ---- 日志 ----
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
