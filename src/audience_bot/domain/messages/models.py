from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, List, Optional


@dataclass(frozen=True)
class RawUserRef:
    display_name: str
    user_id: Optional[int]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_deleted: bool = False
    is_bot: bool = False
    is_channel: bool = False

    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(part for part in parts if part).strip() or self.display_name

@dataclass(frozen=True)
class ChatMessage:
    message_id: Optional[str]
    timestamp: Optional[datetime]
    author: Optional[RawUserRef]
    mentions: List[RawUserRef] = field(default_factory=list)
    text: str = ""
    is_service_message: bool = False
    is_forwarded: bool = False
    forward_author: Optional[RawUserRef] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        """Простейший парсер JSON-структуры в доменную модель."""
        timestamp = cls._parse_timestamp(data)
        author = cls._build_author(data)
        mentions = cls._build_mentions(data)
        fwd_author = cls._build_forward_author(data)
        return cls(
            message_id=cls._parse_message_id(data),
            timestamp=timestamp,
            author=author,
            mentions=mentions,
            text=data.get("text", ""),
            is_service_message=data.get("type") == "service" or data.get("is_service_message", False),
            is_forwarded=bool(fwd_author),
            forward_author=fwd_author,
        )

    @classmethod
    def _build_author(cls, data: dict[str, Any]) -> Optional[RawUserRef]:
        author_payload = data.get("author")
        fallback_name = None
        if isinstance(author_payload, dict):
            return cls._build_raw_user_ref(author_payload)
        fallback_name = data.get("from") or data.get("actor")
        fallback_id = data.get("from_id") or data.get("actor_id")
        fallback_username = data.get("from_username") or data.get("actor_username")
        payload: dict[str, Any] = {"id": fallback_id}
        if fallback_username:
            payload["username"] = fallback_username
        return cls._build_raw_user_ref(payload, fallback_name)

    @classmethod
    def _build_mentions(cls, data: dict[str, Any]) -> List[RawUserRef]:
        mentions: List[RawUserRef] = []
        for entry in data.get("mentions") or []:
            ref = None
            if isinstance(entry, dict):
                ref = cls._build_raw_user_ref(entry)
            elif isinstance(entry, str):
                ref = cls._build_raw_user_ref({}, entry)
            if ref:
                mentions.append(ref)
        return mentions

    @classmethod
    def _build_forward_author(cls, data: dict[str, Any]) -> Optional[RawUserRef]:
        source_name = data.get("forwarded_from") or data.get("forward_from") or data.get("forwarded_from_chat")
        source_id = data.get("forwarded_from_id") or data.get("forward_from_id") or data.get("forwarded_from_chat_id")
        if not source_name and not source_id:
            return None
        payload: dict[str, Any] = {
            "id": source_id,
            "username": data.get("forwarded_from_username"),
            "display_name": source_name,
        }
        # Простая эвристика канала
        id_str = str(source_id) if source_id is not None else ""
        if "channel" in id_str or "forwarded_from_chat" in data or (source_name and "channel" in source_name.lower()):
            payload["is_channel"] = True
        return cls._build_raw_user_ref(payload, fallback_name=source_name)

    @classmethod
    def _build_raw_user_ref(
        cls, payload: dict[str, Any], fallback_name: Optional[str] = None
    ) -> Optional[RawUserRef]:
        if not payload and not fallback_name:
            return None
        first_name = payload.get("first_name")
        last_name = payload.get("last_name")
        if not (first_name or last_name) and fallback_name:
            first_name, last_name = _split_full_name(fallback_name)
        display_name = payload.get("display_name") or fallback_name or first_name or last_name or payload.get("username")
        if not display_name:
            return None
        return RawUserRef(
            display_name=str(display_name).strip(),
            user_id=_parse_user_id(payload.get("id") or payload.get("user_id")),
            username=payload.get("username"),
            first_name=first_name,
            last_name=last_name,
            is_deleted=payload.get("is_deleted", False),
            is_bot=payload.get("is_bot", False),
            is_channel=payload.get("is_channel", False),
        )

    @staticmethod
    def _parse_timestamp(data: dict[str, Any]) -> Optional[datetime]:
        timestamp = data.get("date")
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp)
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp)
            except ValueError:
                pass
            if timestamp.isdigit():
                return datetime.fromtimestamp(int(timestamp))
        unixtime = data.get("date_unixtime")
        if isinstance(unixtime, str) and unixtime.isdigit():
            return datetime.fromtimestamp(int(unixtime))
        if isinstance(unixtime, (int, float)):
            return datetime.fromtimestamp(unixtime)
        return None

    @staticmethod
    def _parse_message_id(data: dict[str, Any]) -> Optional[str]:
        identifier = data.get("message_id") or data.get("id")
        if identifier is None:
            return None
        return str(identifier)


@dataclass(frozen=True)
class ProfileId:
    user_id: Optional[int]
    username: Optional[str]
    display_name: Optional[str]

    @classmethod
    def from_raw(cls, raw: RawUserRef) -> Optional["ProfileId"]:
        if raw.user_id is None and not raw.username and not raw.display_name:
            return None
        return cls(user_id=raw.user_id, username=raw.username, display_name=raw.display_name or None)

    def _comparison_key(self) -> tuple[str, Optional[str | int]]:
        if self.user_id is not None:
            return ("user_id", self.user_id)
        if self.username:
            return ("username", self.username.casefold())
        if self.display_name:
            return ("display_name", self.display_name.casefold())
        return ("none", None)

    def __hash__(self) -> int:
        return hash(self._comparison_key())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProfileId):
            return NotImplemented
        return self._comparison_key() == other._comparison_key()


@dataclass
class ProfileContext:
    raw: RawUserRef
    source: str
    message_id: Optional[str]


def non_deleted_users(*users: RawUserRef) -> Iterable[RawUserRef]:
    for user in users:
        if user and not user.is_deleted:
            yield user


def _split_full_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not full_name:
        return None, None
    parts = [part.strip() for part in full_name.strip().split() if part.strip()]
    if not parts:
        return None, None
    first = parts[0]
    last = " ".join(parts[1:]) if len(parts) > 1 else None
    return first, last


def _parse_user_id(value: Optional[str | int]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            try:
                return int(digits)
            except ValueError:
                pass
    return None
