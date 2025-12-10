from pathlib import Path

import pytest

from audience_bot.cli import create_pipeline
from audience_bot.application.config import PipelineConfig
from audience_bot.application.usecases.dto import RawFileDTO, ReportDTO
from audience_bot.application.usecases.exceptions import PipelineError
from audience_bot.application.services.conversation import ConversationService
from audience_bot.application.services.sessions import InMemorySessionStore
from audience_bot.domain.reporting import ReportFormat
from audience_bot.infrastructure.temp_storage import InMemoryTempStorageAdapter
from audience_bot.infrastructure.telegram import BotController, TelegramWebhookAdapter


@pytest.fixture
def conversation_service() -> ConversationService:
    pipeline = create_pipeline()
    session_store = InMemorySessionStore()
    temp_storage = InMemoryTempStorageAdapter()
    config = PipelineConfig(max_files=1, max_file_size=10 * 1024 * 1024)
    return ConversationService(session_store, pipeline, temp_storage, config)


@pytest.fixture
def raw_json_file() -> RawFileDTO:
    path = Path("tests/data/sample.json")
    return RawFileDTO(path=str(path), filename=path.name, content=path.read_bytes())


def test_upload_then_process_clears_session(conversation_service: ConversationService, raw_json_file: RawFileDTO):
    upload_result = conversation_service.upload_file("user-1", raw_json_file)
    assert "загружен" in upload_result.text
    process_response = conversation_service.process("user-1", chat_name="Test chat")
    assert not process_response.is_error
    session = conversation_service._sessions.get("user-1")  # type: ignore[attr-defined]
    assert len(session.files) == 0


def test_upload_limit_is_enforced(conversation_service: ConversationService, raw_json_file: RawFileDTO):
    conversation_service.upload_file("user-2", raw_json_file)
    second_file = RawFileDTO(
        path="tests/data/sample.html",
        filename="sample.html",
        content=Path("tests/data/sample.html").read_bytes(),
    )
    response = conversation_service.upload_file("user-2", second_file)
    assert response.is_error
    assert "лимит" in response.text.lower()


def test_process_command_passes_target(raw_json_file: RawFileDTO):
    class StubAPI:
        def __init__(self):
            self.sent = []

        def send_text(self, chat_id, text):
            self.sent.append((chat_id, text))

        def send_file(self, chat_id, file_bytes, filename):
            self.sent.append((chat_id, filename))

        def download_file(self, file_id: str) -> bytes:
            raise NotImplementedError

    class StubPipeline:
        def __init__(self, report_format: ReportFormat):
            self.report = ReportDTO(
                format=report_format,
                text="ok" if report_format == ReportFormat.PLAIN_TEXT else None,
                excel_bytes=b"excel" if report_format == ReportFormat.EXCEL else None,
            )

        def execute(self, files, chat_name, user_id):
            return self.report

    pipeline = StubPipeline(ReportFormat.EXCEL)
    session_store = InMemorySessionStore()
    temp_storage = InMemoryTempStorageAdapter()
    config = PipelineConfig(max_files=1, max_file_size=10 * 1024 * 1024)
    service = ConversationService(session_store, pipeline, temp_storage, config)
    api = StubAPI()
    controller = BotController(service, api)
    adapter = TelegramWebhookAdapter(controller)

    ref = temp_storage.save("sample.json", raw_json_file.content, None)
    session = session_store.get("u")
    session.add_file(ref)
    session_store.save(session)

    update = {
        "message": {
            "chat": {"id": "c"},
            "from": {"id": "u"},
            "text": "/process file",
        }
    }

    adapter.handle_request(update)

    assert any(isinstance(item[1], str) and item[1].endswith(".xlsx") for item in api.sent)


def test_process_chat_target_adds_note(raw_json_file: RawFileDTO):
    class StubPipeline:
        def execute(self, files, chat_name, user_id):
            return ReportDTO(format=ReportFormat.EXCEL, excel_bytes=b"x")

    pipeline = StubPipeline()
    session_store = InMemorySessionStore()
    temp_storage = InMemoryTempStorageAdapter()
    config = PipelineConfig(max_files=2, max_file_size=10 * 1024 * 1024)
    service = ConversationService(session_store, pipeline, temp_storage, config)
    api = type("StubAPI", (), {"sent": [], "send_text": lambda self, chat, text: self.sent.append(("text", text)), "send_file": lambda self, chat, data, name: self.sent.append(("file", name)), "download_file": lambda self, fid: b""})()
    controller = BotController(service, api)
    adapter = TelegramWebhookAdapter(controller)

    ref = temp_storage.save("sample.json", raw_json_file.content, None)
    session = session_store.get("u")
    session.add_file(ref)
    session_store.save(session)

    update = {
        "message": {
            "chat": {"id": "c"},
            "from": {"id": "u"},
            "text": "/process chat",
        }
    }

    adapter.handle_request(update)

    assert any("слишком много участников" in entry[1].lower() for entry in api.sent if entry[0] == "text")


def test_process_file_target_with_plain_text_returns_notice(raw_json_file: RawFileDTO):
    class StubPipeline:
        def execute(self, files, chat_name, user_id):
            return ReportDTO(format=ReportFormat.PLAIN_TEXT, text="data")

    pipeline = StubPipeline()
    session_store = InMemorySessionStore()
    temp_storage = InMemoryTempStorageAdapter()
    config = PipelineConfig(max_files=2, max_file_size=10 * 1024 * 1024)
    service = ConversationService(session_store, pipeline, temp_storage, config)
    api = type("StubAPI", (), {"sent": [], "send_text": lambda self, chat, text: self.sent.append(("text", text)), "send_file": lambda self, chat, data, name: self.sent.append(("file", name)), "download_file": lambda self, fid: b""})()
    controller = BotController(service, api)
    adapter = TelegramWebhookAdapter(controller)

    ref = temp_storage.save("sample.json", raw_json_file.content, None)
    session = session_store.get("user")
    session.add_file(ref)
    session_store.save(session)

    update = {
        "message": {
            "chat": {"id": "c"},
            "from": {"id": "user"},
            "text": "/process file",
        }
    }

    adapter.handle_request(update)

    assert any("отчёт небольшой" in entry[1].lower() for entry in api.sent if entry[0] == "text")


def test_process_reports_pipeline_error_to_user(raw_json_file: RawFileDTO):
    class FailingPipeline:
        def execute(self, files, chat_name, user_id):
            raise PipelineError("превышен лимит сообщений")

    pipeline = FailingPipeline()
    session_store = InMemorySessionStore()
    temp_storage = InMemoryTempStorageAdapter()
    config = PipelineConfig(max_files=1, max_file_size=10 * 1024 * 1024)
    service = ConversationService(session_store, pipeline, temp_storage, config)

    temp_ref = temp_storage.save("sample.json", raw_json_file.content, None)
    session = session_store.get("user")
    session.add_file(temp_ref)
    session_store.save(session)

    response = service.process("user", chat_name="Chat")

    assert response.is_error
    assert "лимит" in response.text.lower()


def test_upload_rejects_too_large_file(conversation_service: ConversationService):
    big_content = b"x" * (conversation_service._config.max_file_size + 1)  # type: ignore[attr-defined]
    large_file = RawFileDTO(path="tests/data/big.bin", filename="big.bin", content=big_content)

    response = conversation_service.upload_file("user-big", large_file)

    assert response.is_error
    assert "превышает" in response.text.lower()
