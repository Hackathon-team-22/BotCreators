from __future__ import annotations

from dataclasses import dataclass

from .settings import AppSettings


@dataclass(frozen=True)
class PipelineConfig:
    max_files: int = 10
    max_file_size: int = 5 * 1024 * 1024
    session_ttl_seconds: int = 60 * 60
    report_text_threshold: int = 50
    max_messages: int = 200_000
    report_force_excel: bool = False
    max_total_bytes: int = 50 * 1024 * 1024
    max_processing_seconds: int = 15

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "PipelineConfig":
        return cls(
            max_files=settings.max_files,
            max_file_size=settings.max_file_size,
            session_ttl_seconds=settings.session_ttl_seconds,
            report_text_threshold=settings.report_text_threshold,
            max_messages=settings.max_messages,
            report_force_excel=settings.report_force_excel,
            max_total_bytes=settings.max_total_bytes,
            max_processing_seconds=settings.max_processing_seconds,
        )


@dataclass(frozen=True)
class TelegramConfig:
    token: str
    poll_interval: float
    poll_timeout: int
    base_url: str
    file_base_url: str

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "TelegramConfig":
        if not settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в окружении.")
        return cls(
            token=settings.telegram_bot_token,
            poll_interval=settings.telegram_poll_interval,
            poll_timeout=settings.telegram_poll_timeout,
            base_url=settings.telegram_base_url,
            file_base_url=settings.telegram_file_base_url,
        )
