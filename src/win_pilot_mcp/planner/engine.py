from __future__ import annotations

import time
import re
from typing import Any

from win_pilot_mcp.agent import get_app_shortcuts, list_app_profiles, resolve_app_profile
from win_pilot_mcp.executor import ComputerExecutor
from win_pilot_mcp.memory import MemoryStore
from win_pilot_mcp.types import ActionOptions, PermissionLevel
from win_pilot_mcp.vision import ElementFinder, ScreenAnalyzer


class TaskPlanner:
    def __init__(
        self,
        analyzer: ScreenAnalyzer,
        finder: ElementFinder,
        executor: ComputerExecutor,
        memory: MemoryStore,
    ) -> None:
        self.analyzer = analyzer
        self.finder = finder
        self.executor = executor
        self.memory = memory

    def execute_task(
        self,
        prompt: str,
        max_steps: int = 20,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        action_options = ActionOptions.from_dict(options)
        steps: list[dict[str, Any]] = []
        last_error: str | None = None
        repeated_errors: dict[str, int] = {}
        planned_actions = _parse_prompt_actions(prompt)

        for step_index in range(max_steps):
            analysis = self.analyzer.analyze_screen()
            next_action = self._choose_next_action(prompt, analysis.to_dict(), steps, planned_actions)
            if next_action["type"] == "done":
                return {
                    "ok": True,
                    "completed": True,
                    "steps": steps,
                    "finalObservation": analysis.to_dict(),
                }
            if next_action["type"] == "ask_user":
                return {
                    "ok": False,
                    "completed": False,
                    "needsUser": True,
                    "reason": next_action["reason"],
                    "steps": steps,
                    "lastObservation": analysis.to_dict(),
                }
            try:
                result = self._execute_single_action(next_action, action_options)
                after = self.analyzer.analyze_screen()
                verified = self._verify(next_action, analysis.to_dict(), after.to_dict())
                step = {
                    "index": step_index,
                    "plannedAction": next_action,
                    "result": result,
                    "verified": verified,
                }
                steps.append(step)
                if verified.get("changed"):
                    last_error = None
                else:
                    last_error = "No visible state change detected after action"
                    self._recover(prompt, last_error)
            except Exception as exc:
                last_error = str(exc)
                error_key = f"{next_action.get('type')}:{last_error}"
                repeated_errors[error_key] = repeated_errors.get(error_key, 0) + 1
                steps.append({"index": step_index, "plannedAction": next_action, "error": last_error})
                self._recover(prompt, last_error)
                if repeated_errors[error_key] >= 2:
                    return {
                        "ok": False,
                        "completed": False,
                        "needsUser": True,
                        "reason": "The same planned action failed twice.",
                        "lastError": last_error,
                        "failedAction": next_action,
                        "steps": steps,
                        "recovery": {
                            "strategy": "reobserve_or_rephrase_target",
                            "suggestion": "Use analyze_screen/find_elements to choose a visible target.",
                        },
                    }
                time.sleep(0.5)

        return {
            "ok": False,
            "completed": False,
            "reason": "Reached max_steps before task completion",
            "lastError": last_error,
            "steps": steps,
        }

    def plan_task(self, prompt: str) -> dict[str, Any]:
        actions = _parse_prompt_actions(prompt)
        return {
            "prompt": prompt,
            "principle": "observe -> think -> plan -> act one step -> verify -> retry",
            "steps": actions,
            "requiresPolicyLoop": len(actions) == 0,
        }

    def _choose_next_action(
        self,
        prompt: str,
        observation: dict[str, Any],
        previous_steps: list[dict[str, Any]],
        planned_actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        lowered = prompt.lower()
        if previous_steps and self._looks_complete(lowered, observation):
            return {"type": "done"}

        planned = planned_actions if planned_actions is not None else _parse_prompt_actions(prompt)
        if planned:
            if len(previous_steps) >= len(planned):
                return {"type": "done"}
            return planned[len(previous_steps)]

        if "click" in lowered:
            target_text = _after_keyword(prompt, "click")
            element = self.finder.find(
                self.analyzer.analyze_file(
                    PathLike(observation["screenshot"]["path"]).path,
                ),
                {"text": target_text, "type": "button"},
            )
            if element:
                return {"type": "click", "x": element.bbox.center.x, "y": element.bbox.center.y, "target": element.to_dict()}

        if "type" in lowered or "enter" in lowered:
            text = _quoted(prompt)
            if text:
                return {"type": "type_text", "text": text}

        return {
            "type": "ask_user",
            "reason": (
                "The built-in planner can observe and execute primitive GUI actions, but this "
                "free-form task needs a model policy to choose semantic next steps. Use MCP "
                "tools directly or connect a Codex policy loop that calls analyze_screen, "
                "find_element, and one action at a time."
            ),
        }

    def _execute_single_action(
        self, action: dict[str, Any], options: ActionOptions
    ) -> dict[str, Any]:
        if action["type"] == "click_by_text":
            analysis = self.analyzer.analyze_screen()
            element = self.finder.find(
                analysis,
                {"text": action["text"], "type": action.get("elementType", "button")},
            )
            if not element:
                raise ValueError(f"Could not find element with text: {action['text']}")
            center = element.bbox.center
            action["x"] = center.x
            action["y"] = center.y
            action["target"] = element.to_dict()
            return self.executor.run_action(
                "click",
                lambda: self.executor.mouse.click(center.x, center.y),
                options=options,
                required=PermissionLevel.STANDARD,
                payload=action,
            )
        if action["type"] == "click":
            return self.executor.run_action(
                "click",
                lambda: self.executor.mouse.click(action["x"], action["y"]),
                options=options,
                required=PermissionLevel.STANDARD,
                payload=action,
            )
        if action["type"] == "type_text":
            return self.executor.run_action(
                "type_text",
                lambda: self.executor.keyboard.type_text(action["text"]),
                options=options,
                required=PermissionLevel.STANDARD,
                payload=action,
            )
        if action["type"] == "hotkey":
            return self.executor.run_action(
                "hotkey",
                lambda: self.executor.keyboard.hotkey(*action["keys"]),
                options=options,
                required=PermissionLevel.STANDARD,
                payload=action,
            )
        if action["type"] == "press_key":
            return self.executor.run_action(
                "press_key",
                lambda: self.executor.keyboard.press_key(action["key"], action.get("presses", 1)),
                options=options,
                required=PermissionLevel.STANDARD,
                payload=action,
            )
        if action["type"] == "scroll":
            return self.executor.run_action(
                "scroll",
                lambda: self.executor.mouse.scroll(action["clicks"]),
                options=options,
                required=PermissionLevel.STANDARD,
                payload=action,
            )
        if action["type"] == "wait":
            return self.executor.run_action(
                "wait",
                lambda: time.sleep(action.get("seconds", 1.0)),
                options=options,
                required=PermissionLevel.READ_ONLY,
                payload=action,
            )
        if action["type"] == "focus_window":
            return self.executor.run_action(
                "focus_window",
                lambda: self.executor.windows.focus_window(action["title"]),
                options=options,
                required=PermissionLevel.STANDARD,
                payload=action,
            )
        if action["type"] == "app_shortcut":
            keys = action["keys"]
            return self.executor.run_action(
                "hotkey" if len(keys) > 1 else "press_key",
                lambda: self.executor.keyboard.hotkey(*keys)
                if len(keys) > 1
                else self.executor.keyboard.press_key(keys[0]),
                options=options,
                required=PermissionLevel.STANDARD,
                payload=action,
            )
        raise ValueError(f"Unsupported action type: {action['type']}")

    def _verify(
        self,
        action: dict[str, Any],
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:
        from win_pilot_mcp.vision.similarity import compare_screenshots

        diff = compare_screenshots(
            PathLike(before["screenshot"]["path"]).path,
            PathLike(after["screenshot"]["path"]).path,
        )
        return {"action": action["type"], **diff}

    def _recover(self, prompt: str, reason: str) -> None:
        self.memory.remember_workflow_result(
            "recovery",
            {"prompt": prompt, "reason": reason, "strategy": "reobserve_retry"},
        )

    def _looks_complete(self, lowered_prompt: str, observation: dict[str, Any]) -> bool:
        visible_text = " ".join(item.get("text", "") for item in observation.get("texts", []))
        if "publish" in lowered_prompt and "published" in visible_text.lower():
            return True
        if "save" in lowered_prompt and "saved" in visible_text.lower():
            return True
        return False


class PathLike:
    def __init__(self, value: str) -> None:
        from pathlib import Path

        self.path = Path(value)


def _quoted(text: str) -> str | None:
    for quote in ('"', "'"):
        if quote in text:
            parts = text.split(quote)
            if len(parts) >= 3:
                return parts[1]
    return None


def _after_keyword(text: str, keyword: str) -> str:
    lowered = text.lower()
    index = lowered.find(keyword)
    if index < 0:
        return text
    return text[index + len(keyword) :].strip().strip(".")


def _parse_prompt_actions(prompt: str) -> list[dict[str, Any]]:
    prompt = prompt.strip()
    high_level = _parse_high_level(prompt)
    if high_level:
        return high_level

    parts = re.split(r"\b(?:then|and then|,)\b|[;\n]+", prompt, flags=re.IGNORECASE)
    actions: list[dict[str, Any]] = []
    for raw in parts:
        text = raw.strip()
        lowered = text.lower()
        if not text:
            continue
        quoted = _quoted(text)
        if lowered.startswith("click ") or " click " in f" {lowered} ":
            target = quoted or _after_keyword(text, "click")
            actions.append({"type": "click_by_text", "text": target, "elementType": "button"})
        elif match := re.match(r"^(type|enter)\s+(.+?)\s+(?:into|in)\s+(.+)$", text, flags=re.IGNORECASE):
            typed = _strip_quotes(match.group(2))
            target = _strip_quotes(match.group(3))
            actions.append({"type": "click_by_text", "text": target, "elementType": "input"})
            actions.append({"type": "type_text", "text": typed})
        elif lowered.startswith("type ") or lowered.startswith("enter "):
            typed = quoted or re.sub(r"^(type|enter)\s+", "", text, flags=re.IGNORECASE)
            actions.append({"type": "type_text", "text": typed})
        elif lowered.startswith("paste "):
            typed = quoted or re.sub(r"^paste\s+", "", text, flags=re.IGNORECASE)
            actions.append({"type": "type_text", "text": typed})
        elif lowered.startswith("press "):
            key = re.sub(r"^press\s+", "", lowered).strip()
            actions.append({"type": "press_key", "key": _normalize_key(key)})
        elif lowered.startswith("hotkey "):
            keys = re.sub(r"^hotkey\s+", "", lowered).replace("+", " ").split()
            actions.append({"type": "hotkey", "keys": [_normalize_key(key) for key in keys]})
        elif lowered in {"save", "save file"}:
            actions.append({"type": "hotkey", "keys": ["ctrl", "s"]})
        elif "scroll down" in lowered:
            actions.append({"type": "scroll", "clicks": -5})
        elif "scroll up" in lowered:
            actions.append({"type": "scroll", "clicks": 5})
        elif lowered.startswith("wait"):
            seconds_match = re.search(r"(\d+(?:\.\d+)?)", lowered)
            actions.append(
                {
                    "type": "wait",
                    "seconds": float(seconds_match.group(1)) if seconds_match else 1.0,
                }
            )
    return actions


def _parse_high_level(prompt: str) -> list[dict[str, Any]]:
    lowered = prompt.lower()
    shortcut = _parse_shortcut_intent(prompt)
    if shortcut:
        return [shortcut]
    if lowered in {"open settings", "open windows settings"}:
        return [{"type": "app_shortcut", "application": "settings", "action": "open_settings", "keys": ["win", "i"]}]
    if match := re.search(r"\bopen\s+([a-z0-9 ._-]+)$", lowered):
        app = match.group(1).strip()
        return [
            {"type": "press_key", "key": "win"},
            {"type": "type_text", "text": app},
            {"type": "press_key", "key": "enter"},
            {"type": "wait", "seconds": 2.0},
            {"type": "focus_window", "title": app},
        ]
    if match := re.search(r"\bfocus\s+([a-z0-9 ._-]+)$", lowered):
        app = match.group(1).strip()
        return [{"type": "focus_window", "title": app}]
    if match := re.search(r"\b(?:go to|open url|navigate to)\s+(.+)$", prompt, flags=re.IGNORECASE):
        url = _strip_quotes(match.group(1).strip())
        return [
            {"type": "hotkey", "keys": ["ctrl", "l"]},
            {"type": "type_text", "text": url},
            {"type": "press_key", "key": "enter"},
            {"type": "wait", "seconds": 1.5},
        ]
    if match := re.search(r"\bsearch\s+(?:for\s+)?(.+)$", prompt, flags=re.IGNORECASE):
        query = _strip_quotes(match.group(1).strip())
        return [
            {"type": "hotkey", "keys": ["ctrl", "l"]},
            {"type": "type_text", "text": query},
            {"type": "press_key", "key": "enter"},
            {"type": "wait", "seconds": 1.5},
        ]
    return []


def _parse_shortcut_intent(prompt: str) -> dict[str, Any] | None:
    normalized = prompt.strip().lower()
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"^(run|use|press|do)\s+", "", normalized)
    profiles = list_app_profiles()

    in_match = re.match(r"^(.+?)\s+(?:in|on|for)\s+(.+)$", normalized)
    if in_match:
        action = in_match.group(1).strip()
        app_text = in_match.group(2).strip()
        resolved = _shortcut_for(app_text, action)
        if resolved:
            return resolved

    for profile in profiles:
        aliases = sorted(profile["aliases"], key=len, reverse=True)
        for alias in aliases:
            alias_text = str(alias).lower()
            if normalized == alias_text:
                continue
            if normalized.startswith(alias_text + " "):
                action = normalized[len(alias_text) + 1 :]
                resolved = _shortcut_for(profile["key"], action)
                if resolved:
                    return resolved
            if normalized.endswith(" " + alias_text):
                action = normalized[: -len(alias_text)].strip()
                resolved = _shortcut_for(profile["key"], action)
                if resolved:
                    return resolved
    return None


def _shortcut_for(application: str, action: str) -> dict[str, Any] | None:
    app_profile = resolve_app_profile(application)
    if not app_profile:
        return None
    action_key = action.strip().lower().replace(" ", "_")
    shortcuts = get_app_shortcuts(app_profile.key)
    keys = shortcuts.get(action_key)
    if not keys:
        return None
    return {
        "type": "app_shortcut",
        "application": app_profile.key,
        "action": action_key,
        "keys": keys,
    }


def _strip_quotes(text: str) -> str:
    return text.strip().strip('"').strip("'")


def _normalize_key(key: str) -> str:
    aliases = {
        "control": "ctrl",
        "return": "enter",
        "escape": "esc",
        "windows": "win",
    }
    return aliases.get(key.strip().lower(), key.strip().lower())
