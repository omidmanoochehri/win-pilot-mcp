from __future__ import annotations

import time
from pathlib import Path

import cv2

from win_pilot_mcp.agent import DesktopModelBuilder
from win_pilot_mcp.executor.windows import WindowManager
from win_pilot_mcp.screenshots import ScreenshotManager
from win_pilot_mcp.types import ElementType, ScreenAnalysis, ScreenElement

from .detectors import UiPrimitiveDetector, infer_semantic_elements
from .ocr import OcrEngine


class ScreenAnalyzer:
    def __init__(
        self,
        screenshots: ScreenshotManager,
        ocr: OcrEngine,
        windows: WindowManager,
    ) -> None:
        self.screenshots = screenshots
        self.ocr = ocr
        self.detector = UiPrimitiveDetector()
        self.windows = windows
        self.model_builder = DesktopModelBuilder()
        self.cache_enabled = True
        self.cache_ttl_seconds = 0.75
        self.cache_change_threshold = 0.001
        self._last_analysis: ScreenAnalysis | None = None
        self._last_analyzed_at = 0.0
        self.metrics: dict[str, float | int] = {
            "analyzeCalls": 0,
            "cacheHits": 0,
            "cacheMisses": 0,
            "totalAnalyzeSeconds": 0.0,
            "lastAnalyzeSeconds": 0.0,
        }

    def configure_cache(
        self,
        enabled: bool | None = None,
        ttl_seconds: float | None = None,
        change_threshold: float | None = None,
    ) -> None:
        if enabled is not None:
            self.cache_enabled = enabled
        if ttl_seconds is not None:
            self.cache_ttl_seconds = max(0.0, ttl_seconds)
        if change_threshold is not None:
            self.cache_change_threshold = max(0.0, change_threshold)

    def clear_cache(self) -> None:
        self._last_analysis = None
        self._last_analyzed_at = 0.0

    def get_metrics(self) -> dict[str, float | int | bool]:
        return {
            **self.metrics,
            "cacheEnabled": self.cache_enabled,
            "cacheTtlSeconds": self.cache_ttl_seconds,
            "cacheChangeThreshold": self.cache_change_threshold,
        }

    def analyze_screen(self, force: bool = False) -> ScreenAnalysis:
        started = time.perf_counter()
        self.metrics["analyzeCalls"] = int(self.metrics["analyzeCalls"]) + 1
        screenshot = self.screenshots.capture_screen("observe")
        if self._can_reuse_cached_analysis(screenshot.path, force):
            self.metrics["cacheHits"] = int(self.metrics["cacheHits"]) + 1
            assert self._last_analysis is not None
            return self._last_analysis
        self.metrics["cacheMisses"] = int(self.metrics["cacheMisses"]) + 1
        analysis = self.analyze_file(screenshot.path, screenshot)
        self._last_analysis = analysis
        self._last_analyzed_at = time.time()
        elapsed = time.perf_counter() - started
        self.metrics["lastAnalyzeSeconds"] = elapsed
        self.metrics["totalAnalyzeSeconds"] = float(self.metrics["totalAnalyzeSeconds"]) + elapsed
        return analysis

    def analyze_file(self, path: Path, screenshot=None) -> ScreenAnalysis:
        if screenshot is None:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(path)
            from time import time
            from win_pilot_mcp.types import Screenshot

            screenshot = Screenshot(path=path, width=image.shape[1], height=image.shape[0], timestamp=time())

        texts = self.ocr.read(path)
        primitives = self.detector.detect(path, texts)
        elements = infer_semantic_elements(texts, primitives)
        elements = self._normalize_ids(self._merge_related(elements))
        self._attach_color_metadata(path, elements)
        active_window = self.windows.get_active_window()
        model = self.model_builder.build(elements, active_window)
        return ScreenAnalysis(
            screenshot=screenshot,
            elements=elements,
            buttons=[item for item in elements if item.type == ElementType.BUTTON],
            texts=[item for item in elements if item.type == ElementType.TEXT],
            inputs=[item for item in elements if item.type == ElementType.INPUT],
            icons=[item for item in elements if item.type == ElementType.ICON],
            toolbars=[item for item in elements if item.type == ElementType.TOOLBAR],
            menus=[item for item in elements if item.type == ElementType.MENU],
            tabs=[item for item in elements if item.type == ElementType.TAB],
            dropdowns=[item for item in elements if item.type == ElementType.DROPDOWN],
            checkboxes=[item for item in elements if item.type == ElementType.CHECKBOX],
            radios=[item for item in elements if item.type == ElementType.RADIO],
            regions=[item for item in elements if item.type == ElementType.REGION],
            scrollables=[item for item in elements if item.type == ElementType.SCROLLABLE],
            dialogs=[
                item
                for item in elements
                if item.type in {ElementType.DIALOG, ElementType.FILE_PICKER}
            ],
            images=[item for item in elements if item.type == ElementType.IMAGE],
            canvas_areas=[item for item in elements if item.type == ElementType.CANVAS],
            loading_indicators=[item for item in elements if item.type == ElementType.LOADING],
            context_menus=[item for item in elements if item.type == ElementType.CONTEXT_MENU],
            notifications=[item for item in elements if item.type == ElementType.NOTIFICATION],
            file_pickers=[item for item in elements if item.type == ElementType.FILE_PICKER],
            selected_element=self._detect_selected(elements),
            desktop_model=model,
        )

    def analyze_application(self, application: str) -> dict[str, object]:
        analysis = self.analyze_screen()
        app = application.strip().lower()
        elements = analysis.elements
        if app == "photoshop":
            return {
                "application": "photoshop",
                "screenshot": analysis.screenshot.to_dict(),
                "toolbar": _by_role_or_type(elements, "photoshop_toolbar", ElementType.TOOLBAR),
                "layersPanel": _by_text_or_role(elements, ["layers"], "photoshop_panel"),
                "propertiesPanel": _by_text_or_role(elements, ["properties"], "photoshop_panel"),
                "colorPicker": _by_text_or_role(elements, ["color picker", "color"], None),
                "exportDialog": _by_text_or_role(elements, ["export", "save as"], None),
                "selectionTools": _by_text_or_role(elements, ["select", "lasso", "magic wand"], None),
                "textTool": _by_text_or_role(elements, ["text", "type"], None),
                "moveTool": _by_text_or_role(elements, ["move"], None),
                "canvas": [item.to_dict() for item in analysis.canvas_areas],
                "selectedLayer": _infer_selected_layer(elements),
                "activeTool": _infer_active_tool(elements),
                "documentSize": _infer_document_size(analysis),
            }
        if app == "elementor":
            return {
                "application": "elementor",
                "screenshot": analysis.screenshot.to_dict(),
                "widgetPanel": _by_text_or_role(elements, ["widgets", "elements"], "elementor_left_sidebar"),
                "canvas": [item.to_dict() for item in analysis.canvas_areas],
                "navigator": _by_text_or_role(elements, ["navigator"], None),
                "publishButton": _by_text_or_role(elements, ["publish", "update"], None),
                "responsiveMode": _by_text_or_role(elements, ["responsive", "desktop", "tablet", "mobile"], None),
                "containers": _by_text_or_role(elements, ["container"], None),
                "sections": _by_text_or_role(elements, ["section"], None),
                "columns": _by_text_or_role(elements, ["column"], None),
                "dragHandles": _by_text_or_role(elements, ["drag"], None),
                "contextMenus": [item.to_dict() for item in analysis.context_menus],
                "widgets": [
                    item.to_dict()
                    for item in elements
                    if item.type == ElementType.ELEMENTOR_WIDGET
                ],
            }
        if app in {"browser", "chrome", "edge", "firefox"}:
            return {
                "application": app,
                "screenshot": analysis.screenshot.to_dict(),
                "addressBars": [
                    item.to_dict()
                    for item in elements
                    if item.type == ElementType.ADDRESS_BAR
                ],
                "tabs": [item.to_dict() for item in analysis.tabs],
                "pageCanvas": [item.to_dict() for item in analysis.canvas_areas],
                "dialogs": [item.to_dict() for item in analysis.dialogs],
                "notifications": [item.to_dict() for item in analysis.notifications],
            }
        return {
            "application": application,
            "screenshot": analysis.screenshot.to_dict(),
            "desktopModel": analysis.desktop_model,
            "elements": [item.to_dict() for item in analysis.elements],
        }

    def _merge_related(self, elements: list[ScreenElement]) -> list[ScreenElement]:
        for element in elements:
            if element.type in {ElementType.BUTTON, ElementType.INPUT} and not element.text:
                inside = [
                    other
                    for other in elements
                    if other.type == ElementType.TEXT and _center_inside(other, element)
                ]
                if inside:
                    element.text = " ".join(item.text for item in inside)
        return elements

    def _normalize_ids(self, elements: list[ScreenElement]) -> list[ScreenElement]:
        counters: dict[str, int] = {}
        for element in elements:
            prefix = element.type.value
            counters[prefix] = counters.get(prefix, 0) + 1
            element.id = f"{prefix}-{counters[prefix]}"
        return elements

    def _detect_selected(self, elements: list[ScreenElement]) -> ScreenElement | None:
        selected = [
            item
            for item in elements
            if item.attributes.get("selected") or "selected" in item.description.lower()
        ]
        return selected[0] if selected else None

    def _attach_color_metadata(self, path: Path, elements: list[ScreenElement]) -> None:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            return
        height, width = image.shape[:2]
        for element in elements:
            x1 = max(0, min(width, element.bbox.x))
            y1 = max(0, min(height, element.bbox.y))
            x2 = max(0, min(width, element.bbox.x + element.bbox.width))
            y2 = max(0, min(height, element.bbox.y + element.bbox.height))
            if x2 <= x1 or y2 <= y1:
                continue
            crop = image[y1:y2, x1:x2]
            mean_bgr = crop.reshape(-1, 3).mean(axis=0)
            rgb = [int(mean_bgr[2]), int(mean_bgr[1]), int(mean_bgr[0])]
            element.attributes["dominantColor"] = {
                "rgb": rgb,
                "hex": f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
            }

    def _can_reuse_cached_analysis(self, screenshot_path: Path, force: bool) -> bool:
        if force or not self.cache_enabled or self._last_analysis is None:
            return False
        age = time.time() - self._last_analyzed_at
        if age <= self.cache_ttl_seconds:
            return True
        try:
            from win_pilot_mcp.vision.similarity import compare_screenshots

            diff = compare_screenshots(self._last_analysis.screenshot.path, screenshot_path)
            return float(diff["changeRatio"]) <= self.cache_change_threshold
        except Exception:
            return False


def _center_inside(child: ScreenElement, parent: ScreenElement) -> bool:
    center = child.bbox.center
    return (
        parent.bbox.x <= center.x <= parent.bbox.x + parent.bbox.width
        and parent.bbox.y <= center.y <= parent.bbox.y + parent.bbox.height
    )


def _by_role_or_type(
    elements: list[ScreenElement],
    role: str,
    element_type: ElementType,
) -> list[dict[str, object]]:
    return [
        item.to_dict()
        for item in elements
        if item.attributes.get("domainRole") == role or item.type == element_type
    ]


def _by_text_or_role(
    elements: list[ScreenElement],
    needles: list[str],
    role: str | None,
) -> list[dict[str, object]]:
    result = []
    for item in elements:
        text = f"{item.text} {item.description}".lower()
        if role and item.attributes.get("domainRole") == role:
            result.append(item.to_dict())
        elif any(needle in text for needle in needles):
            result.append(item.to_dict())
    return result


def _infer_selected_layer(elements: list[ScreenElement]) -> dict[str, object] | None:
    candidates = _by_text_or_role(elements, ["selected", "layer"], "photoshop_panel")
    return candidates[0] if candidates else None


def _infer_active_tool(elements: list[ScreenElement]) -> dict[str, object] | None:
    candidates = _by_text_or_role(elements, ["move", "brush", "text", "select", "crop"], None)
    return candidates[0] if candidates else None


def _infer_document_size(analysis: ScreenAnalysis) -> dict[str, int] | None:
    if not analysis.canvas_areas:
        return None
    canvas = max(analysis.canvas_areas, key=lambda item: item.bbox.area)
    return {"width": canvas.bbox.width, "height": canvas.bbox.height}
