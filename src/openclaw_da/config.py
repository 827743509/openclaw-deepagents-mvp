from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    dashscope_api_key: str | None = Field(default=None, alias="DASHSCOPE_API_KEY")
    dashscope_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="DASHSCOPE_BASE_URL"
    )
    openclaw_model: str = Field(default="openai:gpt-5.4", alias="OPENCLAW_MODEL")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    openclaw_workspace: Path = Field(default=Path("./workspace"), alias="OPENCLAW_WORKSPACE")
    openclaw_data_dir: Path = Field(default=Path("./data"), alias="OPENCLAW_DATA_DIR")

    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")

    openclaw_allow_send: bool = Field(default=False, alias="OPENCLAW_ALLOW_SEND")

    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: str | None = Field(default=None, alias="SMTP_FROM")


def get_settings() -> Settings:
    settings = Settings()
    settings.openclaw_workspace.mkdir(parents=True, exist_ok=True)
    settings.openclaw_data_dir.mkdir(parents=True, exist_ok=True)
    return settings
