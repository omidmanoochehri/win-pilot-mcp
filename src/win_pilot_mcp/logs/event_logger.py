from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class EventLogger:
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def action(self, event: str, payload: dict[str, Any]) -> None:
        self._write("actions.log", event, payload)

    def screenshot(self, event: str, payload: dict[str, Any]) -> None:
        self._write("screenshots.log", event, payload)

    def error(self, event: str, payload: dict[str, Any]) -> None:
        self._write("errors.log", event, payload)

    def workflow(self, event: str, payload: dict[str, Any]) -> None:
        self._write("workflows.log", event, payload)

    def read(self, name: str, limit: int = 100) -> list[dict[str, Any]]:
        allowed = {
            "actions": "actions.log",
            "screenshots": "screenshots.log",
            "errors": "errors.log",
            "workflows": "workflows.log",
        }
        path = self.logs_dir / allowed.get(name, name)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        records = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"raw": line})
        return records

    def _write(self, filename: str, event: str, payload: dict[str, Any]) -> None:
        record = {"ts": time.time(), "event": event, "payload": payload}
        with (self.logs_dir / filename).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
