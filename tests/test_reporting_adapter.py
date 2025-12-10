from datetime import datetime, timezone
from typing import Any, List

from audience_bot.domain.reporting import ReportPolicy, ReportFormat
from audience_bot.infrastructure.reporting_adapter import ReportingAdapter
from audience_bot.application.usecases.dto import ExtractionResultDTO, ReportDTO, ReportMetadataDTO
from audience_bot.domain.extraction import AudienceProfile, ExtractionResult, ProfileId, ProfileType


class DummyExcelRenderer:
    def __init__(self) -> None:
        self.rendered_reports: List[str] = []

    def render(self, report: "Any") -> bytes:  # type: ignore[override]
        self.rendered_reports.append("excel")
        return b"excel-bytes"


def build_extraction_result(count: int) -> ExtractionResult:
    result = ExtractionResult()
    for idx in range(count):
        profile = AudienceProfile(
            profile_id=ProfileId(user_id=idx, username=f"user{idx}", display_name=f"User {idx}"),
            profile_type=ProfileType.PARTICIPANT,
            username=f"@user{idx}",
            display_name=f"User {idx}",
            first_name=f"User{idx}",
            last_name="Test",
        )
        result.add_participant(profile)
    return result


def test_reporting_adapter_returns_text_when_under_threshold():
    renderer = DummyExcelRenderer()
    policy = ReportPolicy(plain_text_threshold=5)
    adapter = ReportingAdapter(renderer, report_policy=policy)
    extraction = ExtractionResultDTO(result=build_extraction_result(3))
    metadata = ReportMetadataDTO(export_time=datetime.now(timezone.utc), chat_name="Chat")

    report = adapter.build(extraction, metadata)

    assert isinstance(report, ReportDTO)
    assert report.format == ReportFormat.PLAIN_TEXT
    assert report.text is not None
    assert b"excel" not in (report.excel_bytes or b"")


def test_reporting_adapter_returns_excel_when_threshold_reached():
    renderer = DummyExcelRenderer()
    policy = ReportPolicy(plain_text_threshold=1)
    adapter = ReportingAdapter(renderer, report_policy=policy)
    extraction = ExtractionResultDTO(result=build_extraction_result(2))
    metadata = ReportMetadataDTO(export_time=datetime.now(timezone.utc), chat_name="Chat")

    report = adapter.build(extraction, metadata)

    assert report.format == ReportFormat.EXCEL
    assert report.excel_bytes == b"excel-bytes"
    assert renderer.rendered_reports
