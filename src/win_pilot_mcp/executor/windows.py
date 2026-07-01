from __future__ import annotations

from typing import Any


class WindowManager:
    def list_windows(self) -> list[dict[str, Any]]:
        try:
            import pygetwindow as gw

            return [self._window_to_dict(window) for window in gw.getAllWindows() if window.title]
        except Exception:
            return []

    def get_active_window(self) -> dict[str, Any] | None:
        try:
            import pygetwindow as gw

            window = gw.getActiveWindow()
            return self._window_to_dict(window) if window else None
        except Exception:
            return None

    def focus_window(self, title: str) -> bool:
        window = self._find_window(title)
        if not window:
            return False
        window.activate()
        return True

    def move_window(self, title: str, x: int, y: int) -> bool:
        window = self._find_window(title)
        if not window:
            return False
        window.moveTo(x, y)
        return True

    def resize_window(self, title: str, width: int, height: int) -> bool:
        window = self._find_window(title)
        if not window:
            return False
        window.resizeTo(width, height)
        return True

    def maximize_window(self, title: str) -> bool:
        window = self._find_window(title)
        if not window:
            return False
        window.maximize()
        return True

    def minimize_window(self, title: str) -> bool:
        window = self._find_window(title)
        if not window:
            return False
        window.minimize()
        return True

    def close_window(self, title: str) -> bool:
        window = self._find_window(title)
        if not window:
            return False
        window.close()
        return True

    def _find_window(self, title: str):
        try:
            import pygetwindow as gw

            matches = gw.getWindowsWithTitle(title)
            return matches[0] if matches else None
        except Exception:
            return None

    def _window_to_dict(self, window) -> dict[str, Any]:
        return {
            "title": window.title,
            "left": window.left,
            "top": window.top,
            "width": window.width,
            "height": window.height,
            "isActive": getattr(window, "isActive", False),
            "isMaximized": getattr(window, "isMaximized", False),
            "isMinimized": getattr(window, "isMinimized", False),
        }
