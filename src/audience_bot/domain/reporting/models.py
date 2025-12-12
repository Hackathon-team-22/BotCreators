from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from ..extraction import AudienceProfile, ExtractionResult


class ReportFormat(str, Enum):
    PLAIN_TEXT = "plain_text"
    EXCEL = "excel"


@dataclass(frozen=True)
class ReportMetadata:
    exported_at: datetime
    chat_name: Optional[str]
    participant_count: int


@dataclass
class TextList:
    lines: List[str]


@dataclass
class SheetModel:
    name: str
    columns: List[str]
    rows: List[Dict[str, str]]


@dataclass
class ExcelReport:
    sheets: List[SheetModel]


@dataclass
class AudienceReport:
    report_format: Optional[ReportFormat] = None
    metadata: Optional[ReportMetadata] = None
    text_list: Optional[TextList] = None
    excel_report: Optional[ExcelReport] = None

    def set_text(self, metadata: ReportMetadata, text_list: TextList) -> None:
        self.report_format = ReportFormat.PLAIN_TEXT
        self.metadata = metadata
        self.text_list = text_list
        self.excel_report = None

    def set_excel(self, metadata: ReportMetadata, excel_report: ExcelReport) -> None:
        self.report_format = ReportFormat.EXCEL
        self.metadata = metadata
        self.excel_report = excel_report
        self.text_list = None

    def finalize(self) -> None:
        if not self.report_format or not self.metadata:
            raise ValueError("Report is incomplete.")
        if self.report_format == ReportFormat.PLAIN_TEXT and not self.text_list:
            raise ValueError("Text list missing for plain-text report.")
        if self.report_format == ReportFormat.EXCEL and not self.excel_report:
            raise ValueError("Excel document missing for excel report.")


class ReportPolicy:
    def __init__(self, plain_text_threshold: int = 50) -> None:
        self._plain_text_threshold = plain_text_threshold

    def choose(self, result: ExtractionResult) -> ReportFormat:
        if result.participant_count() <= self._plain_text_threshold:
            return ReportFormat.PLAIN_TEXT
        return ReportFormat.EXCEL


class TextListBuilder:
    @staticmethod
    def build(result: ExtractionResult) -> TextList:
        lines = []
        for profile in sorted(
            result.participants.values(),
            key=lambda profile: (profile.username or "", profile.display_name or ""),
        ):
            username = f" ({profile.username})" if profile.username else ""
            display = profile.display_name or ""
            lines.append(f"{display}{username}")
        return TextList(lines=lines)


class ExcelReportBuilder:
    COLUMN_HEADERS = [
        "Дата экспорта",
        "Username",
        "Отображаемое имя",
        "Имя",
        "Фамилия",
        "Описание",
        "Дата регистрации",
        "Наличие канала",
    ]

    SHEET_ORDER = [
        ("participants", "Участники"),
        ("mentioned_only", "Упомянутые"),
        ("channels", "Каналы"),
    ]

    def build(self, result: ExtractionResult, metadata: ReportMetadata) -> ExcelReport:
        sheets = []
        for key, title in self.SHEET_ORDER:
            rows = self._build_rows(getattr(result, key).values(), metadata)
            sheets.append(SheetModel(name=title, columns=self.COLUMN_HEADERS, rows=rows))
        return ExcelReport(sheets=sheets)

    def _build_rows(
        self, profiles: List[AudienceProfile], metadata: ReportMetadata
    ) -> List[Dict[str, str]]:
        rows = []
        for profile in sorted(profiles, key=lambda profile: (profile.username or "", profile.display_name or "")):
            rows.append(
                {
                    "Дата экспорта": metadata.exported_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Username": profile.username or "",
                    "Отображаемое имя": profile.display_name or "",
                    "Имя": profile.first_name or "",
                    "Фамилия": profile.last_name or "",
                    "Описание": profile.description or "",
                    "Дата регистрации": profile.registered_at or "",
                    "Наличие канала": "да" if profile.has_channel else "",
                }
            )
        return rows
