from __future__ import annotations

import time
from pathlib import Path

from PIL import Image

from win_pilot_mcp.logs import EventLogger
from win_pilot_mcp.types import BoundingBox, Screenshot


class ScreenshotManager:
    def __init__(self, screenshots_dir: Path, logger: EventLogger, retention: int = 500) -> None:
        self.screenshots_dir = screenshots_dir
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.retention = retention
        self._save_count = 0

    def capture_screen(self, name: str = "screen") -> Screenshot:
        image = self._grab_screen()
        return self._save(image, name)

    def capture_region(self, bbox: BoundingBox, name: str = "region") -> Screenshot:
        image = self._grab_screen()
        region = image.crop((bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height))
        return self._save(region, name)

    def capture_window(self, bbox: BoundingBox, name: str = "window") -> Screenshot:
        return self.capture_region(bbox, name)

    def _grab_screen(self) -> Image.Image:
        try:
            import pyautogui

            return pyautogui.screenshot()
        except Exception:
            import mss

            with mss.mss() as sct:
                monitor = sct.monitors[0]
                raw = sct.grab(monitor)
                return Image.frombytes("RGB", raw.size, raw.rgb)

    def _save(self, image: Image.Image, name: str) -> Screenshot:
        ts = time.time()
        path = self.screenshots_dir / f"{name}_{int(ts * 1000)}.png"
        image.save(path)
        screenshot = Screenshot(path=path, width=image.width, height=image.height, timestamp=ts)
        self.logger.screenshot("captured", screenshot.to_dict())
        self._save_count += 1
        if self.retention > 0 and self._save_count % 25 == 0:
            self._prune_old_screenshots()
        return screenshot

    def _prune_old_screenshots(self) -> None:
        files = sorted(
            self.screenshots_dir.glob("*.png"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for old_file in files[self.retention :]:
            try:
                old_file.unlink()
            except OSError:
                pass
