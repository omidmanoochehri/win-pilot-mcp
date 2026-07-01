from __future__ import annotations

import random
import time

import pyautogui


class KeyboardController:
    def type_text(self, text: str, interval: float = 0.03, corrections: bool = False) -> None:
        for char in text:
            pyautogui.write(char)
            time.sleep(max(0.0, random.gauss(interval, interval / 3 if interval else 0.0)))
        if corrections:
            time.sleep(0.1)

    def hotkey(self, *keys: str) -> None:
        pyautogui.hotkey(*keys)

    def press_key(self, key: str, presses: int = 1, interval: float = 0.03) -> None:
        pyautogui.press(key, presses=presses, interval=interval)

    def hold_key(self, key: str, seconds: float) -> None:
        pyautogui.keyDown(key)
        try:
            time.sleep(seconds)
        finally:
            pyautogui.keyUp(key)

    def paste_text(self, text: str) -> None:
        try:
            import pyperclip

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            self.type_text(text, interval=0.01)

    def select_all(self) -> None:
        pyautogui.hotkey("ctrl", "a")
