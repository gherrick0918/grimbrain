from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path


class NDJSONWriter:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = path.open("a", encoding="utf-8")

    def write(self, obj: dict | object) -> None:
        if is_dataclass(obj):
            obj = asdict(obj)
        obj = {"ts": datetime.utcnow().isoformat() + "Z", **obj}
        self._fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._fp.flush()

    def close(self) -> None:
        self._fp.close()
