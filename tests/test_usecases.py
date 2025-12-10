from datetime import datetime, timezone
from typing import List

import pytest

from audience_bot.application.usecases.dto import (
    ParsedMessagesDTO,
    RawFileDTO,
    ExtractionResultDTO,
    ReportDTO,
    ReportMetadataDTO,
)
from audience_bot.application.usecases.exceptions import InvalidInputError
from audience_bot.application.usecases.pipeline import (
    ParseChatExportUC,
    ExtractAudienceUC,
    BuildAudienceReportUC,
)
from audience_bot.domain.reporting import ReportFormat


class DummyParser:
    def __init__(self, messages: ParsedMessagesDTO):
        self.messages = messages
        self.calls: List[List[RawFileDTO]] = []

    def parse(self, files: List[RawFileDTO]) -> ParsedMessagesDTO:
        self.calls.append(files)
        return self.messages


class DummyExtractor:
    def __init__(self, result: ExtractionResultDTO):
        self.result = result
        self.calls: List[ParsedMessagesDTO] = []

    def extract(self, parsed: ParsedMessagesDTO) -> ExtractionResultDTO:
        self.calls.append(parsed)
        return self.result


class DummyReporter:
    def __init__(self, report: ReportDTO):
        self.report = report
        self.calls: List[tuple[ExtractionResultDTO, ReportMetadataDTO]] = []

    def build(self, extraction: ExtractionResultDTO, metadata: ReportMetadataDTO) -> ReportDTO:
        self.calls.append((extraction, metadata))
        return self.report


def test_parse_chat_export_uc_validates_files():
    uc = ParseChatExportUC(parser=DummyParser(messages=ParsedMessagesDTO(messages=[])))
    with pytest.raises(InvalidInputError):
        uc.execute([], chat_id=None, user_id="u1")


def test_parse_chat_export_uc_calls_parser():
    dummy_messages = ParsedMessagesDTO(messages=[object()])
    parser = DummyParser(messages=dummy_messages)
    uc = ParseChatExportUC(parser=parser)
    files = [RawFileDTO(path="<stub>", filename="stub", content=b"123")]

    result = uc.execute(files, chat_id=None, user_id="u1")

    assert result is dummy_messages
    assert parser.calls == [files]


def test_extract_audience_uc_validates_messages():
    extractor_uc = ExtractAudienceUC(extractor=DummyExtractor(result=ExtractionResultDTO(result=object())))
    with pytest.raises(InvalidInputError):
        extractor_uc.execute(ParsedMessagesDTO(messages=[]))


def test_extract_audience_uc_calls_extractor():
    dummy_result = ExtractionResultDTO(result=object())
    extractor = DummyExtractor(result=dummy_result)
    uc = ExtractAudienceUC(extractor=extractor)
    parsed = ParsedMessagesDTO(messages=[object()])

    result = uc.execute(parsed)

    assert result is dummy_result
    assert extractor.calls == [parsed]


def test_build_audience_report_uc_passes_metadata():
    expected_report = ReportDTO(format=ReportFormat.PLAIN_TEXT, text="demo")
    reporter = DummyReporter(report=expected_report)
    uc = BuildAudienceReportUC(report_builder=reporter)
    extraction = ExtractionResultDTO(result=object())
    metadata = ReportMetadataDTO(export_time=datetime.now(timezone.utc), chat_name="demo")

    result = uc.execute(extraction, metadata)

    assert result is expected_report
    assert reporter.calls == [(extraction, metadata)]
