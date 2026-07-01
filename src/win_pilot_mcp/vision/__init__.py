from __future__ import annotations

from typing import Any

__all__ = ["ScreenAnalyzer", "ElementFinder", "compare_screenshots"]


def __getattr__(name: str) -> Any:
    if name == "ScreenAnalyzer":
        from .analyzer import ScreenAnalyzer

        return ScreenAnalyzer
    if name == "ElementFinder":
        from .finder import ElementFinder

        return ElementFinder
    if name == "compare_screenshots":
        from .similarity import compare_screenshots

        return compare_screenshots
    raise AttributeError(name)
