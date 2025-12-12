from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from ..usecases.files import TempFileRef
from ..usecases.ports import ISessionStore


class SessionState(str, Enum):
    EMPTY = "empty"
    COLLECTING = "collecting"
    READY = "ready"
    PROCESSING = "processing"


@dataclass
class SessionRecord:
    user_id: str
    files: List[TempFileRef] = field(default_factory=list)
    state: SessionState = SessionState.EMPTY
    export_format: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_file(self, temp_file: TempFileRef) -> None:
        self.files.append(temp_file)
        self.updated_at = datetime.now(timezone.utc)

    def clear(self) -> None:
        self.files.clear()
        self.state = SessionState.EMPTY
        self.export_format = None
        self.updated_at = datetime.now(timezone.utc)


class InMemorySessionStore(ISessionStore):
    def __init__(self):
        self._store: Dict[str, SessionRecord] = {}

    def get(self, user_id: str) -> SessionRecord:
        record = self._store.get(user_id)
        if record is None:
            record = SessionRecord(user_id=user_id)
            self._store[user_id] = record
        return record

    def save(self, session: SessionRecord) -> None:
        session.updated_at = datetime.now(timezone.utc)
        self._store[session.user_id] = session

    def clear(self, user_id: str) -> None:
        record = self._store.get(user_id)
        if record:
            record.clear()
