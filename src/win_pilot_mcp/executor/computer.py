from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from win_pilot_mcp.logs import EventLogger
from win_pilot_mcp.permissions import PermissionManager
from win_pilot_mcp.screenshots import ScreenshotManager
from win_pilot_mcp.types import ActionOptions, PermissionLevel

from .keyboard import KeyboardController
from .mouse import MouseController
from .windows import WindowManager


class ComputerExecutor:
    def __init__(
        self,
        permissions: PermissionManager,
        screenshots: ScreenshotManager,
        logger: EventLogger,
        action_delay: float = 0.15,
    ) -> None:
        self.permissions = permissions
        self.screenshots = screenshots
        self.logger = logger
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.windows = WindowManager()
        self.action_delay = action_delay

    def run_action(
        self,
        name: str,
        func: Callable[[], Any],
        options: ActionOptions | None = None,
        required: PermissionLevel = PermissionLevel.STANDARD,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        options = options or ActionOptions()
        payload = payload or {}
        self.permissions.require(required, name)
        before_enabled, after_enabled, verification_reason = self._resolve_verification_policy(
            name,
            options,
            required,
            payload,
        )
        before = None
        after = None
        if before_enabled:
            before = self.screenshots.capture_screen(f"before_{name}").to_dict()
        if options.dry_run:
            self.logger.action(
                "dry_run",
                {"action": name, "payload": payload, "verificationReason": verification_reason},
            )
            return {"ok": True, "dryRun": True, "before": before, "after": after}
        if options.require_confirmation:
            record = {
                "action": name,
                "payload": payload,
                "before": before,
                "after": after,
                "requiresConfirmation": True,
                "executed": False,
                "message": (
                    "Action was not executed because requireConfirmation=true. "
                    "Re-run the same action with requireConfirmation=false after approval."
                ),
            }
            self.logger.action("confirmation_required", record)
            return {"ok": False, **record}

        try:
            result = func()
            time.sleep(self.action_delay)
            if after_enabled:
                after = self.screenshots.capture_screen(f"after_{name}").to_dict()
            state_change = self._compare_before_after(before, after)
            record = {
                "action": name,
                "payload": payload,
                "before": before,
                "after": after,
                "stateChange": state_change,
                "verificationReason": verification_reason,
                "result": result,
            }
            self.logger.action("completed", record)
            return {"ok": True, **record}
        except Exception as exc:
            self.logger.error("action_failed", {"action": name, "payload": payload, "error": str(exc)})
            raise

    def _resolve_verification_policy(
        self,
        name: str,
        options: ActionOptions,
        required: PermissionLevel,
        payload: dict[str, Any],
    ) -> tuple[bool, bool, str]:
        mode = options.verification_mode.lower().strip()
        if options.take_screenshot_before is not None or options.take_screenshot_after is not None:
            before = bool(options.take_screenshot_before)
            after = bool(options.take_screenshot_after)
            return before, after, "explicit_screenshot_options"
        if mode in {"off", "none", "never"}:
            return False, False, "verification_disabled"
        if mode in {"always", "screenshots", "strict"}:
            return True, True, f"verification_mode_{mode}"

        low_value_actions = {
            "move_mouse",
            "scroll",
            "press_key",
            "hotkey",
            "hold_key",
            "select_all",
            "focus_window",
            "wait",
        }
        high_value_actions = {
            "click",
            "double_click",
            "right_click",
            "drag",
            "drag_and_drop",
            "draw_path",
            "type_text",
            "paste_text",
            "move_window",
            "resize_window",
            "maximize_window",
            "minimize_window",
            "close_window",
        }
        uncertain = self._payload_is_uncertain(payload)
        if required in {PermissionLevel.FULL_CONTROL, PermissionLevel.DANGEROUS}:
            return True, True, f"permission_{required.value}"
        if uncertain:
            return True, True, "uncertain_target_or_low_confidence"
        if name in low_value_actions:
            return False, False, "low_value_action"
        if name in high_value_actions:
            return True, True, "state_changing_action"
        return False, False, "default_no_screenshot"

    def _payload_is_uncertain(self, payload: dict[str, Any]) -> bool:
        target = payload.get("target") or {}
        if target:
            confidence = float(target.get("confidence", 1.0) or 0.0)
            match_score = float(target.get("attributes", {}).get("matchScore", 1.0) or 0.0)
            if confidence < 0.55 or match_score < 0.75:
                return True
        query = payload.get("query")
        if query and not target:
            return True
        if payload.get("uncertain") is True:
            return True
        return False

    def _compare_before_after(
        self,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not before or not after:
            return None
        try:
            from win_pilot_mcp.vision.similarity import compare_screenshots

            return compare_screenshots(Path(before["path"]), Path(after["path"]))
        except Exception as exc:
            return {"changed": None, "error": str(exc)}
