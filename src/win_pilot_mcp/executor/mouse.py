from __future__ import annotations

import math
import random
import time
from collections.abc import Iterable

import pyautogui

from win_pilot_mcp.types import Point


class MouseController:
    def move_mouse(
        self,
        x: int,
        y: int,
        speed: float = 1.0,
        easing: str = "ease_in_out",
        randomness: float = 1.5,
    ) -> None:
        start_x, start_y = pyautogui.position()
        distance = math.dist((start_x, start_y), (x, y))
        duration = max(0.08, min(2.5, distance / 900 / max(0.1, speed)))
        steps = max(8, int(duration * 60))
        control_x = (start_x + x) / 2 + random.uniform(-80, 80)
        control_y = (start_y + y) / 2 + random.uniform(-80, 80)
        for step in range(1, steps + 1):
            t = step / steps
            eased = self._ease(t, easing)
            px = (1 - eased) ** 2 * start_x + 2 * (1 - eased) * eased * control_x + eased**2 * x
            py = (1 - eased) ** 2 * start_y + 2 * (1 - eased) * eased * control_y + eased**2 * y
            px += random.uniform(-randomness, randomness)
            py += random.uniform(-randomness, randomness)
            pyautogui.moveTo(int(px), int(py), duration=0)
            time.sleep(duration / steps)
        pyautogui.moveTo(x, y, duration=0)

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        if x is not None and y is not None:
            self.move_mouse(x, y)
        pyautogui.click(button=button)

    def double_click(self, x: int | None = None, y: int | None = None) -> None:
        if x is not None and y is not None:
            self.move_mouse(x, y)
        pyautogui.doubleClick()

    def right_click(self, x: int | None = None, y: int | None = None) -> None:
        self.click(x, y, button="right")

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        if x is not None and y is not None:
            self.move_mouse(x, y)
        pyautogui.scroll(clicks)

    def drag(self, start: Point, end: Point, duration: float = 0.7, button: str = "left") -> None:
        self.move_mouse(start.x, start.y)
        pyautogui.dragTo(end.x, end.y, duration=duration, button=button)

    def drag_and_drop(self, start: Point, end: Point, duration: float = 0.8) -> None:
        self.drag(start, end, duration=duration)

    def draw_path(self, points: Iterable[Point], duration_per_segment: float = 0.05) -> None:
        points = list(points)
        if not points:
            return
        self.move_mouse(points[0].x, points[0].y)
        pyautogui.mouseDown()
        try:
            for point in points[1:]:
                pyautogui.moveTo(point.x, point.y, duration=duration_per_segment)
        finally:
            pyautogui.mouseUp()

    def _ease(self, t: float, easing: str) -> float:
        if easing == "linear":
            return t
        if easing == "ease_out":
            return 1 - (1 - t) * (1 - t)
        if easing == "ease_in":
            return t * t
        return t * t * (3 - 2 * t)
