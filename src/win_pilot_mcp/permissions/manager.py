from __future__ import annotations

from dataclasses import dataclass

from win_pilot_mcp.types import PermissionLevel


_ORDER = {
    PermissionLevel.READ_ONLY: 0,
    PermissionLevel.STANDARD: 1,
    PermissionLevel.FULL_CONTROL: 2,
    PermissionLevel.DANGEROUS: 3,
}


@dataclass(slots=True)
class PermissionManager:
    current_level: PermissionLevel = PermissionLevel.STANDARD

    def set_level(self, level: PermissionLevel | str) -> None:
        self.current_level = PermissionLevel(level)

    def require(self, required: PermissionLevel | str, action: str) -> None:
        required_level = PermissionLevel(required)
        if _ORDER[self.current_level] < _ORDER[required_level]:
            raise PermissionError(
                f"Action '{action}' requires {required_level.value}, "
                f"current level is {self.current_level.value}"
            )

    def snapshot(self) -> dict[str, str]:
        return {"currentLevel": self.current_level.value}
