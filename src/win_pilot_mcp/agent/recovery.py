from __future__ import annotations

from typing import Any


class RecoveryEngine:
    def analyze(self, observation: dict[str, Any]) -> dict[str, Any]:
        texts = " ".join(item.get("text", "") for item in observation.get("texts", [])).lower()
        loading = observation.get("loadingIndicators", [])
        dialogs = observation.get("dialogs", [])
        notifications = observation.get("notifications", [])

        if loading:
            return {
                "state": "loading",
                "recommendedAction": "wait_until_disappears",
                "query": {"type": "loading"},
                "reason": "Loading indicator is visible.",
            }
        if dialogs:
            return {
                "state": "dialog",
                "recommendedAction": "inspect_dialog",
                "reason": "A dialog or file picker appears to be blocking the workspace.",
                "dialogs": dialogs,
            }
        if any(term in texts for term in ("crash", "not responding", "has stopped working")):
            return {
                "state": "application_crash",
                "recommendedAction": "ask_user",
                "reason": "The visible text suggests the application crashed or is not responding.",
            }
        if any(term in texts for term in ("error", "failed", "denied", "invalid")):
            return {
                "state": "error_message",
                "recommendedAction": "read_error_and_retry",
                "reason": "An error message is visible.",
                "notifications": notifications,
            }
        if any(term in texts for term in ("sign in", "login", "password", "authentication")):
            return {
                "state": "auth_required",
                "recommendedAction": "ask_user",
                "reason": "Credentials or authentication appear to be required.",
            }
        return {
            "state": "unknown",
            "recommendedAction": "reobserve",
            "reason": "No specific recovery pattern matched.",
        }
