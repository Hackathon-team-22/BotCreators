from pathlib import Path

import pytest

from audience_bot.application.usecases.dto import RawFileDTO
from audience_bot.infrastructure.parsers import ParserAdapter


@pytest.fixture
def parser_adapter() -> ParserAdapter:
    return ParserAdapter()


@pytest.fixture
def sample_json_raw() -> RawFileDTO:
    path = Path("tests/data/sample.json")
    return RawFileDTO(path=str(path), filename=path.name, content=path.read_bytes())


@pytest.fixture
def sample_html_raw() -> RawFileDTO:
    path = Path("tests/data/sample.html")
    return RawFileDTO(path=str(path), filename=path.name, content=path.read_bytes())


def test_parse_json_export(parser_adapter: ParserAdapter):
    path = Path("tests/data/sample.json")
    raw_file = RawFileDTO(
        path=str(path),
        filename=path.name,
        content=path.read_bytes(),
    )
    parsed = parser_adapter.parse([raw_file])

    assert parsed.messages, "Ожидается как минимум одно сообщение из JSON-экспорта"
    authors = [msg.author for msg in parsed.messages if msg.author]
    assert any(author.username or author.first_name for author in authors)


def test_parse_html_export(parser_adapter: ParserAdapter):
    html = """
    <html><body>
        <div class="message" data-id="1" data-author-id="10" data-text="hi" data-date="2025-01-01T00:00:00"
             data-author-username="alice" data-author-first-name="Alice" data-author-last-name="Liddell">
        </div>
        <div class="message" data-id="2" data-author-id="11" data-text="ping" data-date="2025-01-01T00:00:10"
             data-author-username="bob" data-author-first-name="Bob">
        </div>
    </body></html>
    """
    raw_file = RawFileDTO(path="<html>", filename="test.html", content=html.encode("utf-8"))
    parsed = parser_adapter.parse([raw_file])

    assert len(parsed.messages) == 2
    assert parsed.messages[0].text == "hi"
    assert parsed.messages[1].author.display_name == "Bob"


def test_parse_zip_container(parser_adapter: ParserAdapter):
    import io
    import zipfile

    json_payload = b'{"messages":[{"id":123,"text":"zip","date":"2025-01-02T00:00:00","from":"ZipUser","from_id":"321"}]}'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("inner.json", json_payload)
    raw_zip = RawFileDTO(path="<zip>", filename="export.zip", content=buffer.getvalue())
    parsed = parser_adapter.parse([raw_zip])

    assert parsed.messages
    assert parsed.messages[0].text == "zip"


def test_parse_sample_json_file(parser_adapter: ParserAdapter, sample_json_raw: RawFileDTO):
    """Проверяем реальный sample.json: авторы, реакции, сервисные события."""
    parsed = parser_adapter.parse([sample_json_raw])

    assert parsed.messages
    authors = [msg.author for msg in parsed.messages if msg.author]
    assert any((a.username or a.first_name or a.display_name) for a in authors), "Ожидается идентифицирующее поле автора"
    assert any(m.is_service_message for m in parsed.messages), "Ожидается наличие сервисных событий"
    assert all(msg.message_id for msg in parsed.messages), "Каждое сообщение должно иметь id"
    assert any(msg.timestamp for msg in parsed.messages), "Ожидается наличие временных меток"


def test_parse_sample_html_file(parser_adapter: ParserAdapter, sample_html_raw: RawFileDTO):
    """Проверяем реальный sample.html: авторы и текст загружаются."""
    parsed = parser_adapter.parse([sample_html_raw])

    assert parsed.messages
    assert all(msg.message_id for msg in parsed.messages)
    assert any(msg.author for msg in parsed.messages), "Ожидается наличие авторов"
    assert any(msg.text for msg in parsed.messages), "Ожидается наличие текста"
    assert all(msg.timestamp for msg in parsed.messages if msg.timestamp is not None)
