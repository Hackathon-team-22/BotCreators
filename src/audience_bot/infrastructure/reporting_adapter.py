from __future__ import annotations

import logging

from ..application.usecases.dto import ExtractionResultDTO, ReportDTO, ReportMetadataDTO
from ..application.usecases.ports import IExcelRenderer, IReportBuilder
from ..domain.reporting import (
    AudienceReport,
    ExcelReportBuilder,
    ReportFormat,
    ReportMetadata,
    ReportPolicy,
    TextListBuilder,
)

logger = logging.getLogger(__name__)


class ReportingAdapter(IReportBuilder):
    def __init__(self, renderer: IExcelRenderer, report_policy: ReportPolicy | None = None, force_excel: bool = False):
        self._renderer = renderer
        self._excel_builder = ExcelReportBuilder()
        self._report_policy = report_policy or ReportPolicy()
        self._force_excel = force_excel

    def build(
            self, extraction: ExtractionResultDTO, metadata: ReportMetadataDTO
    ) -> ReportDTO:
        metadata_model = ReportMetadata(
            exported_at=metadata.export_time,
            chat_name=metadata.chat_name,
            participant_count=extraction.result.participant_count(),
        )
        format_choice = ReportFormat.EXCEL if self._force_excel else self._report_policy.choose(extraction.result)
        report_model = AudienceReport()
        if format_choice == ReportFormat.PLAIN_TEXT:
            text_list = TextListBuilder.build(extraction.result)
            report_model.set_text(metadata_model, text_list)
            report_model.finalize()
            joined_text = "\n".join(text_list.lines)
            return ReportDTO(format=format_choice, text=joined_text)
        excel_model = self._excel_builder.build(extraction.result, metadata_model)
        report_model.set_excel(metadata_model, excel_model)
        report_model.finalize()

        logger.info(
            "report_format_choice",
            extra={"report_format": format_choice.value, "participant_count": metadata_model.participant_count},
        )
        excel_bytes = self._renderer.render(excel_model)
        return ReportDTO(format=format_choice, excel_bytes=excel_bytes)
