from __future__ import annotations

from dependency_injector import containers, providers

from ..domain.reporting import ReportPolicy
from ..infrastructure.excel_renderer import ExcelRendererAdapter
from ..infrastructure.extraction_adapter import ExtractionAdapter
from ..infrastructure.parsers import ParserAdapter
from ..infrastructure.reporting_adapter import ReportingAdapter
from ..infrastructure.temp_storage import InMemoryTempStorageAdapter
from .config import PipelineConfig, TelegramConfig
from .services.conversation import ConversationService
from .services.sessions import InMemorySessionStore
from .usecases.pipeline import (
    BuildAudienceReportUC,
    ExtractAudienceUC,
    ParseChatExportUC,
    RunFullPipelineUC,
)
from .config.settings import load_app_settings


class AppContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    config.env_file.from_value(".env")

    settings = providers.Singleton(load_app_settings, env_file=config.env_file)

    pipeline_config = providers.Singleton(PipelineConfig.from_settings, settings)

    report_policy = providers.Singleton(
        lambda settings: ReportPolicy(plain_text_threshold=settings.report_text_threshold),
        settings,
    )

    parser_adapter = providers.Singleton(ParserAdapter)
    extractor_adapter = providers.Singleton(ExtractionAdapter)
    excel_renderer = providers.Singleton(ExcelRendererAdapter)
    reporting_adapter = providers.Singleton(
        ReportingAdapter,
        renderer=excel_renderer,
        report_policy=report_policy,
        force_excel=pipeline_config.provided.report_force_excel,
    )

    parse_uc = providers.Singleton(ParseChatExportUC, parser=parser_adapter)
    extract_uc = providers.Singleton(ExtractAudienceUC, extractor=extractor_adapter)
    report_uc = providers.Singleton(BuildAudienceReportUC, report_builder=reporting_adapter)

    pipeline = providers.Singleton(
        RunFullPipelineUC,
        parser_uci=parse_uc,
        extractor_uc=extract_uc,
        reporting_uc=report_uc,
        config=pipeline_config,
    )

    session_store = providers.Singleton(InMemorySessionStore)
    temp_storage = providers.Singleton(InMemoryTempStorageAdapter)

    conversation_service = providers.Factory(
        ConversationService,
        session_store=session_store,
        pipeline=pipeline,
        temp_storage=temp_storage,
        config=pipeline_config,
    )

    telegram_config = providers.Singleton(TelegramConfig.from_settings, settings)
