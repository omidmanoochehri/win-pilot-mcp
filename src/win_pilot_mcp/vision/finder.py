from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from win_pilot_mcp.types import BoundingBox, ElementType, ScreenAnalysis, ScreenElement


@dataclass(slots=True)
class ElementFinder:
    def find(self, analysis: ScreenAnalysis, query: dict[str, Any]) -> ScreenElement | None:
        ranked = self.find_all(analysis, query, limit=1)
        return ranked[0] if ranked else None

    def find_all(
        self,
        analysis: ScreenAnalysis,
        query: dict[str, Any],
        limit: int = 10,
    ) -> list[ScreenElement]:
        candidates = self._prefilter(analysis.elements, query)
        enriched_query = {
            **query,
            "screenWidth": analysis.screenshot.width,
            "screenHeight": analysis.screenshot.height,
        }
        scored = [(self._score(item, enriched_query), item) for item in candidates]
        scored = [(score, item) for score, item in scored if score > 0]
        if not scored:
            return []
        scored.sort(key=lambda pair: pair[0], reverse=True)
        results = []
        for score, item in scored[:limit]:
            item.attributes["matchScore"] = round(score, 4)
            results.append(item)
        return results

    def _prefilter(
        self,
        elements: list[ScreenElement],
        query: dict[str, Any],
    ) -> list[ScreenElement]:
        candidates = elements
        if element_type := query.get("type"):
            requested = str(element_type)
            exact = [item for item in candidates if item.type.value == requested]
            if exact:
                candidates = exact
        if role := query.get("role"):
            role_text = str(role).lower()
            role_matches = [
                item
                for item in candidates
                if role_text in str(item.attributes.get("domainRole", "")).lower()
                or role_text in item.description.lower()
            ]
            if role_matches:
                candidates = role_matches
        if region := query.get("within"):
            candidates = [
                item
                for item in candidates
                if _center_within(item.bbox, region)
            ]
        return candidates

    def _score(self, element: ScreenElement, query: dict[str, Any]) -> float:
        score = 0.0
        breakdown: dict[str, float] = {}
        if text := query.get("text"):
            text_score = self._text_score(element, str(text)) * 3.0
            score += text_score
            breakdown["text"] = round(text_score, 4)
        if description := query.get("description"):
            haystack = f"{element.description} {element.text} {element.type.value}".strip()
            description_score = (
                SequenceMatcher(None, haystack.lower(), str(description).lower()).ratio() * 1.5
            )
            score += description_score
            breakdown["description"] = round(description_score, 4)
        if element_type := query.get("type"):
            if element.type.value == str(element_type):
                score += 1.5
                breakdown["type"] = 1.5
        if role := query.get("role"):
            role_score = self._role_score(element, str(role))
            score += role_score
            breakdown["role"] = round(role_score, 4)
        if position := query.get("position"):
            position_score = self._position_score(
                element.bbox,
                str(position),
                int(query.get("screenWidth", 1200)),
                int(query.get("screenHeight", 900)),
            )
            score += position_score
            breakdown["position"] = round(position_score, 4)
        if color := query.get("color"):
            color_score = self._color_score(element, str(color))
            score += color_score
            breakdown["color"] = round(color_score, 4)
        if icon := query.get("icon"):
            icon_score = self._icon_score(element, str(icon))
            score += icon_score
            breakdown["icon"] = round(icon_score, 4)
        confidence = max(0.2, element.confidence)
        final = score * confidence
        if breakdown:
            element.attributes["matchBreakdown"] = breakdown
        return final

    def _text_score(self, element: ScreenElement, text: str) -> float:
        if not element.text:
            return 0.0
        needle = _normalize_text(text)
        haystack = _normalize_text(element.text)
        if needle == haystack:
            return 1.0
        if needle in haystack:
            return 0.85
        needle_tokens = set(needle.split())
        haystack_tokens = set(haystack.split())
        if needle_tokens and needle_tokens <= haystack_tokens:
            return 0.8
        synonyms = _synonyms(needle)
        if any(alias == haystack or alias in haystack for alias in synonyms):
            return 0.78
        if not needle_tokens.intersection(haystack_tokens):
            return 0.0
        return SequenceMatcher(None, needle, haystack).ratio()

    def _role_score(self, element: ScreenElement, role: str) -> float:
        role = role.lower().strip()
        haystack = f"{element.attributes.get('domainRole', '')} {element.description} {element.type.value}".lower()
        if role in haystack:
            return 1.4
        return SequenceMatcher(None, role, haystack).ratio() * 0.6

    def _icon_score(self, element: ScreenElement, icon: str) -> float:
        haystack = f"{element.text} {element.description} {element.attributes}".lower()
        icon = icon.lower().strip()
        aliases = {
            "save": ["save", "disk", "floppy"],
            "publish": ["publish", "upload", "send"],
            "add": ["add", "plus", "+"],
            "delete": ["delete", "trash", "remove"],
            "search": ["search", "magnifier"],
        }.get(icon, [icon])
        return 1.0 if any(alias in haystack for alias in aliases) else 0.0

    def _position_score(self, bbox: BoundingBox, position: str, width: int, height: int) -> float:
        position = position.lower()
        cx, cy = bbox.center.x, bbox.center.y
        score = 0.0
        if "left" in position:
            score += max(0.0, 1.0 - cx / max(1, width))
        if "right" in position:
            score += min(1.0, cx / max(1, width))
        if "top" in position:
            score += max(0.0, 1.0 - cy / max(1, height))
        if "bottom" in position:
            score += min(1.0, cy / max(1, height))
        if "center" in position or "middle" in position:
            nx = abs(cx - width / 2) / max(1, width / 2)
            ny = abs(cy - height / 2) / max(1, height / 2)
            score += max(0.0, 1.0 - (nx + ny) / 2)
        return score

    def _color_score(self, element: ScreenElement, color: str) -> float:
        target = _parse_color(color)
        source = element.attributes.get("dominantColor", {}).get("rgb")
        if not target or not source:
            return 0.0
        distance = sum((int(source[index]) - target[index]) ** 2 for index in range(3)) ** 0.5
        return max(0.0, 1.0 - distance / 441.7)

    def find_by_template(
        self,
        screenshot_path: Path,
        template_path: Path,
        threshold: float = 0.82,
    ) -> ScreenElement | None:
        import cv2

        screenshot = cv2.imread(str(screenshot_path), cv2.IMREAD_COLOR)
        template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if screenshot is None or template is None:
            return None
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            return None
        h, w = template.shape[:2]
        return ScreenElement(
            id="template-match",
            type=ElementType.IMAGE,
            bbox=BoundingBox(max_loc[0], max_loc[1], w, h),
            confidence=float(max_val),
            source="template",
        )


def element_to_target(element: ScreenElement | dict[str, Any]) -> tuple[int, int]:
    if isinstance(element, ScreenElement):
        center = element.bbox.center
        return center.x, center.y
    bbox = element.get("bbox", element)
    x = int(bbox["x"] + bbox["width"] / 2)
    y = int(bbox["y"] + bbox["height"] / 2)
    return x, y


def _parse_color(color: str) -> tuple[int, int, int] | None:
    value = color.strip().lower()
    named = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 128, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "orange": (255, 165, 0),
        "purple": (128, 0, 128),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
    }
    if value in named:
        return named[value]
    if value.startswith("#") and len(value) == 7:
        try:
            return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
        except ValueError:
            return None
    if "," in value:
        try:
            parts = [int(part.strip()) for part in value.split(",")]
        except ValueError:
            return None
        if len(parts) == 3 and all(0 <= part <= 255 for part in parts):
            return parts[0], parts[1], parts[2]
    return None


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").strip().split())


def _synonyms(text: str) -> list[str]:
    groups = {
        "publish": ["update", "save", "post"],
        "save": ["apply", "done", "ok"],
        "add": ["new", "create", "plus"],
        "delete": ["remove", "trash"],
        "search": ["find"],
        "settings": ["preferences", "options"],
    }
    return groups.get(text, [])


def _center_within(bbox: BoundingBox, region: dict[str, Any]) -> bool:
    box = region.get("bbox", region)
    center = bbox.center
    return (
        int(box["x"]) <= center.x <= int(box["x"]) + int(box["width"])
        and int(box["y"]) <= center.y <= int(box["y"]) + int(box["height"])
    )
