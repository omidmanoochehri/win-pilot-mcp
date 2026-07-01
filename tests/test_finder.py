from win_pilot_mcp.types import BoundingBox, ElementType, ScreenAnalysis, ScreenElement, Screenshot
from win_pilot_mcp.vision.finder import ElementFinder


def test_find_element_prefers_exact_text_and_type(tmp_path):
    screenshot = Screenshot(tmp_path / "screen.png", 100, 100, 0)
    save = ScreenElement(
        id="button-1",
        type=ElementType.BUTTON,
        bbox=BoundingBox(10, 10, 80, 30),
        text="Save",
        confidence=0.95,
    )
    cancel = ScreenElement(
        id="button-2",
        type=ElementType.BUTTON,
        bbox=BoundingBox(10, 50, 80, 30),
        text="Cancel",
        confidence=0.95,
    )
    analysis = ScreenAnalysis(screenshot=screenshot, elements=[cancel, save])

    found = ElementFinder().find(analysis, {"text": "Save", "type": "button"})

    assert found is save
    assert found.attributes["matchScore"] > 0


def test_find_element_uses_synonyms_and_returns_ranked_alternatives(tmp_path):
    screenshot = Screenshot(tmp_path / "screen.png", 200, 100, 0)
    update = ScreenElement(
        id="button-1",
        type=ElementType.BUTTON,
        bbox=BoundingBox(10, 10, 80, 30),
        text="Update",
        confidence=0.9,
    )
    unrelated = ScreenElement(
        id="button-2",
        type=ElementType.BUTTON,
        bbox=BoundingBox(100, 10, 80, 30),
        text="Settings",
        confidence=0.9,
    )
    analysis = ScreenAnalysis(screenshot=screenshot, elements=[unrelated, update])

    found = ElementFinder().find(analysis, {"text": "Publish", "type": "button"})

    assert found is update
    assert "matchBreakdown" in found.attributes


def test_find_element_can_prefilter_within_region(tmp_path):
    screenshot = Screenshot(tmp_path / "screen.png", 300, 200, 0)
    left = ScreenElement(
        id="button-1",
        type=ElementType.BUTTON,
        bbox=BoundingBox(10, 10, 80, 30),
        text="Save",
        confidence=0.9,
    )
    right = ScreenElement(
        id="button-2",
        type=ElementType.BUTTON,
        bbox=BoundingBox(210, 10, 80, 30),
        text="Save",
        confidence=0.9,
    )
    analysis = ScreenAnalysis(screenshot=screenshot, elements=[left, right])

    found = ElementFinder().find(
        analysis,
        {"text": "Save", "type": "button", "within": {"x": 200, "y": 0, "width": 100, "height": 100}},
    )

    assert found is right
