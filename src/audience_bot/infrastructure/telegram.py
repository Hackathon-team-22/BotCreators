from __future__ import annotations

from dataclasses import dataclass
import io
import json
import logging
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..application.services.conversation import BotResponse, ConversationService
from ..application.usecases.dto import RawFileDTO
from ..application.config import TelegramConfig

LOGGER = logging.getLogger(__name__)


@dataclass
class TelegramDocument:
    filename: str
    content: Optional[bytes] = None
    mime_type: Optional[str] = None
    file_id: Optional[str] = None


@dataclass
class TelegramUpdateDTO:
    user_id: str
    chat_id: str
    command: Optional[str] = None
    document: Optional[TelegramDocument] = None


class BotController:
    def __init__(self, conversation: ConversationService, api_adapter: "TelegramAPIAdapter"):
        self._conversation = conversation
        self._api = api_adapter

    def handle_update(self, update: TelegramUpdateDTO) -> None:
        response = self._route(update)
        self._send_response(update.chat_id, response)

    def _route(self, update: TelegramUpdateDTO) -> BotResponse:
        cmd = (update.command or "").strip().lower()
        if cmd == "/start":
            return self._conversation.start(update.user_id)
        if cmd in {"/help", "/?", "?"}:
            return self._conversation.help(update.user_id)
        if cmd == "/reset":
            return self._conversation.reset(update.user_id)
        if cmd == "/status":
            return self._conversation.status(update.user_id)
        if cmd.startswith("/process"):
            parts = cmd.split()
            target = "auto"
            if len(parts) > 1 and parts[1] in {"chat", "file"}:
                target = parts[1]
            return self._conversation.process(update.user_id, chat_name=None, target=target)
        if update.document:
            document = update.document
            if document.content is None and document.file_id:
                try:
                    document.content = self._api.download_file(document.file_id)
                except TelegramAPIError as exc:
                    LOGGER.exception("Не удалось загрузить файл по file_id=%s", document.file_id, exc_info=exc)
                    return BotResponse(text="Ошибка загрузки файла.", is_error=True)
            raw = RawFileDTO(
                path="<telegram>",
                filename=document.filename,
                content=document.content or b"",
                mime_type=document.mime_type,
            )
            return self._conversation.upload_file(update.user_id, raw)
        return BotResponse(text="Неизвестная команда.", is_error=True)

    def _send_response(self, chat_id: str, response: BotResponse) -> None:
        try:
            if response.file_bytes:
                self._api.send_file(chat_id, response.file_bytes, response.filename or "audience-report.xlsx")
            self._api.send_text(chat_id, response.text or "Готово.")
        except TelegramAPIError:
            LOGGER.exception("Ошибка отправки ответа Telegram.")


class TelegramAPIError(Exception):
    pass


class TelegramAPIAdapter:
    def __init__(self, config: TelegramConfig):
        self._config = config
        self._base_url = f"{self._config.base_url}/bot{self._config.token}"
        self._file_base = f"{self._config.file_base_url}/bot{self._config.token}"

    def send_text(self, chat_id: str, text: str) -> None:
        self._post("sendMessage", {"chat_id": chat_id, "text": text})

    def send_file(self, chat_id: str, file_bytes: bytes, filename: str) -> None:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        fields = {"chat_id": chat_id}
        files = [("document", filename, file_bytes, content_type)]
        self._multipart_post("sendDocument", fields, files)

    def download_file(self, file_id: str) -> bytes:
        payload = self._post("getFile", {"file_id": file_id})
        file_path = payload.get("result", {}).get("file_path")
        if not file_path:
            raise TelegramAPIError("Не удалось получить путь к файлу.")
        url = f"{self._file_base}/{file_path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read()
        except Exception as exc:
            raise TelegramAPIError("Не удалось скачать файл.") from exc

    def _post(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        body = urllib.parse.urlencode(data).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        return self._request(method, body, headers)

    def _multipart_post(
        self,
        method: str,
        fields: Dict[str, Any],
        files: List[Tuple[str, str, bytes, str]],
    ) -> Dict[str, Any]:
        boundary = uuid.uuid4().hex
        body = self._build_multipart_body(boundary, fields, files)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        return self._request(method, body, headers)

    def _build_multipart_body(
        self, boundary: str, fields: Dict[str, Any], files: List[Tuple[str, str, bytes, str]]
    ) -> bytes:
        buffer = io.BytesIO()
        for name, value in fields.items():
            buffer.write(f"--{boundary}\r\n".encode())
            buffer.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            buffer.write(str(value).encode())
            buffer.write(b"\r\n")
        for name, filename, data, content_type in files:
            buffer.write(f"--{boundary}\r\n".encode())
            buffer.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
            buffer.write(f"Content-Type: {content_type}\r\n\r\n".encode())
            buffer.write(data)
            buffer.write(b"\r\n")
        buffer.write(f"--{boundary}--\r\n".encode())
        return buffer.getvalue()

    def _request(self, method: str, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        url = f"{self._base_url}/{method}"
        req = urllib.request.Request(url, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            raise TelegramAPIError(f"HTTP {exc.code}") from exc
        except Exception as exc:
            raise TelegramAPIError("Не удалось выполнить вызов Telegram API.") from exc
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise TelegramAPIError("Некорректный JSON от Telegram.") from exc


class ConsoleTelegramAPIAdapter:
    def send_text(self, chat_id: str, text: str) -> None:
        LOGGER.info("[Telegram console] chat=%s text=%s", chat_id, text)

    def send_file(self, chat_id: str, file_bytes: bytes, filename: str) -> None:
        LOGGER.info(
            "[Telegram console] chat=%s file=%s size=%d",
            chat_id,
            filename,
            len(file_bytes),
        )

    def download_file(self, file_id: str) -> bytes:
        raise TelegramAPIError("Console adapter не умеет скачивать файлы.")


class TelegramWebhookAdapter:
    def __init__(self, controller: BotController):
        self._controller = controller

    def handle_request(self, payload: Dict[str, Any]) -> None:
        update = self._normalize(payload)
        self._controller.handle_update(update)

    def _normalize(self, payload: Dict[str, Any]) -> TelegramUpdateDTO:
        message = payload.get("message") or payload.get("edited_message") or payload
        user = message.get("from", {})
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        user_id = str(user.get("id", ""))
        text = (message.get("text") or "").strip()
        command = text if text and (text.startswith("/") or text.startswith("?")) else None
        document = None
        doc_payload = message.get("document")
        if doc_payload:
            document = TelegramDocument(
                filename=doc_payload.get("file_name") or doc_payload.get("file_id", "document"),
                mime_type=doc_payload.get("mime_type"),
                file_id=doc_payload.get("file_id"),
            )
        return TelegramUpdateDTO(user_id=user_id, chat_id=chat_id, command=command, document=document)


class TelegramPollingService:
    def __init__(self, adapter: TelegramWebhookAdapter, config: TelegramConfig):
        self._adapter = adapter
        self._config = config
        self._base_url = f"{self._config.base_url}/bot{self._config.token}"
        self._running = False

    def run(self) -> None:
        LOGGER.info("Запуск long polling (token=%s)", self._config.token[:8])
        offset: Optional[int] = None
        self._running = True
        try:
            while self._running:
                params = {"timeout": self._config.poll_timeout}
                if offset:
                    params["offset"] = offset
                url = f"{self._base_url}/getUpdates?{urllib.parse.urlencode(params)}"
                try:
                    with urllib.request.urlopen(url, timeout=self._config.poll_timeout + 5) as response:
                        payload = json.load(response)
                except Exception as exc:
                    LOGGER.exception("Polling error")
                    time.sleep(self._config.poll_interval)
                    continue
                for update in payload.get("result", []):
                    offset = update.get("update_id", offset)
                    if offset is not None:
                        offset += 1
                    self._adapter.handle_request(update)
        except KeyboardInterrupt:
            LOGGER.info("Long polling остановлен пользователем.")
