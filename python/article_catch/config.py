"""Environment settings. No secrets in code; load from env / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    feishu_app_id: str = Field(default="", alias="FEISHU_APP_ID")
    feishu_app_secret: str = Field(default="", alias="FEISHU_APP_SECRET")

    # N8N environment constants (not business target tables)
    feishu_config_base: str = Field(
        default="",
        alias="FEISHU_CONFIG_BASE",
    )
    feishu_list_table: str = Field(default="", alias="FEISHU_LIST_TABLE")
    feishu_config_table: str = Field(default="", alias="FEISHU_CONFIG_TABLE")

    wechat2rss_base: str = Field(default="http://127.0.0.1:8080", alias="WECHAT2RSS_BASE")
    wechat2rss_token: str = Field(default="", alias="WECHAT2RSS_TOKEN")

    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.deepseek.com", alias="LLM_BASE_URL")
    llm_default_model: str = Field(default="", alias="LLM_DEFAULT_MODEL")

    jizhile_base_url: str = Field(default="", alias="JIZHILE_BASE_URL")
    jizhile_token: str = Field(default="", alias="JIZHILE_TOKEN")

    sqlite_path: str = Field(default="./data/article_catch.db", alias="SQLITE_PATH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
