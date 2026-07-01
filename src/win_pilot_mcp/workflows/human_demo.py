from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from win_pilot_mcp.screenshots import ScreenshotManager


class HumanDemoRecorder:
    def __init__(self, recordings_dir: Path, screenshots: ScreenshotManager) -> None:
        self.recordings_dir = recordings_dir
        self.screenshots = screenshots
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    def learn_from_user(self, name: str, duration_seconds: float = 30.0) -> dict[str, Any]:
        try:
            from pynput import keyboard, mouse
        except Exception as exc:
            return {"ok": False, "reason": f"pynput is required for human demonstration mode: {exc}"}

        events: list[dict[str, Any]] = []
        started = time.time()
        before = self.screenshots.capture_screen(f"demo_{name}_before").to_dict()

        def stamp(event_type: str, payload: dict[str, Any]) -> None:
            events.append({"dt": time.time() - started, "type": event_type, "payload": payload})

        def on_click(x: int, y: int, button, pressed: bool) -> None:
            stamp("mouse_click", {"x": x, "y": y, "button": str(button), "pressed": pressed})

        def on_move(x: int, y: int) -> None:
            if not events or events[-1]["type"] != "mouse_move" or events[-1]["dt"] < time.time() - started - 0.15:
                stamp("mouse_move", {"x": x, "y": y})

        def on_scroll(x: int, y: int, dx: int, dy: int) -> None:
            stamp("mouse_scroll", {"x": x, "y": y, "dx": dx, "dy": dy})

        def on_press(key) -> None:
            stamp("key_press", {"key": _key_name(key)})

        def on_release(key) -> None:
            stamp("key_release", {"key": _key_name(key)})

        mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
        keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        mouse_listener.start()
        keyboard_listener.start()
        try:
            time.sleep(max(0.1, duration_seconds))
        finally:
            mouse_listener.stop()
            keyboard_listener.stop()
            mouse_listener.join(timeout=2)
            keyboard_listener.join(timeout=2)

        after = self.screenshots.capture_screen(f"demo_{name}_after").to_dict()
        path = self.recordings_dir / f"human_demo_{name}_{int(time.time())}.json"
        payload = {
            "name": name,
            "kind": "human_demo",
            "started": started,
            "durationSeconds": duration_seconds,
            "before": before,
            "after": after,
            "events": events,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"ok": True, "path": str(path), "events": len(events), "before": before, "after": after}


def _key_name(key) -> str:
    char = getattr(key, "char", None)
    if char:
        return char
    return str(key).replace("Key.", "")
