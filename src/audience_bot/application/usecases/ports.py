from __future__ import annotations

from typing import List, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.reporting import ExcelReport

from .dto import (
    ExtractionResultDTO,
    ParsedMessagesDTO,
    RawFileDTO,
    ReportDTO,
    ReportMetadataDTO,
)
from .files import TempFileRef


class IParser(Protocol):
    def parse(self, files: List[RawFileDTO]) -> ParsedMessagesDTO:
        ...


class IExtractor(Protocol):
    def extract(self, parsed: ParsedMessagesDTO) -> ExtractionResultDTO:
        ...


class IReportBuilder(Protocol):
    def build(
            self, extraction: ExtractionResultDTO, metadata: ReportMetadataDTO
    ) -> ReportDTO:
        ...


class IExcelRenderer(Protocol):
    def render(self, report: "ExcelReport") -> bytes:
        ...


class ISessionStore(Protocol):
    def get(self, user_id: str) -> Optional["SessionRecord"]:
        ...

    def save(self, user_id: str, record: "SessionRecord") -> None:
        ...

    def clear(self, user_id: str) -> None:
        ...


class ITempFileStorage(Protocol):
    def save(self, filename: str, content: bytes, mime_type: Optional[str]) -> TempFileRef:
        ...

    def read(self, ref: TempFileRef) -> bytes:
        ...

    def delete(self, ref: TempFileRef) -> None:
        ...
