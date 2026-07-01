from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from win_pilot_mcp.types import BoundingBox, ElementType, ScreenElement
from win_pilot_mcp.vision.ocr import load_cv_image


class UiPrimitiveDetector:
    def detect(self, image_path: Path, text_elements: list[ScreenElement]) -> list[ScreenElement]:
        image = load_cv_image(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 160)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        elements: list[ScreenElement] = []
        height, width = gray.shape[:2]
        for index, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            if w < 10 or h < 8 or w > width * 0.98 or h > height * 0.98:
                continue
            area = cv2.contourArea(contour)
            rect_area = max(1, w * h)
            rectangularity = area / rect_area
            bbox = BoundingBox(int(x), int(y), int(w), int(h))
            element_type = self._classify_box(bbox, rectangularity, text_elements, image.shape)
            if element_type == ElementType.UNKNOWN:
                continue
            elements.append(
                ScreenElement(
                    id=f"shape-{index}",
                    type=element_type,
                    bbox=bbox,
                    confidence=min(0.95, max(0.25, rectangularity)),
                    source="opencv",
                    attributes={"rectangularity": rectangularity},
                )
            )

        elements.extend(self._detect_loading(gray))
        elements.extend(self._detect_scrollbars(gray))
        elements.extend(self._detect_dialogs(gray, text_elements))
        elements.extend(self._detect_visual_regions(gray, text_elements))
        return self._dedupe(elements)

    def _classify_box(
        self,
        bbox: BoundingBox,
        rectangularity: float,
        text_elements: list[ScreenElement],
        image_shape: tuple[int, int, int],
    ) -> ElementType:
        height, width = image_shape[:2]
        has_text = any(_overlap_ratio(bbox, text.bbox) > 0.15 for text in text_elements)
        aspect = bbox.width / max(1, bbox.height)
        if 0.45 <= rectangularity <= 1.25 and has_text and 1.2 <= aspect <= 8:
            return ElementType.BUTTON
        if 0.45 <= rectangularity <= 1.25 and has_text and 0.8 <= aspect <= 3.5 and bbox.y < image_shape[0] * 0.18:
            return ElementType.TAB
        if 0.45 <= rectangularity <= 1.25 and bbox.height >= 18 and aspect >= 2.2:
            return ElementType.INPUT
        if bbox.width <= 28 and bbox.height <= 28 and 0.55 <= aspect <= 1.45:
            return ElementType.CHECKBOX
        if bbox.width <= 30 and bbox.height <= 30 and 0.7 <= aspect <= 1.3 and rectangularity < 0.45:
            return ElementType.RADIO
        if 12 <= bbox.width <= 48 and 12 <= bbox.height <= 48 and not has_text:
            return ElementType.ICON
        if bbox.width > width * 0.28 and bbox.height > height * 0.18:
            return ElementType.REGION
        if bbox.height < 60 and bbox.width > width * 0.35:
            return ElementType.TOOLBAR
        return ElementType.UNKNOWN

    def _detect_loading(self, gray: np.ndarray) -> list[ScreenElement]:
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=30,
            param1=80,
            param2=28,
            minRadius=6,
            maxRadius=36,
        )
        if circles is None:
            return []
        elements: list[ScreenElement] = []
        for index, circle in enumerate(np.round(circles[0, :]).astype("int")):
            x, y, radius = circle
            elements.append(
                ScreenElement(
                    id=f"loading-{index}",
                    type=ElementType.LOADING,
                    bbox=BoundingBox(int(x - radius), int(y - radius), int(radius * 2), int(radius * 2)),
                    confidence=0.45,
                    source="opencv",
                )
            )
        return elements

    def _detect_scrollbars(self, gray: np.ndarray) -> list[ScreenElement]:
        height, width = gray.shape[:2]
        elements: list[ScreenElement] = []
        vertical = gray[:, max(0, width - 40) : width]
        if vertical.size:
            edges = cv2.Canny(vertical, 80, 180)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for index, contour in enumerate(contours):
                x, y, w, h = cv2.boundingRect(contour)
                if h > height * 0.12 and 4 <= w <= 28:
                    elements.append(
                        ScreenElement(
                            id=f"scrollable-right-{index}",
                            type=ElementType.SCROLLABLE,
                            bbox=BoundingBox(width - 40 + x, y, w, h),
                            confidence=0.55,
                            source="opencv",
                            description="vertical scrollable region indicator",
                        )
                    )
        horizontal = gray[max(0, height - 40) : height, :]
        if horizontal.size:
            edges = cv2.Canny(horizontal, 80, 180)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for index, contour in enumerate(contours):
                x, y, w, h = cv2.boundingRect(contour)
                if w > width * 0.12 and 4 <= h <= 28:
                    elements.append(
                        ScreenElement(
                            id=f"scrollable-bottom-{index}",
                            type=ElementType.SCROLLABLE,
                            bbox=BoundingBox(x, height - 40 + y, w, h),
                            confidence=0.55,
                            source="opencv",
                            description="horizontal scrollable region indicator",
                        )
                    )
        return elements

    def _detect_dialogs(
        self,
        gray: np.ndarray,
        text_elements: list[ScreenElement],
    ) -> list[ScreenElement]:
        height, width = gray.shape[:2]
        dialog_words = {"ok", "cancel", "yes", "no", "open", "save", "file name", "browse"}
        dialog_texts = [
            item
            for item in text_elements
            if any(word in item.text.lower() for word in dialog_words)
        ]
        if len(dialog_texts) < 2:
            return []
        xs = [item.bbox.x for item in dialog_texts]
        ys = [item.bbox.y for item in dialog_texts]
        rights = [item.bbox.x + item.bbox.width for item in dialog_texts]
        bottoms = [item.bbox.y + item.bbox.height for item in dialog_texts]
        x1 = max(0, min(xs) - 80)
        y1 = max(0, min(ys) - 100)
        x2 = min(width, max(rights) + 80)
        y2 = min(height, max(bottoms) + 80)
        box_width = x2 - x1
        box_height = y2 - y1
        if box_width < width * 0.18 or box_height < height * 0.12:
            return []
        return [
            ScreenElement(
                id="dialog-candidate-1",
                type=ElementType.DIALOG,
                bbox=BoundingBox(x1, y1, box_width, box_height),
                confidence=0.45,
                source="semantic",
                description="possible dialog or file picker",
            )
        ]

    def _detect_visual_regions(
        self,
        gray: np.ndarray,
        text_elements: list[ScreenElement],
    ) -> list[ScreenElement]:
        height, width = gray.shape[:2]
        elements: list[ScreenElement] = []
        text_blob = " ".join(item.text.lower() for item in text_elements)

        if any(term in text_blob for term in ("layers", "properties", "adjustments", "history")):
            elements.append(
                ScreenElement(
                    id="photoshop-panel-candidate",
                    type=ElementType.PHOTOSHOP_PANEL,
                    bbox=BoundingBox(int(width * 0.72), 0, int(width * 0.28), height),
                    confidence=0.45,
                    source="semantic",
                    description="possible Photoshop side panels such as Layers or Properties",
                    attributes={"domainRole": "photoshop_panel"},
                )
            )

        if any(term in text_blob for term in ("elementor", "widgets", "navigator", "publish")):
            elements.extend(
                [
                    ScreenElement(
                        id="elementor-sidebar-candidate",
                        type=ElementType.REGION,
                        bbox=BoundingBox(0, 0, int(width * 0.28), height),
                        confidence=0.5,
                        source="semantic",
                        description="possible Elementor left sidebar or widgets panel",
                        attributes={"domainRole": "elementor_left_sidebar"},
                    ),
                    ScreenElement(
                        id="elementor-canvas-candidate",
                        type=ElementType.CANVAS,
                        bbox=BoundingBox(int(width * 0.28), 0, int(width * 0.72), height),
                        confidence=0.45,
                        source="semantic",
                        description="possible Elementor page canvas",
                        attributes={"domainRole": "elementor_canvas"},
                    ),
                ]
            )

        if any(term in text_blob for term in ("wordpress", "wp-admin", "edit page", "block", "permalink")):
            elements.append(
                ScreenElement(
                    id="wordpress-editor-candidate",
                    type=ElementType.WORDPRESS_EDITOR,
                    bbox=BoundingBox(0, int(height * 0.08), width, int(height * 0.92)),
                    confidence=0.42,
                    source="semantic",
                    description="possible WordPress editor",
                    attributes={"domainRole": "wordpress_editor"},
                )
            )

        if any(term in text_blob for term in ("http", "www.", ".com", "localhost")):
            top_inputs = [
                item
                for item in text_elements
                if item.bbox.y < height * 0.18 and item.bbox.width > width * 0.2
            ]
            for index, item in enumerate(top_inputs[:2]):
                elements.append(
                    ScreenElement(
                        id=f"browser-address-bar-candidate-{index}",
                        type=ElementType.ADDRESS_BAR,
                        bbox=BoundingBox(
                            max(0, item.bbox.x - 24),
                            max(0, item.bbox.y - 8),
                            min(width - item.bbox.x, item.bbox.width + 48),
                            item.bbox.height + 16,
                        ),
                        text=item.text,
                        confidence=0.45,
                        source="semantic",
                        description="possible browser address bar",
                        attributes={"domainRole": "browser_address_bar"},
                    )
                )

        bright_regions = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(bright_regions, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for index, contour in enumerate(contours[:80]):
            x, y, w, h = cv2.boundingRect(contour)
            if w > width * 0.25 and h > height * 0.2:
                elements.append(
                    ScreenElement(
                        id=f"canvas-candidate-{index}",
                        type=ElementType.CANVAS,
                        bbox=BoundingBox(x, y, w, h),
                        confidence=0.3,
                        source="opencv",
                        description="large blank or image-editing canvas candidate",
                    )
                )

        return elements

    def _dedupe(self, elements: list[ScreenElement]) -> list[ScreenElement]:
        kept: list[ScreenElement] = []
        for element in sorted(elements, key=lambda item: item.bbox.area, reverse=True):
            if any(_overlap_ratio(element.bbox, other.bbox) > 0.8 for other in kept):
                continue
            kept.append(element)
        return list(reversed(kept))


def infer_semantic_elements(
    text_elements: list[ScreenElement],
    primitive_elements: list[ScreenElement],
) -> list[ScreenElement]:
    elements = [*text_elements, *primitive_elements]
    lowered = [(item, item.text.lower()) for item in text_elements]
    semantic: list[ScreenElement] = []
    button_words = {
        "ok",
        "cancel",
        "save",
        "publish",
        "update",
        "submit",
        "next",
        "back",
        "add",
        "export",
        "open",
        "new",
        "delete",
    }
    menu_words = {"file", "edit", "view", "window", "help", "filter", "select", "image", "layer"}
    dropdown_words = {"select", "choose", "dropdown", "menu"}
    notification_words = {"success", "saved", "published", "error", "warning", "failed", "complete"}
    widget_words = {"heading", "image", "text editor", "button", "container", "section", "spacer"}
    for index, (text, lower) in enumerate(lowered):
        if any(word == lower or word in lower.split() for word in button_words):
            semantic.append(
                ScreenElement(
                    id=f"semantic-button-{index}",
                    type=ElementType.BUTTON,
                    bbox=_inflate(text.bbox, 12, 8),
                    text=text.text,
                    description=f"{text.text} button",
                    confidence=min(0.9, text.confidence + 0.15),
                    source="semantic",
                )
            )
        if lower in menu_words:
            semantic.append(
                ScreenElement(
                    id=f"semantic-menu-{index}",
                    type=ElementType.MENU,
                    bbox=_inflate(text.bbox, 10, 6),
                    text=text.text,
                    description=f"{text.text} menu",
                    confidence=min(0.85, text.confidence + 0.1),
                    source="semantic",
                )
            )
        if any(word in lower for word in dropdown_words):
            semantic.append(
                ScreenElement(
                    id=f"semantic-dropdown-{index}",
                    type=ElementType.DROPDOWN,
                    bbox=_inflate(text.bbox, 16, 8),
                    text=text.text,
                    description="possible dropdown",
                    confidence=min(0.75, text.confidence + 0.05),
                    source="semantic",
                )
            )
        if any(word in lower for word in notification_words):
            semantic.append(
                ScreenElement(
                    id=f"semantic-notification-{index}",
                    type=ElementType.NOTIFICATION,
                    bbox=_inflate(text.bbox, 80, 30),
                    text=text.text,
                    description="possible notification or toast",
                    confidence=min(0.75, text.confidence + 0.05),
                    source="semantic",
                )
            )
        if any(word == lower or word in lower for word in widget_words):
            semantic.append(
                ScreenElement(
                    id=f"semantic-elementor-widget-{index}",
                    type=ElementType.ELEMENTOR_WIDGET,
                    bbox=_inflate(text.bbox, 18, 14),
                    text=text.text,
                    description="possible Elementor widget",
                    confidence=min(0.8, text.confidence + 0.08),
                    source="semantic",
                    attributes={"domainRole": "elementor_widget"},
                )
            )
        if "loading" in lower or "please wait" in lower:
            semantic.append(
                ScreenElement(
                    id=f"semantic-loading-{index}",
                    type=ElementType.LOADING,
                    bbox=_inflate(text.bbox, 12, 8),
                    text=text.text,
                    confidence=text.confidence,
                    source="semantic",
                )
            )
        if "file name" in lower or "save as" in lower or "open file" in lower:
            semantic.append(
                ScreenElement(
                    id=f"semantic-file-picker-{index}",
                    type=ElementType.FILE_PICKER,
                    bbox=_inflate(text.bbox, 120, 80),
                    text=text.text,
                    description="possible file picker dialog",
                    confidence=min(0.8, text.confidence + 0.1),
                    source="semantic",
                )
            )
    elements.extend(semantic)
    return elements


def _inflate(bbox: BoundingBox, dx: int, dy: int) -> BoundingBox:
    return BoundingBox(
        x=max(0, bbox.x - dx),
        y=max(0, bbox.y - dy),
        width=bbox.width + dx * 2,
        height=bbox.height + dy * 2,
    )


def _overlap_ratio(a: BoundingBox, b: BoundingBox) -> float:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.width, b.x + b.width)
    y2 = min(a.y + a.height, b.y + b.height)
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    return intersection / max(1, min(a.area, b.area))
