from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PermissionLevel(str, Enum):
    READ_ONLY = "read_only"
    STANDARD = "standard"
    FULL_CONTROL = "full_control"
    DANGEROUS = "dangerous"


class ElementType(str, Enum):
    UNKNOWN = "unknown"
    BUTTON = "button"
    TEXT = "text"
    INPUT = "input"
    ICON = "icon"
    TOOLBAR = "toolbar"
    MENU = "menu"
    TAB = "tab"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DIALOG = "dialog"
    IMAGE = "image"
    CANVAS = "canvas"
    LOADING = "loading"
    CONTEXT_MENU = "context_menu"
    NOTIFICATION = "notification"
    FILE_PICKER = "file_picker"
    SCROLLABLE = "scrollable"
    REGION = "region"
    ADDRESS_BAR = "address_bar"
    WORDPRESS_EDITOR = "wordpress_editor"
    ELEMENTOR_WIDGET = "elementor_widget"
    PHOTOSHOP_PANEL = "photoshop_panel"


@dataclass(slots=True)
class Point:
    x: int
    y: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(slots=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Point:
        return Point(self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(slots=True)
class ScreenElement:
    id: str
    type: ElementType
    bbox: BoundingBox
    text: str = ""
    description: str = ""
    confidence: float = 0.0
    source: str = "vision"
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        return data


@dataclass(slots=True)
class Screenshot:
    path: Path
    width: int
    height: int
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "width": self.width,
            "height": self.height,
            "timestamp": self.timestamp,
        }


@dataclass(slots=True)
class ScreenAnalysis:
    screenshot: Screenshot
    elements: list[ScreenElement] = field(default_factory=list)
    buttons: list[ScreenElement] = field(default_factory=list)
    texts: list[ScreenElement] = field(default_factory=list)
    inputs: list[ScreenElement] = field(default_factory=list)
    icons: list[ScreenElement] = field(default_factory=list)
    toolbars: list[ScreenElement] = field(default_factory=list)
    menus: list[ScreenElement] = field(default_factory=list)
    tabs: list[ScreenElement] = field(default_factory=list)
    dropdowns: list[ScreenElement] = field(default_factory=list)
    checkboxes: list[ScreenElement] = field(default_factory=list)
    radios: list[ScreenElement] = field(default_factory=list)
    regions: list[ScreenElement] = field(default_factory=list)
    scrollables: list[ScreenElement] = field(default_factory=list)
    dialogs: list[ScreenElement] = field(default_factory=list)
    images: list[ScreenElement] = field(default_factory=list)
    canvas_areas: list[ScreenElement] = field(default_factory=list)
    loading_indicators: list[ScreenElement] = field(default_factory=list)
    context_menus: list[ScreenElement] = field(default_factory=list)
    notifications: list[ScreenElement] = field(default_factory=list)
    file_pickers: list[ScreenElement] = field(default_factory=list)
    selected_element: ScreenElement | None = None
    desktop_model: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "screenshot": self.screenshot.to_dict(),
            "elements": [item.to_dict() for item in self.elements],
            "buttons": [item.to_dict() for item in self.buttons],
            "texts": [item.to_dict() for item in self.texts],
            "inputs": [item.to_dict() for item in self.inputs],
            "icons": [item.to_dict() for item in self.icons],
            "toolbars": [item.to_dict() for item in self.toolbars],
            "menus": [item.to_dict() for item in self.menus],
            "tabs": [item.to_dict() for item in self.tabs],
            "dropdowns": [item.to_dict() for item in self.dropdowns],
            "checkboxes": [item.to_dict() for item in self.checkboxes],
            "radioButtons": [item.to_dict() for item in self.radios],
            "regions": [item.to_dict() for item in self.regions],
            "scrollables": [item.to_dict() for item in self.scrollables],
            "dialogs": [item.to_dict() for item in self.dialogs],
            "images": [item.to_dict() for item in self.images],
            "canvasAreas": [item.to_dict() for item in self.canvas_areas],
            "loadingIndicators": [item.to_dict() for item in self.loading_indicators],
            "contextMenus": [item.to_dict() for item in self.context_menus],
            "notifications": [item.to_dict() for item in self.notifications],
            "filePickers": [item.to_dict() for item in self.file_pickers],
            "selectedElement": self.selected_element.to_dict() if self.selected_element else None,
            "desktopModel": self.desktop_model,
        }


@dataclass(slots=True)
class ActionOptions:
    dry_run: bool = False
    require_confirmation: bool = False
    take_screenshot_before: bool | None = None
    take_screenshot_after: bool | None = None
    verification_mode: str = "auto"
    permission: PermissionLevel = PermissionLevel.STANDARD

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ActionOptions":
        data = data or {}
        permission = data.get("permission", PermissionLevel.STANDARD.value)
        return cls(
            dry_run=bool(data.get("dryRun", data.get("dry_run", False))),
            require_confirmation=bool(
                data.get("requireConfirmation", data.get("require_confirmation", False))
            ),
            take_screenshot_before=_optional_bool(
                data,
                "takeScreenshotBefore",
                "take_screenshot_before",
            ),
            take_screenshot_after=_optional_bool(
                data,
                "takeScreenshotAfter",
                "take_screenshot_after",
            ),
            verification_mode=str(
                data.get("verificationMode", data.get("verification_mode", "auto"))
            ),
            permission=PermissionLevel(permission),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dryRun": self.dry_run,
            "requireConfirmation": self.require_confirmation,
            "takeScreenshotBefore": self.take_screenshot_before,
            "takeScreenshotAfter": self.take_screenshot_after,
            "verificationMode": self.verification_mode,
            "permission": self.permission.value,
        }


def _optional_bool(data: dict[str, Any], camel_key: str, snake_key: str) -> bool | None:
    if camel_key in data:
        return bool(data[camel_key])
    if snake_key in data:
        return bool(data[snake_key])
    return None
