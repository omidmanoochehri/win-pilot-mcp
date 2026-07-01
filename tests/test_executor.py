from win_pilot_mcp.executor.computer import ComputerExecutor
from win_pilot_mcp.permissions import PermissionManager
from win_pilot_mcp.types import ActionOptions


class DummyScreenshots:
    def __init__(self):
        self.captures = []

    def capture_screen(self, name):
        self.captures.append(name)

        class Shot:
            def to_dict(self):
                return {"path": f"{name}.png"}

        return Shot()


class DummyLogger:
    def action(self, event, payload):
        self.last = (event, payload)

    def error(self, event, payload):
        self.last_error = (event, payload)


def test_require_confirmation_does_not_execute_action():
    logger = DummyLogger()
    executor = ComputerExecutor(PermissionManager(), DummyScreenshots(), logger)
    called = False

    def action():
        nonlocal called
        called = True

    result = executor.run_action(
        "click",
        action,
        ActionOptions(require_confirmation=True, take_screenshot_after=False),
    )

    assert result["ok"] is False
    assert result["requiresConfirmation"] is True
    assert result["executed"] is False
    assert called is False


def test_low_value_action_skips_screenshots_by_default():
    screenshots = DummyScreenshots()
    executor = ComputerExecutor(PermissionManager(), screenshots, DummyLogger())

    result = executor.run_action("press_key", lambda: None, ActionOptions())

    assert result["ok"] is True
    assert result["before"] is None
    assert result["after"] is None
    assert screenshots.captures == []
    assert result["verificationReason"] == "low_value_action"


def test_uncertain_click_takes_screenshots_by_default():
    screenshots = DummyScreenshots()
    executor = ComputerExecutor(PermissionManager(), screenshots, DummyLogger())

    result = executor.run_action(
        "click",
        lambda: None,
        ActionOptions(),
        payload={
            "target": {
                "confidence": 0.4,
                "attributes": {"matchScore": 0.5},
            }
        },
    )

    assert result["ok"] is True
    assert result["before"] is not None
    assert result["after"] is not None
    assert screenshots.captures == ["before_click", "after_click"]
    assert result["verificationReason"] == "uncertain_target_or_low_confidence"


def test_explicit_screenshot_options_override_policy():
    screenshots = DummyScreenshots()
    executor = ComputerExecutor(PermissionManager(), screenshots, DummyLogger())

    result = executor.run_action(
        "press_key",
        lambda: None,
        ActionOptions(take_screenshot_before=True, take_screenshot_after=False),
    )

    assert result["before"] is not None
    assert result["after"] is None
    assert screenshots.captures == ["before_press_key"]
    assert result["verificationReason"] == "explicit_screenshot_options"
