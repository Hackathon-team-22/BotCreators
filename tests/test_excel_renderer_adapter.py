import io
from zipfile import ZipFile

from audience_bot.domain.reporting import ExcelReport, SheetModel
from audience_bot.infrastructure.excel_renderer import ExcelRendererAdapter


def make_excel_report() -> ExcelReport:
    rows = [
        {"A": "1", "B": "2"},
        {"A": "3", "B": "4"},
    ]
    sheet = SheetModel(name="Sheet1", columns=["A", "B"], rows=rows)
    return ExcelReport(sheets=[sheet])


def test_excel_renderer_creates_workbook():
    renderer = ExcelRendererAdapter()
    payload = renderer.render(make_excel_report())

    with ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        assert "[Content_Types].xml" in names
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        assert any(name.endswith(".rels") for name in names)
