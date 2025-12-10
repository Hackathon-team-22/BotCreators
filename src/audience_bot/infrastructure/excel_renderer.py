from __future__ import annotations

import io

from openpyxl import Workbook

from ..domain.reporting import ExcelReport


class ExcelRendererAdapter:
    """Рендерит ExcelReport в полноценный xlsx через openpyxl для совместимости с Excel 2007+."""

    def render(self, report: ExcelReport) -> bytes:
        wb = Workbook()
        # По умолчанию создаётся один лист — переиспользуем или удаляем, если имён больше одного.
        if report.sheets:
            wb.remove(wb.active)

        for sheet in report.sheets:
            ws = wb.create_sheet(title=sheet.name)
            if sheet.columns:
                ws.append(list(sheet.columns))
            for row in sheet.rows:
                ws.append([row.get(col, "") for col in sheet.columns])

        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()
