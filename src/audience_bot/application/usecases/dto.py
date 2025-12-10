from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from audience_bot.domain.extraction import ExtractionResult
from audience_bot.domain.messages import ChatMessage
from audience_bot.domain.reporting import ReportFormat


@dataclass
class RawFileDTO:
    path: str
    filename: str
    content: bytes
    mime_type: Optional[str] = None


@dataclass
class ParsedMessagesDTO:
    messages: List[ChatMessage]


@dataclass
class ExtractionResultDTO:
    result: ExtractionResult


@dataclass
class ReportMetadataDTO:
    export_time: datetime
    chat_name: Optional[str]


@dataclass
class ReportDTO:
    format: ReportFormat
    text: Optional[str] = None
    excel_bytes: Optional[bytes] = None
