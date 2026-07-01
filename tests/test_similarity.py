from PIL import Image, ImageDraw

from win_pilot_mcp.vision.similarity import compare_screenshots


def test_compare_screenshots_reports_changed_region(tmp_path):
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"
    Image.new("RGB", (100, 100), "white").save(before)
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 40, 40), fill="black")
    image.save(after)

    result = compare_screenshots(before, after)

    assert result["changed"] is True
    assert result["changeRatio"] > 0
    assert result["regions"]
