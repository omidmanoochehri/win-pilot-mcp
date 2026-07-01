from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from win_pilot_mcp.logs import EventLogger


class WorkflowRecorder:
    def __init__(self, recordings_dir: Path, logger: EventLogger) -> None:
        self.recordings_dir = recordings_dir
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.active_name: str | None = None
        self.events: list[dict[str, Any]] = []

    def start(self, name: str) -> dict[str, Any]:
        self.active_name = name
        self.events = []
        self.logger.workflow("recording_started", {"name": name})
        return {"recording": True, "name": name}

    def record(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self.active_name:
            return
        self.events.append({"ts": time.time(), "type": event_type, "payload": payload})

    def stop(self) -> dict[str, Any]:
        if not self.active_name:
            return {"recording": False, "path": None, "events": 0}
        path = self.recordings_dir / f"{self.active_name}_{int(time.time())}.json"
        payload = {"name": self.active_name, "events": self.events}
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.workflow("recording_stopped", {"name": self.active_name, "path": str(path)})
        count = len(self.events)
        self.active_name = None
        self.events = []
        return {"recording": False, "path": str(path), "events": count}

    def load(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict[str, Any]]:
        workflows = []
        for path in sorted(self.recordings_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                workflows.append(
                    {
                        "path": str(path),
                        "name": payload.get("name", path.stem),
                        "kind": payload.get("kind", "workflow"),
                        "events": len(payload.get("events", [])),
                        "modified": path.stat().st_mtime,
                    }
                )
            except Exception:
                workflows.append({"path": str(path), "name": path.stem, "kind": "unknown", "events": None})
        return workflows
