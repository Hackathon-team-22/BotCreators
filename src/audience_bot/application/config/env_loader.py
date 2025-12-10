from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional


def _search_upwards(start: Path, targets: Iterable[str]) -> Optional[Path]:
    current = start.resolve()
    root = current.anchor
    while True:
        for name in targets:
            candidate = current / name
            if candidate.exists():
                return candidate
        if str(current) == root:
            break
        current = current.parent
    return None


def load_dotenv(path: str | Path = ".env") -> None:
    target = Path(path)
    if not target.exists():
        candidate = _search_upwards(Path.cwd(), [path.name if isinstance(path, (Path, str)) else path])
        if candidate:
            target = candidate
    if not target.exists():
        return
    for line in target.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
