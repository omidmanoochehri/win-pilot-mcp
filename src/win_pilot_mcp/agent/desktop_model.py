from __future__ import annotations

from win_pilot_mcp.types import ElementType, ScreenElement


class DesktopModelBuilder:
    def build(self, elements: list[ScreenElement], active_window: dict[str, object] | None) -> dict[str, object]:
        model: dict[str, object] = {
            "desktop": {
                "activeWindow": active_window,
                "regions": [],
            }
        }
        regions = [item for item in elements if item.type in {ElementType.REGION, ElementType.DIALOG}]
        for region in sorted(regions, key=lambda item: (item.bbox.y, item.bbox.x)):
            children = [
                child.to_dict()
                for child in elements
                if child.id != region.id and _contains(region, child)
            ]
            model["desktop"]["regions"].append(
                {
                    "id": region.id,
                    "type": region.type.value,
                    "bbox": region.bbox.to_dict(),
                    "description": _describe_region(children),
                    "children": children[:80],
                }
            )
        return model


def _contains(parent: ScreenElement, child: ScreenElement) -> bool:
    return (
        parent.bbox.x <= child.bbox.center.x <= parent.bbox.x + parent.bbox.width
        and parent.bbox.y <= child.bbox.center.y <= parent.bbox.y + parent.bbox.height
    )


def _describe_region(children: list[dict[str, object]]) -> str:
    text = " ".join(str(child.get("text", "")) for child in children if child.get("text"))
    lowered = text.lower()
    if "elementor" in lowered or "widgets" in lowered:
        return "possible Elementor workspace"
    if "layers" in lowered or "properties" in lowered:
        return "possible design/editor panel"
    if "file name" in lowered or "open" in lowered and "cancel" in lowered:
        return "possible file picker dialog"
    if "publish" in lowered:
        return "possible publishing/editor interface"
    return "screen region"
