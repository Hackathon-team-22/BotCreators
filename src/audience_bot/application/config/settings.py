from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    telegram_bot_token: str | None = None
    telegram_poll_interval: float = 1.0
    telegram_poll_timeout: int = 30
    telegram_base_url: str = "https://api.telegram.org"
    telegram_file_base_url: str = "https://api.telegram.org/file"

    max_files: int = 10
    max_file_size: int = 5 * 1024 * 1024
    session_ttl_seconds: int = 60 * 60
    max_messages: int = 200_000
    max_total_bytes: int = 50 * 1024 * 1024
    max_processing_seconds: int = 15

    report_text_threshold: int = 50
    report_force_excel: bool = False

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        str_strip_whitespace=True,
        validate_default=True,
    )


def load_app_settings(env_file: str = ".env") -> AppSettings:
    return AppSettings(_env_file=env_file)
