from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec


@dataclass(slots=True)
class VisionProviderStatus:
    name: str
    installed: bool
    enabled: bool
    purpose: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "installed": self.installed,
            "enabled": self.enabled,
            "purpose": self.purpose,
        }


class VisionProviderRegistry:
    def __init__(self) -> None:
        self.providers = {
            "tesseract": ("pytesseract", "OCR"),
            "paddleocr": ("paddleocr", "OCR"),
            "yolo": ("ultralytics", "object_detection"),
            "opencv": ("cv2", "image_similarity_and_ui_primitives"),
            "omniparser": ("omniparser", "screen_parsing_extension"),
            "florence2": ("transformers", "captioning_and_grounding_extension"),
            "grounding_dino": ("groundingdino", "open_vocabulary_detection_extension"),
        }

    def status(self) -> list[dict[str, object]]:
        rows = []
        for name, (module, purpose) in self.providers.items():
            installed = find_spec(module) is not None
            rows.append(
                VisionProviderStatus(
                    name=name,
                    installed=installed,
                    enabled=installed and name in {"tesseract", "paddleocr", "opencv"},
                    purpose=purpose,
                ).to_dict()
            )
        return rows
