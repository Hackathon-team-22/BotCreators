from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from ..application.usecases.files import TempFileRef


class TempFileStorageError(Exception):
    pass


class TempFileStorageAdapter:
    def __init__(self, base_dir: Optional[Path] = None):
        self._base_dir = Path(base_dir or Path(tempfile.mkdtemp(prefix="audience_bot_")))
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes, mime_type: Optional[str] = None) -> TempFileRef:
        target = self._base_dir / f"{TempFileRef.__name__.lower()}-{filename}-{os.urandom(4).hex()}"
        try:
            target.write_bytes(content)
        except OSError as exc:
            raise TempFileStorageError("Не удалось сохранить файл в temp storage.") from exc
        return TempFileRef.create(
            path=target,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(content),
        )

    def read(self, ref: TempFileRef) -> bytes:
        try:
            return ref.path.read_bytes()
        except FileNotFoundError as exc:
            raise TempFileStorageError("Временный файл удалён.") from exc

    def delete(self, ref: TempFileRef) -> None:
        self._delete_path(ref.path)

    def _delete_path(self, path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def cleanup(self, max_age_seconds: int) -> List[Path]:
        expired: List[Path] = []
        threshold = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        for entry in self._base_dir.iterdir():
            try:
                mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if mtime < threshold:
                expired.append(entry)
                self._delete_path(entry)
        return expired


class InMemoryTempStorageAdapter:
    """Хранилище временных файлов в памяти, без записи на диск."""

    def __init__(self):
        self._storage: Dict[str, bytes] = {}

    def save(self, filename: str, content: bytes, mime_type: Optional[str] = None) -> TempFileRef:
        file_id = uuid.uuid4().hex
        self._storage[file_id] = content
        pseudo_path = Path(f"/inmem/{file_id}")
        return TempFileRef(
            id=file_id,
            path=pseudo_path,
            filename=filename,
            size_bytes=len(content),
            mime_type=mime_type,
            created_at=datetime.now(timezone.utc),
        )

    def read(self, ref: TempFileRef) -> bytes:
        try:
            return self._storage[ref.id]
        except KeyError as exc:
            raise TempFileStorageError("Временные данные удалены.") from exc

    def delete(self, ref: TempFileRef) -> None:
        self._storage.pop(ref.id, None)
