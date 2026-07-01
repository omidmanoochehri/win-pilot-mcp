from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .types import PermissionLevel


@dataclass(slots=True)
class Settings:
    runtime_dir: Path
    screenshots_dir: Path
    logs_dir: Path
    recordings_dir: Path
    memory_path: Path
    permission_level: PermissionLevel = PermissionLevel.STANDARD
    tesseract_cmd: str | None = None
    screenshot_retention: int = 500
    default_wait_timeout: float = 15.0
    action_delay: float = 0.15

    @classmethod
    def from_env(cls) -> "Settings":
        runtime_dir = Path(os.getenv("WIN_PILOT_RUNTIME_DIR", "runtime")).resolve()
        permission = PermissionLevel(
            os.getenv("WIN_PILOT_PERMISSION", PermissionLevel.STANDARD.value)
        )
        return cls(
            runtime_dir=runtime_dir,
            screenshots_dir=runtime_dir / "screenshots",
            logs_dir=runtime_dir / "logs",
            recordings_dir=runtime_dir / "recordings",
            memory_path=runtime_dir / "memory.json",
            permission_level=permission,
            tesseract_cmd=os.getenv("TESSERACT_CMD"),
        )

    def ensure_dirs(self) -> None:
        for path in (
            self.runtime_dir,
            self.screenshots_dir,
            self.logs_dir,
            self.recordings_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_dirs()
    return settings
