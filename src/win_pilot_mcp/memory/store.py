from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = self._load()

    def remember_element(self, key: str, element: dict[str, Any]) -> None:
        self.data.setdefault("elements", {})[key] = {"ts": time.time(), "element": element}
        self.save()

    def get_element(self, key: str) -> dict[str, Any] | None:
        item = self.data.get("elements", {}).get(key)
        return item.get("element") if item else None

    def remember_workflow_result(self, name: str, payload: dict[str, Any]) -> None:
        self.data.setdefault("workflowResults", {}).setdefault(name, []).append(
            {"ts": time.time(), **payload}
        )
        self.save()

    def set_preference(self, key: str, value: Any) -> None:
        self.data.setdefault("preferences", {})[key] = value
        self.save()

    def snapshot(self) -> dict[str, Any]:
        return self.data

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, ensure_ascii=False)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"elements": {}, "workflowResults": {}, "preferences": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"elements": {}, "workflowResults": {}, "preferences": {}}
