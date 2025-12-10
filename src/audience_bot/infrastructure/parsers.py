from __future__ import annotations

import io
import json
import zipfile
from html.parser import HTMLParser
from typing import Any, Dict, List

from ..application.usecases.dto import RawFileDTO, ParsedMessagesDTO
from ..domain.messages import ChatMessage


class _HTMLMessageParser(HTMLParser):
    """Минимальный парсер, ожидающий <div class=\"message\"> с data-атрибутами."""

    def __init__(self) -> None:
        super().__init__()
        self._messages: List[Dict[str, Any]] = []
        self._current: Dict[str, Any] | None = None
        self._in_from_name = False
        self._in_text = False
        self._in_date = False
        self._message_depth = 0

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str]]) -> None:
        if tag != "div":
            return
        meta = dict(attrs)
        class_value = meta.get("class", "")
        classes = class_value.split()

        # Новый блок сообщения (Telegram HTML: class содержит "message")
        if meta.get("class") == "message" or "message" in classes:
            self._current = {
                "message_id": meta.get("data-id") or meta.get("id"),
                "text": meta.get("data-text", ""),
            }
            if meta.get("data-date"):
                self._current["date"] = meta.get("data-date")
            self._message_depth = 1

            author_id = meta.get("data-author-id")
            author_username = meta.get("data-author-username")
            if author_id or author_username:
                self._current["author"] = {
                    "id": int(author_id) if author_id and author_id.isdigit() else None,
                    "username": author_username,
                    "first_name": meta.get("data-author-first-name"),
                    "last_name": meta.get("data-author-last-name"),
                    "display_name": None,
                    "is_deleted": meta.get("data-author-deleted") == "1",
                    "is_bot": meta.get("data-author-bot") == "1",
                    "is_channel": meta.get("data-author-channel") == "1",
                }
            mentions = []
            mention_ids = meta.get("data-mention-ids", "")
            mention_usernames = meta.get("data-mention-usernames", "")
            ids = [part.strip() for part in mention_ids.split(",") if part.strip()]
            usernames = [part.strip() for part in mention_usernames.split(",") if part.strip()]
            for idx, username in enumerate(usernames):
                mention = {"username": username}
                if idx < len(ids) and ids[idx].isdigit():
                    mention["id"] = int(ids[idx])
                mentions.append(mention)
            if mentions:
                self._current["mentions"] = mentions
            return

        # Внутри текущего сообщения отслеживаем вложенные блоки автора, даты, текста
        if self._current:
            self._message_depth += 1
            if "from_name" in classes:
                self._in_from_name = True
            if "text" in classes:
                self._in_text = True
            if classes == ["pull_right", "date", "details"] or "date" in classes:
                # Telegram export ставит title с ISO-датой
                if meta.get("title"):
                    self._current["date"] = meta.get("title")
                self._in_date = True

    def handle_endtag(self, tag: str) -> None:
        if tag != "div":
            return
        if self._message_depth > 0:
            self._message_depth -= 1
            if self._message_depth == 0 and self._current:
                self._messages.append(self._current)
                self._current = None
        # Сброс флагов вложенных блоков
        self._in_from_name = False
        self._in_text = False
        self._in_date = False

    def handle_data(self, data: str) -> None:
        if not self._current:
            return
        text = data.strip()
        if not text:
            return
        if self._in_from_name:
            self._current["from"] = text
            if self._current.get("author") is None:
                self._current["author"] = {"display_name": text}
        elif self._in_text:
            existing = self._current.get("text", "")
            sep = "\n" if existing else ""
            self._current["text"] = f"{existing}{sep}{text}"
        elif self._in_date:
            self._current["date"] = text

    def get_messages(self) -> List[Dict[str, Any]]:
        return self._messages


class ParserAdapter:
    def parse(self, files: List[RawFileDTO]) -> ParsedMessagesDTO:
        messages = []
        for raw in files:
            messages.extend(self._parse_file(raw))
        if not messages:
            raise ValueError("Парсер вернул пустой список сообщений.")
        return ParsedMessagesDTO(messages=messages)

    def _parse_file(self, file: RawFileDTO) -> List[ChatMessage]:
        if zipfile.is_zipfile(io.BytesIO(file.content)):
            return self._parse_zip(file.content)
        text = self._decode(file.content)
        if text.lstrip().startswith("{"):
            return self._parse_json(text)
        if text.lstrip().startswith("<"):
            return self._parse_html(text)
        raise ValueError(f"Неподдерживаемый формат файла {file.filename}")

    def _parse_zip(self, blob: bytes) -> List[ChatMessage]:
        messages: List[ChatMessage] = []
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            for member in archive.namelist():
                with archive.open(member) as stream:
                    data = stream.read()
                    messages.extend(self._parse_file(RawFileDTO(path=member, filename=member, content=data)))
        return messages

    def _decode(self, data: bytes) -> str:
        return data.decode("utf-8", errors="ignore")

    def _parse_json(self, text: str) -> List[ChatMessage]:
        payload = json.loads(text)
        entries = payload.get("messages") or payload.get("chat_history") or []
        return [ChatMessage.from_dict(entry) for entry in entries if isinstance(entry, dict)]

    def _parse_html(self, text: str) -> List[ChatMessage]:
        parser = _HTMLMessageParser()
        parser.feed(text)
        return [ChatMessage.from_dict(entry) for entry in parser.get_messages()]
