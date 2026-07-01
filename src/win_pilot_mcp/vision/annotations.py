from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from win_pilot_mcp.types import ScreenAnalysis


def create_annotated_screenshot(analysis: ScreenAnalysis, output_path: Path) -> Path:
    image = Image.open(analysis.screenshot.path).convert("RGB")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()

    colors = {
        "button": "#2E7D32",
        "input": "#1565C0",
        "text": "#6A1B9A",
        "dialog": "#C62828",
        "region": "#EF6C00",
        "loading": "#00838F",
    }
    for element in analysis.elements:
        color = colors.get(element.type.value, "#455A64")
        box = element.bbox
        draw.rectangle(
            (box.x, box.y, box.x + box.width, box.y + box.height),
            outline=color,
            width=2,
        )
        label = f"{element.id} {element.text or element.type.value}".strip()
        label = label[:80]
        text_box = draw.textbbox((box.x, max(0, box.y - 16)), label, font=font)
        draw.rectangle(text_box, fill=color)
        draw.text((box.x, max(0, box.y - 16)), label, fill="white", font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
