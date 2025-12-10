from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TempFileRef:
    id: str
    path: Path
    filename: str
    size_bytes: int
    mime_type: Optional[str]
    created_at: datetime

    @classmethod
    def create(cls, path: Path, filename: str, mime_type: Optional[str], size_bytes: int) -> "TempFileRef":
        return cls(
            id=uuid.uuid4().hex,
            path=path,
            filename=filename,
            size_bytes=size_bytes,
            mime_type=mime_type,
            created_at=_now(),
        )
