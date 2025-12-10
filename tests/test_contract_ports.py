import pytest

from datetime import datetime, timezone

from audience_bot.application.usecases.dto import ParsedMessagesDTO, ExtractionResultDTO, ReportMetadataDTO
from audience_bot.application.usecases.exceptions import InvalidInputError
from audience_bot.application.usecases.pipeline import (
    ParseChatExportUC,
    ExtractAudienceUC,
    BuildAudienceReportUC,
)
from audience_bot.domain.reporting import ReportFormat
from audience_bot.domain.extraction import ExtractionResult


class DummyExcelReport:
    pass


def test_parser_contract_must_return_parsed_messages():
    class GoodParser:
        def parse(self, files):
            return ParsedMessagesDTO(messages=[object()])

    uc = ParseChatExportUC(parser=GoodParser())
    parsed = uc.execute([object()], chat_id=None, user_id="u")
    assert isinstance(parsed, ParsedMessagesDTO)


def test_parser_contract_invalid_returns_error():
    class BadParser:
        def parse(self, files):
            return ParsedMessagesDTO(messages=[])

    uc = ParseChatExportUC(parser=BadParser())
    with pytest.raises(InvalidInputError):
        uc.execute([], chat_id=None, user_id="u")


def test_extractor_contract_returns_result():
    class GoodExtractor:
        def extract(self, parsed):
            return ExtractionResultDTO(result=object())

    uc = ExtractAudienceUC(extractor=GoodExtractor())
    result = uc.execute(ParsedMessagesDTO(messages=[object()]))
    assert isinstance(result, ExtractionResultDTO)


def test_report_builder_contract_generates_dto():
    class GoodExcelRenderer:
        def render(self, report):
            return b"excel"

    from audience_bot.infrastructure.reporting_adapter import ReportingAdapter
    from audience_bot.domain.reporting import ReportPolicy

    adapter = ReportingAdapter(renderer=GoodExcelRenderer(), report_policy=ReportPolicy())
    uc = BuildAudienceReportUC(report_builder=adapter)
    extraction = ExtractionResultDTO(result=ExtractionResult())
    metadata = ReportMetadataDTO(export_time=datetime.now(timezone.utc), chat_name=None)
    report = uc.execute(extraction, metadata)
    assert report.format in (ReportFormat.PLAIN_TEXT, ReportFormat.EXCEL)
