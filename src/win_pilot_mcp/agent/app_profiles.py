from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AppProfile:
    key: str
    aliases: tuple[str, ...]
    landmarks: dict[str, tuple[str, ...]]
    shortcuts: dict[str, tuple[str, ...]]


COMMON_SHORTCUTS: dict[str, tuple[str, ...]] = {
    "new": ("ctrl", "n"),
    "open": ("ctrl", "o"),
    "save": ("ctrl", "s"),
    "save_as": ("f12",),
    "print": ("ctrl", "p"),
    "undo": ("ctrl", "z"),
    "redo": ("ctrl", "y"),
    "cut": ("ctrl", "x"),
    "copy": ("ctrl", "c"),
    "paste": ("ctrl", "v"),
    "select_all": ("ctrl", "a"),
    "find": ("ctrl", "f"),
    "replace": ("ctrl", "h"),
    "close": ("ctrl", "w"),
}


APP_PROFILES: dict[str, AppProfile] = {
    "word": AppProfile(
        key="word",
        aliases=("word", "microsoft word", "winword"),
        landmarks={
            "ribbon": ("home", "insert", "draw", "design", "layout", "references", "mailings", "review", "view"),
            "documentCanvas": ("page", "words", "paragraph", "document"),
            "commentsPane": ("comments", "resolve", "reply"),
            "trackChanges": ("track changes", "accept", "reject"),
            "statusBar": ("page", "words", "accessibility"),
        },
        shortcuts={
            **COMMON_SHORTCUTS,
            "bold": ("ctrl", "b"),
            "italic": ("ctrl", "i"),
            "underline": ("ctrl", "u"),
            "align_left": ("ctrl", "l"),
            "align_center": ("ctrl", "e"),
            "align_right": ("ctrl", "r"),
            "justify": ("ctrl", "j"),
            "insert_link": ("ctrl", "k"),
            "spellcheck": ("f7",),
            "word_count": ("ctrl", "shift", "g"),
        },
    ),
    "excel": AppProfile(
        key="excel",
        aliases=("excel", "microsoft excel"),
        landmarks={
            "ribbon": ("home", "insert", "page layout", "formulas", "data", "review", "view"),
            "formulaBar": ("fx", "formula"),
            "grid": ("a1", "sheet", "cell", "row", "column"),
            "sheetTabs": ("sheet1", "sheet2", "new sheet"),
            "filters": ("sort", "filter"),
        },
        shortcuts={
            **COMMON_SHORTCUTS,
            "edit_cell": ("f2",),
            "format_cells": ("ctrl", "1"),
            "autosum": ("alt", "="),
            "insert_row": ("ctrl", "shift", "+"),
            "delete_row": ("ctrl", "-"),
            "fill_down": ("ctrl", "d"),
            "fill_right": ("ctrl", "r"),
            "go_to": ("ctrl", "g"),
        },
    ),
    "powerpoint": AppProfile(
        key="powerpoint",
        aliases=("powerpoint", "microsoft powerpoint", "ppt"),
        landmarks={
            "ribbon": ("home", "insert", "design", "transitions", "animations", "slide show", "review", "view"),
            "slideCanvas": ("click to add title", "click to add subtitle", "slide"),
            "thumbnails": ("slide 1", "slide 2"),
            "notes": ("notes",),
            "presentControls": ("from beginning", "present", "slide show"),
        },
        shortcuts={
            **COMMON_SHORTCUTS,
            "new_slide": ("ctrl", "m"),
            "duplicate_slide": ("ctrl", "d"),
            "start_slideshow": ("f5",),
            "start_from_current": ("shift", "f5"),
            "group": ("ctrl", "g"),
            "ungroup": ("ctrl", "shift", "g"),
        },
    ),
    "vscode": AppProfile(
        key="vscode",
        aliases=("vscode", "visual studio code", "code"),
        landmarks={
            "activityBar": ("explorer", "search", "source control", "run", "extensions"),
            "explorer": ("open editors", "folder", "outline"),
            "editor": ("problems", "terminal", "output", "debug console"),
            "terminal": ("powershell", "cmd", "terminal"),
            "commandPalette": (">", "command palette"),
        },
        shortcuts={
            **COMMON_SHORTCUTS,
            "command_palette": ("ctrl", "shift", "p"),
            "quick_open": ("ctrl", "p"),
            "toggle_terminal": ("ctrl", "`"),
            "format_document": ("shift", "alt", "f"),
            "go_to_definition": ("f12",),
            "rename_symbol": ("f2",),
            "toggle_sidebar": ("ctrl", "b"),
            "find_in_files": ("ctrl", "shift", "f"),
            "run_build_task": ("ctrl", "shift", "b"),
        },
    ),
    "illustrator": AppProfile(
        key="illustrator",
        aliases=("illustrator", "adobe illustrator"),
        landmarks={
            "toolbar": ("selection tool", "pen", "type", "shape", "brush"),
            "artboard": ("artboard",),
            "layersPanel": ("layers",),
            "propertiesPanel": ("properties", "appearance", "transform"),
            "colorPanel": ("color", "swatches", "gradient"),
        },
        shortcuts={
            **COMMON_SHORTCUTS,
            "selection_tool": ("v",),
            "direct_selection_tool": ("a",),
            "pen_tool": ("p",),
            "type_tool": ("t",),
            "rectangle_tool": ("m",),
            "eyedropper": ("i",),
            "group": ("ctrl", "g"),
            "ungroup": ("ctrl", "shift", "g"),
            "export_for_screens": ("ctrl", "alt", "e"),
        },
    ),
    "player": AppProfile(
        key="player",
        aliases=("player", "media player", "vlc", "spotify", "youtube", "video"),
        landmarks={
            "playbackControls": ("play", "pause", "next", "previous", "volume", "mute"),
            "timeline": ("00:", "duration", "progress"),
            "playlist": ("playlist", "queue", "library"),
        },
        shortcuts={
            "play_pause": ("space",),
            "mute": ("m",),
            "fullscreen": ("f",),
            "next": ("ctrl", "right"),
            "previous": ("ctrl", "left"),
            "volume_up": ("up",),
            "volume_down": ("down",),
            "seek_forward": ("right",),
            "seek_backward": ("left",),
        },
    ),
    "settings": AppProfile(
        key="settings",
        aliases=("settings", "windows settings"),
        landmarks={
            "search": ("find a setting", "search"),
            "categories": ("system", "bluetooth", "network", "personalization", "apps", "accounts", "time", "privacy"),
            "detailsPane": ("display", "sound", "notifications", "storage", "activation"),
        },
        shortcuts={
            "open_settings": ("win", "i"),
            "search": ("ctrl", "f"),
            "back": ("alt", "left"),
            "forward": ("alt", "right"),
            "close": ("alt", "f4"),
        },
    ),
    "browser": AppProfile(
        key="browser",
        aliases=("browser", "chrome", "edge", "firefox"),
        landmarks={
            "addressBar": ("http", "www.", ".com", "localhost"),
            "tabs": ("new tab", "close tab"),
            "page": ("reload", "bookmark", "extensions"),
            "downloads": ("downloads",),
            "devtools": ("elements", "console", "network", "sources"),
        },
        shortcuts={
            **COMMON_SHORTCUTS,
            "address_bar": ("ctrl", "l"),
            "new_tab": ("ctrl", "t"),
            "reopen_tab": ("ctrl", "shift", "t"),
            "close_tab": ("ctrl", "w"),
            "next_tab": ("ctrl", "tab"),
            "previous_tab": ("ctrl", "shift", "tab"),
            "reload": ("ctrl", "r"),
            "hard_reload": ("ctrl", "shift", "r"),
            "downloads": ("ctrl", "j"),
            "devtools": ("ctrl", "shift", "i"),
        },
    ),
}


def resolve_app_profile(application: str) -> AppProfile | None:
    normalized = application.strip().lower()
    for profile in APP_PROFILES.values():
        if normalized == profile.key or normalized in profile.aliases:
            return profile
    return None


def list_app_profiles() -> list[dict[str, Any]]:
    return [
        {
            "key": profile.key,
            "aliases": list(profile.aliases),
            "landmarks": {key: list(value) for key, value in profile.landmarks.items()},
            "shortcuts": {key: list(value) for key, value in profile.shortcuts.items()},
        }
        for profile in APP_PROFILES.values()
    ]


def get_app_shortcuts(application: str) -> dict[str, list[str]]:
    profile = resolve_app_profile(application)
    if not profile:
        return {key: list(value) for key, value in COMMON_SHORTCUTS.items()}
    return {key: list(value) for key, value in profile.shortcuts.items()}
