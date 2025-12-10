from __future__ import annotations

from ..application.usecases.dto import ExtractionResultDTO, ParsedMessagesDTO
from ..application.usecases.ports import IExtractor
from ..domain.extraction import AudienceExtractor


class ExtractionAdapter(IExtractor):
    def __init__(self, extractor: AudienceExtractor | None = None):
        self._extractor = extractor or AudienceExtractor()

    def extract(self, parsed: ParsedMessagesDTO) -> ExtractionResultDTO:
        result = self._extractor.extract(parsed.messages)
        return ExtractionResultDTO(result=result)
