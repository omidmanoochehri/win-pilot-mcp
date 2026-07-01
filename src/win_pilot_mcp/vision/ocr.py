from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from win_pilot_mcp.types import BoundingBox, ElementType, ScreenElement


class OcrEngine:
    def __init__(self, tesseract_cmd: str | None = None) -> None:
        self.tesseract_cmd = tesseract_cmd
        self._paddle = None

    def read(self, image_path: Path) -> list[ScreenElement]:
        elements = self._read_with_tesseract(image_path)
        if elements:
            return elements
        return self._read_with_paddle(image_path)

    def _read_with_tesseract(self, image_path: Path) -> list[ScreenElement]:
        try:
            import pytesseract

            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            image = Image.open(image_path)
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        except Exception:
            return []

        elements: list[ScreenElement] = []
        for index, text in enumerate(data.get("text", [])):
            clean = (text or "").strip()
            try:
                confidence = float(data["conf"][index]) / 100.0
            except (ValueError, KeyError):
                confidence = 0.0
            if not clean or confidence < 0.2:
                continue
            bbox = BoundingBox(
                x=int(data["left"][index]),
                y=int(data["top"][index]),
                width=int(data["width"][index]),
                height=int(data["height"][index]),
            )
            elements.append(
                ScreenElement(
                    id=f"ocr-{index}",
                    type=ElementType.TEXT,
                    bbox=bbox,
                    text=clean,
                    confidence=confidence,
                    source="tesseract",
                )
            )
        return self._merge_nearby_words(elements)

    def _read_with_paddle(self, image_path: Path) -> list[ScreenElement]:
        try:
            if self._paddle is None:
                from paddleocr import PaddleOCR

                self._paddle = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            result = self._paddle.ocr(str(image_path), cls=True)
        except Exception:
            return []

        elements: list[ScreenElement] = []
        rows = result[0] if result else []
        for index, row in enumerate(rows):
            points, payload = row
            text, confidence = payload
            xs = [int(point[0]) for point in points]
            ys = [int(point[1]) for point in points]
            bbox = BoundingBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            elements.append(
                ScreenElement(
                    id=f"paddle-{index}",
                    type=ElementType.TEXT,
                    bbox=bbox,
                    text=str(text).strip(),
                    confidence=float(confidence),
                    source="paddleocr",
                )
            )
        return elements

    def _merge_nearby_words(self, words: list[ScreenElement]) -> list[ScreenElement]:
        if not words:
            return []
        rows: list[list[ScreenElement]] = []
        for word in sorted(words, key=lambda item: (item.bbox.y, item.bbox.x)):
            placed = False
            for row in rows:
                row_y = sum(item.bbox.y for item in row) / len(row)
                row_h = max(item.bbox.height for item in row)
                if abs(word.bbox.y - row_y) <= max(8, row_h * 0.7):
                    row.append(word)
                    placed = True
                    break
            if not placed:
                rows.append([word])

        merged: list[ScreenElement] = []
        counter = 0
        for row in rows:
            row = sorted(row, key=lambda item: item.bbox.x)
            group: list[ScreenElement] = []
            previous: ScreenElement | None = None
            for word in row:
                gap = word.bbox.x - (previous.bbox.x + previous.bbox.width) if previous else 0
                if previous and gap > max(18, previous.bbox.height * 1.5):
                    merged.append(self._merge_group(group, counter))
                    counter += 1
                    group = []
                group.append(word)
                previous = word
            if group:
                merged.append(self._merge_group(group, counter))
                counter += 1
        return merged

    def _merge_group(self, group: list[ScreenElement], index: int) -> ScreenElement:
        xs = [item.bbox.x for item in group]
        ys = [item.bbox.y for item in group]
        rights = [item.bbox.x + item.bbox.width for item in group]
        bottoms = [item.bbox.y + item.bbox.height for item in group]
        text = " ".join(item.text for item in group).strip()
        confidence = float(np.mean([item.confidence for item in group]))
        return ScreenElement(
            id=f"text-{index}",
            type=ElementType.TEXT,
            bbox=BoundingBox(min(xs), min(ys), max(rights) - min(xs), max(bottoms) - min(ys)),
            text=text,
            confidence=confidence,
            source="ocr",
        )


def load_cv_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image
