from __future__ import annotations

from datetime import datetime, timezone
import time
import logging
from typing import List, Optional

from .dto import (
    ExtractionResultDTO,
    ParsedMessagesDTO,
    RawFileDTO,
    ReportDTO,
    ReportMetadataDTO,
)
from .exceptions import InvalidInputError, PipelineError
from .ports import IExtractor, IParser, IReportBuilder


class ParseChatExportUC:
    def __init__(self, parser: IParser):
        self._parser = parser

    def execute(self, files: List[RawFileDTO], chat_id: Optional[str], user_id: str) -> ParsedMessagesDTO:
        if not files:
            raise InvalidInputError("Список файлов пуст.")
        return self._parser.parse(files)


class ExtractAudienceUC:
    def __init__(self, extractor: IExtractor):
        self._extractor = extractor

    def execute(self, parsed: ParsedMessagesDTO) -> ExtractionResultDTO:
        if not parsed.messages:
            raise InvalidInputError("Нет сообщений для извлечения.")
        return self._extractor.extract(parsed)


class BuildAudienceReportUC:
    def __init__(self, report_builder: IReportBuilder):
        self._report_builder = report_builder

    def execute(
        self, extraction: ExtractionResultDTO, metadata: ReportMetadataDTO
    ) -> ReportDTO:
        return self._report_builder.build(extraction, metadata)


class RunFullPipelineUC:
    def __init__(
        self,
        parser_uci: ParseChatExportUC,
        extractor_uc: ExtractAudienceUC,
        reporting_uc: BuildAudienceReportUC,
        config: "PipelineConfig",
    ):
        self._parse = parser_uci
        self._extract = extractor_uc
        self._report = reporting_uc
        self._config = config

    def execute(
        self,
        files: List[RawFileDTO],
        chat_name: Optional[str],
        user_id: str,
    ) -> ReportDTO:
        try:
            start = time.time()
            total_bytes = sum(len(f.content or b"") for f in files)
            if total_bytes > self._config.max_total_bytes:
                raise PipelineError(
                    f"Превышен лимит объёма входных данных ({total_bytes} > {self._config.max_total_bytes} байт)."
                )
            parsed = self._parse.execute(files, chat_name, user_id)
            if len(parsed.messages) > self._config.max_messages:
                raise PipelineError(f"Превышен лимит сообщений ({len(parsed.messages)} > {self._config.max_messages}).")
            logger.info(
                "parsed_export",
                extra={"user_id": user_id, "message_count": len(parsed.messages)},
            )
            extracted = self._extract.execute(parsed)
            metadata = ReportMetadataDTO(export_time=datetime.now(timezone.utc), chat_name=chat_name)
            result = self._report.execute(extracted, metadata)
            elapsed = time.time() - start
            if elapsed > self._config.max_processing_seconds:
                raise PipelineError(
                    f"Превышен лимит времени обработки ({elapsed:.1f}s > {self._config.max_processing_seconds}s)."
                )
            logger.info(
                "pipeline_metrics",
                extra={
                    "total_bytes": total_bytes,
                    "message_count": len(parsed.messages),
                    "elapsed_seconds": round(elapsed, 3),
                },
            )
            return result
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError("Ошибка выполнения пайплайна.") from exc
logger = logging.getLogger(__name__)
