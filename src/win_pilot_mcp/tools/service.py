from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from win_pilot_mcp.config import Settings, load_settings
from win_pilot_mcp.agent import RecoveryEngine
from win_pilot_mcp.executor import ComputerExecutor, WindowManager
from win_pilot_mcp.logs import EventLogger
from win_pilot_mcp.memory import MemoryStore
from win_pilot_mcp.permissions import PermissionManager
from win_pilot_mcp.planner import TaskPlanner
from win_pilot_mcp.screenshots import ScreenshotManager
from win_pilot_mcp.types import ActionOptions, BoundingBox, PermissionLevel, Point
from win_pilot_mcp.vision import ElementFinder, ScreenAnalyzer, compare_screenshots
from win_pilot_mcp.vision.annotations import create_annotated_screenshot
from win_pilot_mcp.vision.ocr import OcrEngine
from win_pilot_mcp.vision.providers import VisionProviderRegistry
from win_pilot_mcp.workflows import HumanDemoRecorder, WorkflowRecorder


class WinPilotService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.logger = EventLogger(self.settings.logs_dir)
        self.permissions = PermissionManager(self.settings.permission_level)
        self.screenshots = ScreenshotManager(
            self.settings.screenshots_dir,
            self.logger,
            retention=self.settings.screenshot_retention,
        )
        self.windows = WindowManager()
        self.ocr = OcrEngine(self.settings.tesseract_cmd)
        self.analyzer = ScreenAnalyzer(self.screenshots, self.ocr, self.windows)
        self.finder = ElementFinder()
        self.executor = ComputerExecutor(
            self.permissions,
            self.screenshots,
            self.logger,
            action_delay=self.settings.action_delay,
        )
        self.memory = MemoryStore(self.settings.memory_path)
        self.workflows = WorkflowRecorder(self.settings.recordings_dir, self.logger)
        self.human_demo = HumanDemoRecorder(self.settings.recordings_dir, self.screenshots)
        self.planner = TaskPlanner(self.analyzer, self.finder, self.executor, self.memory)
        self.recovery = RecoveryEngine()
        self.vision_providers = VisionProviderRegistry()

    def analyze_screen(self, force: bool = False) -> dict[str, Any]:
        return self.analyzer.analyze_screen(force=force).to_dict()

    def configure_optimization(
        self,
        cache_enabled: bool | None = None,
        cache_ttl_seconds: float | None = None,
        cache_change_threshold: float | None = None,
        action_delay: float | None = None,
    ) -> dict[str, Any]:
        self.analyzer.configure_cache(cache_enabled, cache_ttl_seconds, cache_change_threshold)
        if action_delay is not None:
            self.executor.action_delay = max(0.0, action_delay)
        return self.get_performance_stats()

    def clear_observation_cache(self) -> dict[str, Any]:
        self.analyzer.clear_cache()
        return {"ok": True}

    def get_performance_stats(self) -> dict[str, Any]:
        return {
            "analyzer": self.analyzer.get_metrics(),
            "executor": {"actionDelay": self.executor.action_delay},
        }

    def analyze_application(self, application: str) -> dict[str, Any]:
        return self.analyzer.analyze_application(application)

    def get_desktop_model(self) -> dict[str, Any]:
        return self.analyzer.analyze_screen().desktop_model

    def get_vision_providers(self) -> list[dict[str, object]]:
        return self.vision_providers.status()

    def detect_objects(
        self,
        provider: str = "opencv",
        image_path: str | None = None,
        prompt: str | None = None,
        model_path: str | None = None,
    ) -> dict[str, Any]:
        provider = provider.lower()
        screenshot = None
        if image_path:
            path = Path(image_path)
        else:
            screenshot = self.screenshots.capture_screen("detect_objects")
            path = screenshot.path

        if provider == "opencv":
            analysis = self.analyzer.analyze_file(path, screenshot)
            return {
                "ok": True,
                "provider": "opencv",
                "objects": [item.to_dict() for item in analysis.elements],
            }

        if provider == "yolo":
            try:
                from ultralytics import YOLO
            except Exception as exc:
                return {"ok": False, "provider": provider, "reason": f"ultralytics is not available: {exc}"}
            if not model_path:
                return {"ok": False, "provider": provider, "reason": "model_path is required for YOLO"}
            model = YOLO(model_path)
            results = model(str(path))
            objects = []
            for result in results:
                for index, box in enumerate(result.boxes):
                    xyxy = box.xyxy[0].tolist()
                    objects.append(
                        {
                            "id": f"yolo-{index}",
                            "bbox": {
                                "x": int(xyxy[0]),
                                "y": int(xyxy[1]),
                                "width": int(xyxy[2] - xyxy[0]),
                                "height": int(xyxy[3] - xyxy[1]),
                            },
                            "confidence": float(box.conf[0]),
                            "class": int(box.cls[0]),
                        }
                    )
            return {"ok": True, "provider": provider, "objects": objects}

        return {
            "ok": False,
            "provider": provider,
            "prompt": prompt,
            "reason": (
                "Provider hook exists but no local runtime adapter is configured. "
                "Install/configure the provider package and model, then call detect_objects again."
            ),
        }

    def get_canvas_state(self) -> dict[str, Any]:
        analysis = self.analyzer.analyze_screen()
        largest = max(analysis.canvas_areas, key=lambda item: item.bbox.area, default=None)
        return {
            "canvasAreas": [item.to_dict() for item in analysis.canvas_areas],
            "activeCanvas": largest.to_dict() if largest else None,
            "selectedElement": analysis.selected_element.to_dict() if analysis.selected_element else None,
            "documentSize": (
                {"width": largest.bbox.width, "height": largest.bbox.height} if largest else None
            ),
        }

    def get_photoshop_state(self) -> dict[str, Any]:
        return self.analyzer.analyze_application("photoshop")

    def get_elementor_state(self) -> dict[str, Any]:
        return self.analyzer.analyze_application("elementor")

    def get_browser_state(self) -> dict[str, Any]:
        return self.analyzer.analyze_application("browser")

    def recover_from_unexpected_state(self) -> dict[str, Any]:
        observation = self.analyze_screen()
        recovery = self.recovery.analyze(observation)
        self.logger.action("recovery_analysis", recovery)
        return {"observation": observation, "recovery": recovery}

    def decide_next_action(self, prompt: str) -> dict[str, Any]:
        observation = self.analyze_screen()
        recovery = self.recovery.analyze(observation)
        plan = self.planner.plan_task(prompt)
        next_step = plan["steps"][0] if plan.get("steps") else None
        candidates = []
        if next_step and next_step.get("type") == "click_by_text":
            candidates = [
                item.to_dict()
                for item in self.finder.find_all(
                    self.analyzer.analyze_screen(),
                    {
                        "text": next_step["text"],
                        "type": next_step.get("elementType", "button"),
                    },
                    limit=5,
                )
            ]
        return {
            "prompt": prompt,
            "recovery": recovery,
            "plan": plan,
            "nextStep": next_step,
            "targetCandidates": candidates,
            "performance": self.get_performance_stats(),
        }

    def find_element(self, query: dict[str, Any]) -> dict[str, Any]:
        analysis = self.analyzer.analyze_screen()
        element = self._resolve_element(analysis, query)
        key = query.get("rememberAs")
        if element and key:
            self.memory.remember_element(str(key), element.to_dict())
        alternatives = self.finder.find_all(analysis, query, limit=int(query.get("alternatives", 5)))
        return {
            "found": element is not None,
            "element": element.to_dict() if element else None,
            "alternatives": [item.to_dict() for item in alternatives],
        }

    def find_elements(self, query: dict[str, Any], limit: int = 10) -> dict[str, Any]:
        analysis = self.analyzer.analyze_screen()
        elements = self.finder.find_all(analysis, query, limit=limit)
        return {"count": len(elements), "elements": [item.to_dict() for item in elements]}

    def wait_for_element(
        self,
        query: dict[str, Any],
        timeout: float | None = None,
        interval: float = 0.5,
    ) -> dict[str, Any]:
        deadline = time.time() + (timeout or self.settings.default_wait_timeout)
        observations = 0
        while time.time() <= deadline:
            observations += 1
            analysis = self.analyzer.analyze_screen()
            element = self._resolve_element(analysis, query)
            if element:
                return {
                    "found": True,
                    "observations": observations,
                    "element": element.to_dict(),
                    "screenshot": analysis.screenshot.to_dict(),
                }
            time.sleep(interval)
        return {"found": False, "observations": observations}

    def wait_until_disappears(
        self,
        query: dict[str, Any],
        timeout: float | None = None,
        interval: float = 0.5,
    ) -> dict[str, Any]:
        deadline = time.time() + (timeout or self.settings.default_wait_timeout)
        observations = 0
        last = None
        while time.time() <= deadline:
            observations += 1
            analysis = self.analyzer.analyze_screen()
            element = self._resolve_element(analysis, query)
            last = element.to_dict() if element else None
            if not element:
                return {"disappeared": True, "observations": observations}
            time.sleep(interval)
        return {"disappeared": False, "observations": observations, "lastElement": last}

    def wait_until_stable(
        self,
        timeout: float | None = None,
        interval: float = 0.5,
        threshold: float = 0.002,
        stable_observations: int = 2,
    ) -> dict[str, Any]:
        deadline = time.time() + (timeout or self.settings.default_wait_timeout)
        previous = self.screenshots.capture_screen("stable_before")
        observations = 1
        stable_count = 0
        last_change = None
        while time.time() <= deadline:
            time.sleep(interval)
            current = self.screenshots.capture_screen("stable_after")
            observations += 1
            last_change = compare_screenshots(previous.path, current.path)
            if float(last_change["changeRatio"]) <= threshold:
                stable_count += 1
                if stable_count >= stable_observations:
                    return {
                        "stable": True,
                        "observations": observations,
                        "lastChange": last_change,
                        "screenshot": current.to_dict(),
                    }
            else:
                stable_count = 0
            previous = current
        return {"stable": False, "observations": observations, "lastChange": last_change}

    def detect_state_changes(self, before_path: str, after_path: str) -> dict[str, Any]:
        return compare_screenshots(Path(before_path), Path(after_path))

    def compare_screenshots(self, before_path: str, after_path: str) -> dict[str, Any]:
        return self.detect_state_changes(before_path, after_path)

    def capture_screen(self) -> dict[str, Any]:
        return self.screenshots.capture_screen("manual_screen").to_dict()

    def capture_region(self, x: int, y: int, width: int, height: int) -> dict[str, Any]:
        return self.screenshots.capture_region(BoundingBox(x, y, width, height), "manual_region").to_dict()

    def capture_window(self, title: str) -> dict[str, Any]:
        windows = self.windows.list_windows()
        match = next((window for window in windows if title.lower() in window["title"].lower()), None)
        if not match:
            return {"ok": False, "reason": f"No window found matching '{title}'"}
        screenshot = self.screenshots.capture_window(
            BoundingBox(match["left"], match["top"], match["width"], match["height"]),
            "manual_window",
        )
        return {"ok": True, "window": match, "screenshot": screenshot.to_dict()}

    def create_annotated_screenshot(self) -> dict[str, Any]:
        analysis = self.analyzer.analyze_screen()
        output = self.settings.screenshots_dir / f"annotated_{int(time.time() * 1000)}.png"
        path = create_annotated_screenshot(analysis, output)
        return {"path": str(path), "elements": len(analysis.elements)}

    def move_mouse(self, x: int, y: int, options: dict[str, Any] | None = None) -> dict[str, Any]:
        action_options = ActionOptions.from_dict(options)
        return self.executor.run_action(
            "move_mouse",
            lambda: self.executor.mouse.move_mouse(x, y),
            action_options,
            PermissionLevel.STANDARD,
            {"x": x, "y": y},
        )

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        query: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"x": x, "y": y, "query": query}
        if query:
            analysis = self.analyzer.analyze_screen()
            element = self._resolve_element(analysis, query)
            if not element:
                return {"ok": False, "reason": "Element not found", "query": query}
            center = element.bbox.center
            x, y = center.x, center.y
            payload["target"] = element.to_dict()
        if x is None or y is None:
            return {"ok": False, "reason": "click requires coordinates or a query"}
        self.workflows.record("click", payload)
        return self.executor.run_action(
            "click",
            lambda: self.executor.mouse.click(x, y),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def double_click(self, x: int, y: int, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"x": x, "y": y}
        self.workflows.record("double_click", payload)
        return self.executor.run_action(
            "double_click",
            lambda: self.executor.mouse.double_click(x, y),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def right_click(self, x: int, y: int, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"x": x, "y": y}
        self.workflows.record("right_click", payload)
        return self.executor.run_action(
            "right_click",
            lambda: self.executor.mouse.right_click(x, y),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def scroll(
        self,
        clicks: int,
        x: int | None = None,
        y: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"clicks": clicks, "x": x, "y": y}
        self.workflows.record("scroll", payload)
        return self.executor.run_action(
            "scroll",
            lambda: self.executor.mouse.scroll(clicks, x, y),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def drag(
        self,
        start: dict[str, int],
        end: dict[str, int],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"start": start, "end": end}
        self.workflows.record("drag", payload)
        return self.executor.run_action(
            "drag",
            lambda: self.executor.mouse.drag(Point(**start), Point(**end)),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def drag_and_drop(
        self,
        start: dict[str, int],
        end: dict[str, int],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"start": start, "end": end}
        self.workflows.record("drag_and_drop", payload)
        return self.executor.run_action(
            "drag_and_drop",
            lambda: self.executor.mouse.drag_and_drop(Point(**start), Point(**end)),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def draw_path(
        self,
        points: list[dict[str, int]],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"points": points}
        self.workflows.record("draw_path", payload)
        return self.executor.run_action(
            "draw_path",
            lambda: self.executor.mouse.draw_path([Point(**point) for point in points]),
            ActionOptions.from_dict(options),
            PermissionLevel.FULL_CONTROL,
            payload,
        )

    def type_text(self, text: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"text": text}
        self.workflows.record("type_text", payload)
        return self.executor.run_action(
            "type_text",
            lambda: self.executor.keyboard.type_text(text),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def hotkey(self, keys: list[str], options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"keys": keys}
        self.workflows.record("hotkey", payload)
        return self.executor.run_action(
            "hotkey",
            lambda: self.executor.keyboard.hotkey(*keys),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def press_key(
        self,
        key: str,
        presses: int = 1,
        interval: float = 0.03,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"key": key, "presses": presses, "interval": interval}
        self.workflows.record("press_key", payload)
        return self.executor.run_action(
            "press_key",
            lambda: self.executor.keyboard.press_key(key, presses, interval),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def hold_key(self, key: str, seconds: float, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"key": key, "seconds": seconds}
        self.workflows.record("hold_key", payload)
        return self.executor.run_action(
            "hold_key",
            lambda: self.executor.keyboard.hold_key(key, seconds),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def paste_text(self, text: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"text": text}
        self.workflows.record("paste_text", payload)
        return self.executor.run_action(
            "paste_text",
            lambda: self.executor.keyboard.paste_text(text),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def select_all(self, options: dict[str, Any] | None = None) -> dict[str, Any]:
        self.workflows.record("select_all", {})
        return self.executor.run_action(
            "select_all",
            self.executor.keyboard.select_all,
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            {},
        )

    def list_windows(self) -> list[dict[str, Any]]:
        return self.windows.list_windows()

    def get_active_window(self) -> dict[str, Any] | None:
        return self.windows.get_active_window()

    def focus_window(self, title: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"title": title}
        self.workflows.record("focus_window", payload)
        return self.executor.run_action(
            "focus_window",
            lambda: self.windows.focus_window(title),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def move_window(
        self,
        title: str,
        x: int,
        y: int,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"title": title, "x": x, "y": y}
        self.workflows.record("move_window", payload)
        return self.executor.run_action(
            "move_window",
            lambda: self.windows.move_window(title, x, y),
            ActionOptions.from_dict(options),
            PermissionLevel.FULL_CONTROL,
            payload,
        )

    def resize_window(
        self,
        title: str,
        width: int,
        height: int,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"title": title, "width": width, "height": height}
        self.workflows.record("resize_window", payload)
        return self.executor.run_action(
            "resize_window",
            lambda: self.windows.resize_window(title, width, height),
            ActionOptions.from_dict(options),
            PermissionLevel.FULL_CONTROL,
            payload,
        )

    def maximize_window(self, title: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"title": title}
        self.workflows.record("maximize_window", payload)
        return self.executor.run_action(
            "maximize_window",
            lambda: self.windows.maximize_window(title),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def minimize_window(self, title: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"title": title}
        self.workflows.record("minimize_window", payload)
        return self.executor.run_action(
            "minimize_window",
            lambda: self.windows.minimize_window(title),
            ActionOptions.from_dict(options),
            PermissionLevel.STANDARD,
            payload,
        )

    def close_window(self, title: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"title": title}
        self.workflows.record("close_window", payload)
        return self.executor.run_action(
            "close_window",
            lambda: self.windows.close_window(title),
            ActionOptions.from_dict(options),
            PermissionLevel.DANGEROUS,
            payload,
        )

    def set_permission_level(self, level: str) -> dict[str, Any]:
        self.permissions.set_level(level)
        return self.permissions.snapshot()

    def get_permission_level(self) -> dict[str, str]:
        return self.permissions.snapshot()

    def get_memory(self) -> dict[str, Any]:
        return self.memory.snapshot()

    def remember_preference(self, key: str, value: Any) -> dict[str, Any]:
        self.memory.set_preference(key, value)
        return {"ok": True, "key": key, "value": value}

    def remember_element(self, key: str, element: dict[str, Any]) -> dict[str, Any]:
        self.memory.remember_element(key, element)
        return {"ok": True, "key": key}

    def get_remembered_element(self, key: str) -> dict[str, Any]:
        element = self.memory.get_element(key)
        return {"found": element is not None, "element": element}

    def read_logs(self, name: str = "actions", limit: int = 100) -> list[dict[str, Any]]:
        return self.logger.read(name, limit)

    def start_recording(self, name: str) -> dict[str, Any]:
        return self.workflows.start(name)

    def stop_recording(self) -> dict[str, Any]:
        return self.workflows.stop()

    def list_workflows(self) -> list[dict[str, Any]]:
        return self.workflows.list()

    def learn_from_user(self, name: str, duration_seconds: float = 30.0) -> dict[str, Any]:
        return self.human_demo.learn_from_user(name, duration_seconds)

    def replay_workflow(
        self,
        path: str,
        speed: float = 1.0,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workflow = self.workflows.load(Path(path))
        events = workflow.get("events", [])
        replayed = 0
        previous_dt = 0.0
        for event in events:
            dt = float(event.get("dt", event.get("ts", 0.0)))
            if workflow.get("kind") == "human_demo":
                delay = max(0.0, (dt - previous_dt) / max(0.1, speed))
                previous_dt = dt
            else:
                delay = 0.05 / max(0.1, speed)
            time.sleep(min(delay, 3.0))
            if self._replay_event(event, options):
                replayed += 1
        return {"ok": True, "path": path, "events": len(events), "replayed": replayed}

    def _replay_event(self, event: dict[str, Any], options: dict[str, Any] | None) -> bool:
        event_type = event.get("type")
        payload = event.get("payload", {})
        if event_type == "click":
            self.click(payload["x"], payload["y"], options=options)
            return True
        if event_type == "double_click":
            self.double_click(payload["x"], payload["y"], options=options)
            return True
        if event_type == "right_click":
            self.right_click(payload["x"], payload["y"], options=options)
            return True
        if event_type in {"drag", "drag_and_drop"}:
            self.drag_and_drop(payload["start"], payload["end"], options=options)
            return True
        if event_type == "draw_path":
            self.draw_path(payload["points"], options=options)
            return True
        if event_type == "type_text":
            self.type_text(payload["text"], options=options)
            return True
        if event_type == "paste_text":
            self.paste_text(payload["text"], options=options)
            return True
        if event_type == "hotkey":
            self.hotkey(payload["keys"], options=options)
            return True
        if event_type == "press_key":
            self.press_key(
                payload["key"],
                payload.get("presses", 1),
                payload.get("interval", 0.03),
                options=options,
            )
            return True
        if event_type == "select_all":
            self.select_all(options=options)
            return True
        if event_type == "scroll":
            self.scroll(payload["clicks"], payload.get("x"), payload.get("y"), options=options)
            return True
        if event_type == "focus_window":
            self.focus_window(payload["title"], options=options)
            return True
        if event_type == "move_window":
            self.move_window(payload["title"], payload["x"], payload["y"], options=options)
            return True
        if event_type == "resize_window":
            self.resize_window(
                payload["title"],
                payload["width"],
                payload["height"],
                options=options,
            )
            return True
        if event_type == "maximize_window":
            self.maximize_window(payload["title"], options=options)
            return True
        if event_type == "minimize_window":
            self.minimize_window(payload["title"], options=options)
            return True
        if event_type == "close_window":
            self.close_window(payload["title"], options=options)
            return True
        if event_type == "mouse_click" and payload.get("pressed"):
            self.click(payload["x"], payload["y"], options=options)
            return True
        if event_type == "key_press":
            key = payload.get("key", "")
            if len(key) == 1:
                self.type_text(key, options=options)
                return True
        return False

    def _resolve_element(self, analysis, query: dict[str, Any]):
        if memory_key := query.get("memoryKey"):
            remembered = self.memory.get_element(str(memory_key))
            if remembered:
                return self._dict_to_element(remembered)
        if image_path := query.get("image"):
            match = self.finder.find_by_template(
                Path(analysis.screenshot.path),
                Path(str(image_path)),
                float(query.get("threshold", 0.82)),
            )
            if match:
                return match
        return self.finder.find(analysis, query)

    def _dict_to_element(self, data: dict[str, Any]):
        from win_pilot_mcp.types import BoundingBox, ElementType, ScreenElement

        bbox = data["bbox"]
        return ScreenElement(
            id=data.get("id", "memory-element"),
            type=ElementType(data.get("type", "unknown")),
            bbox=BoundingBox(
                int(bbox["x"]),
                int(bbox["y"]),
                int(bbox["width"]),
                int(bbox["height"]),
            ),
            text=data.get("text", ""),
            description=data.get("description", ""),
            confidence=float(data.get("confidence", 0.5)),
            source=data.get("source", "memory"),
            attributes=data.get("attributes", {}),
        )

    def execute_task(
        self,
        prompt: str,
        max_steps: int = 20,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.planner.execute_task(prompt, max_steps=max_steps, options=options)

    def plan_task(self, prompt: str) -> dict[str, Any]:
        return self.planner.plan_task(prompt)
