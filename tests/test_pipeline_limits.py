import pytest

from audience_bot.application.usecases.dto import ParsedMessagesDTO, ReportMetadataDTO, ExtractionResultDTO, RawFileDTO
from audience_bot.application.usecases.pipeline import RunFullPipelineUC, ParseChatExportUC, ExtractAudienceUC, BuildAudienceReportUC
from audience_bot.application.config._impl import PipelineConfig
from audience_bot.application.usecases.exceptions import PipelineError


class DummyParser:
    def __init__(self, messages_count: int):
        self.messages_count = messages_count

    def parse(self, files):
        return ParsedMessagesDTO(messages=[object()] * self.messages_count)


class DummyExtractor:
    def extract(self, parsed: ParsedMessagesDTO):
        return ExtractionResultDTO(result=object())


class DummyReporter:
    def build(self, extraction: ExtractionResultDTO, metadata: ReportMetadataDTO):
        return object()


@pytest.mark.slow
def test_pipeline_hits_message_limit():
    config = PipelineConfig(max_messages=1000, max_total_bytes=10 * 1024 * 1024, max_processing_seconds=5)
    uc = RunFullPipelineUC(
        parser_uci=ParseChatExportUC(DummyParser(messages_count=5000)),
        extractor_uc=ExtractAudienceUC(DummyExtractor()),
        reporting_uc=BuildAudienceReportUC(DummyReporter()),
        config=config,
    )
    with pytest.raises(PipelineError):
        uc.execute([RawFileDTO(path="<stub>", filename="stub", content=b"stub")], chat_name=None, user_id="u")
