from win_pilot_mcp.types import ActionOptions, PermissionLevel


def test_action_options_accepts_camel_case_payload():
    options = ActionOptions.from_dict(
        {
            "dryRun": True,
            "requireConfirmation": True,
            "takeScreenshotBefore": False,
            "takeScreenshotAfter": False,
            "permission": "full_control",
        }
    )

    assert options.dry_run is True
    assert options.require_confirmation is True
    assert options.take_screenshot_before is False
    assert options.take_screenshot_after is False
    assert options.verification_mode == "auto"
    assert options.permission == PermissionLevel.FULL_CONTROL


def test_action_options_defaults_to_auto_screenshot_policy():
    options = ActionOptions.from_dict(None)

    assert options.take_screenshot_before is None
    assert options.take_screenshot_after is None
    assert options.verification_mode == "auto"
