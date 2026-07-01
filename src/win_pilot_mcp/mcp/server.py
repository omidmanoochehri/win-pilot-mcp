from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from win_pilot_mcp.tools import WinPilotService


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


mcp = FastMCP(
    "WinPilot Computer Use",
    host=os.getenv("WIN_PILOT_MCP_HOST", "127.0.0.1"),
    port=_int_env("WIN_PILOT_MCP_PORT", 8765),
    streamable_http_path=os.getenv("WIN_PILOT_MCP_PATH", "/mcp"),
    sse_path=os.getenv("WIN_PILOT_MCP_SSE_PATH", "/sse"),
    message_path=os.getenv("WIN_PILOT_MCP_MESSAGE_PATH", "/messages/"),
)
service = WinPilotService()


@mcp.tool()
def analyze_screen(force: bool = False) -> dict[str, Any]:
    """Capture and analyze the current screen."""
    return service.analyze_screen(force)


@mcp.tool()
def configure_optimization(
    cache_enabled: bool | None = None,
    cache_ttl_seconds: float | None = None,
    cache_change_threshold: float | None = None,
    action_delay: float | None = None,
) -> dict[str, Any]:
    """Tune observation caching and action delay for speed/accuracy tradeoffs."""
    return service.configure_optimization(
        cache_enabled,
        cache_ttl_seconds,
        cache_change_threshold,
        action_delay,
    )


@mcp.tool()
def clear_observation_cache() -> dict[str, Any]:
    """Clear cached screen analysis before a high-accuracy observation."""
    return service.clear_observation_cache()


@mcp.tool()
def get_performance_stats() -> dict[str, Any]:
    """Return observation cache and action timing metrics."""
    return service.get_performance_stats()


@mcp.tool()
def analyze_application(application: str) -> dict[str, Any]:
    """Analyze a known GUI workspace such as photoshop, elementor, browser, or generic."""
    return service.analyze_application(application)


@mcp.tool()
def get_desktop_model() -> dict[str, Any]:
    """Return the semantic desktop model built from the current screen."""
    return service.get_desktop_model()


@mcp.tool()
def get_vision_providers() -> list[dict[str, object]]:
    """Report installed OCR, object detection, grounding, and similarity providers."""
    return service.get_vision_providers()


@mcp.tool()
def detect_objects(
    provider: str = "opencv",
    image_path: str | None = None,
    prompt: str | None = None,
    model_path: str | None = None,
) -> dict[str, Any]:
    """Run a local vision provider over a screenshot or image path."""
    return service.detect_objects(provider, image_path, prompt, model_path)


@mcp.tool()
def get_canvas_state() -> dict[str, Any]:
    """Infer canvas areas, active canvas, selected element, and document size from screenshots."""
    return service.get_canvas_state()


@mcp.tool()
def get_photoshop_state() -> dict[str, Any]:
    """Infer Photoshop-specific panels, canvas, tools, layers, and export state from screenshots."""
    return service.get_photoshop_state()


@mcp.tool()
def get_elementor_state() -> dict[str, Any]:
    """Infer Elementor-specific sidebar, widgets, canvas, navigator, responsive mode, and publish controls."""
    return service.get_elementor_state()


@mcp.tool()
def get_browser_state() -> dict[str, Any]:
    """Infer browser address bar, tabs, dialogs, notifications, and page canvas from screenshots."""
    return service.get_browser_state()


@mcp.tool()
def get_word_state() -> dict[str, Any]:
    """Infer Word ribbon, document canvas, comments, review tools, and status from screenshots."""
    return service.get_word_state()


@mcp.tool()
def get_excel_state() -> dict[str, Any]:
    """Infer Excel ribbon, formula bar, grid, filters, and sheet tabs from screenshots."""
    return service.get_excel_state()


@mcp.tool()
def get_powerpoint_state() -> dict[str, Any]:
    """Infer PowerPoint ribbon, slide canvas, thumbnails, notes, and presentation controls."""
    return service.get_powerpoint_state()


@mcp.tool()
def get_vscode_state() -> dict[str, Any]:
    """Infer VSCode activity bar, explorer, editor, terminal, and command palette landmarks."""
    return service.get_vscode_state()


@mcp.tool()
def get_illustrator_state() -> dict[str, Any]:
    """Infer Illustrator toolbar, artboard, layers, properties, and color panels."""
    return service.get_illustrator_state()


@mcp.tool()
def get_player_state() -> dict[str, Any]:
    """Infer media player playback controls, timeline, playlist, and volume controls."""
    return service.get_player_state()


@mcp.tool()
def get_settings_state() -> dict[str, Any]:
    """Infer Windows Settings search, categories, and details pane."""
    return service.get_settings_state()


@mcp.tool()
def list_supported_apps() -> list[dict[str, Any]]:
    """List app profiles with landmarks and shortcut maps."""
    return service.list_supported_apps()


@mcp.tool()
def get_shortcuts(application: str = "common") -> dict[str, list[str]]:
    """Get registered keyboard shortcuts for an app profile."""
    return service.get_shortcuts(application)


@mcp.tool()
def run_app_shortcut(
    application: str,
    action: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a registered app shortcut, such as vscode command_palette or word bold."""
    return service.run_app_shortcut(application, action, options)


@mcp.tool()
def recover_from_unexpected_state() -> dict[str, Any]:
    """Analyze the screen and recommend a recovery path for popups, loading, crashes, errors, or auth."""
    return service.recover_from_unexpected_state()


@mcp.tool()
def decide_next_action(prompt: str) -> dict[str, Any]:
    """Observe the screen, parse the goal, assess recovery state, and rank candidates for the next step."""
    return service.decide_next_action(prompt)


@mcp.tool()
def find_element(query: dict[str, Any]) -> dict[str, Any]:
    """Find an element by text, icon, description, image, color, position, or type."""
    return service.find_element(query)


@mcp.tool()
def find_elements(query: dict[str, Any], limit: int = 10) -> dict[str, Any]:
    """Return ranked matching elements with match scores and score breakdowns."""
    return service.find_elements(query, limit)


@mcp.tool()
def wait_for_element(query: dict[str, Any], timeout: float = 15.0, interval: float = 0.5) -> dict[str, Any]:
    """Wait until a matching element appears."""
    return service.wait_for_element(query, timeout, interval)


@mcp.tool()
def wait_until_disappears(query: dict[str, Any], timeout: float = 15.0, interval: float = 0.5) -> dict[str, Any]:
    """Wait until a matching element disappears."""
    return service.wait_until_disappears(query, timeout, interval)


@mcp.tool()
def wait_until_stable(
    timeout: float = 15.0,
    interval: float = 0.5,
    threshold: float = 0.002,
    stable_observations: int = 2,
) -> dict[str, Any]:
    """Wait until repeated screenshots show the screen has stopped changing."""
    return service.wait_until_stable(timeout, interval, threshold, stable_observations)


@mcp.tool()
def detect_state_changes(before_path: str, after_path: str) -> dict[str, Any]:
    """Compare two screenshots and report visible changes."""
    return service.detect_state_changes(before_path, after_path)


@mcp.tool()
def compare_screenshots(before_path: str, after_path: str) -> dict[str, Any]:
    """Compare two screenshots and report visible changes."""
    return service.compare_screenshots(before_path, after_path)


@mcp.tool()
def capture_screen() -> dict[str, Any]:
    """Capture the full screen."""
    return service.capture_screen()


@mcp.tool()
def capture_region(x: int, y: int, width: int, height: int) -> dict[str, Any]:
    """Capture a screen region."""
    return service.capture_region(x, y, width, height)


@mcp.tool()
def capture_window(title: str) -> dict[str, Any]:
    """Capture a window by title substring."""
    return service.capture_window(title)


@mcp.tool()
def create_annotated_screenshot() -> dict[str, Any]:
    """Create a screenshot with detected element boxes drawn on top."""
    return service.create_annotated_screenshot()


@mcp.tool()
def move_mouse(x: int, y: int, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Move the mouse with human-like motion."""
    return service.move_mouse(x, y, options)


@mcp.tool()
def click(
    x: int | None = None,
    y: int | None = None,
    query: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Click coordinates or a found element."""
    return service.click(x, y, query, options)


@mcp.tool()
def double_click(x: int, y: int, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Double-click coordinates."""
    return service.double_click(x, y, options)


@mcp.tool()
def right_click(x: int, y: int, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Right-click coordinates."""
    return service.right_click(x, y, options)


@mcp.tool()
def scroll(
    clicks: int,
    x: int | None = None,
    y: int | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Scroll at the current cursor position, or at x/y if provided."""
    return service.scroll(clicks, x, y, options)


@mcp.tool()
def drag(start: dict[str, int], end: dict[str, int], options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Drag from one point to another."""
    return service.drag(start, end, options)


@mcp.tool()
def drag_and_drop(start: dict[str, int], end: dict[str, int], options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Drag and drop from one point to another."""
    return service.drag_and_drop(start, end, options)


@mcp.tool()
def draw_path(points: list[dict[str, int]], options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hold the mouse and draw through a list of points."""
    return service.draw_path(points, options)


@mcp.tool()
def type_text(text: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Type text using keyboard input."""
    return service.type_text(text, options)


@mcp.tool()
def hotkey(keys: list[str], options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Press a key combination such as ['ctrl', 's'].""" 
    return service.hotkey(keys, options)


@mcp.tool()
def press_key(
    key: str,
    presses: int = 1,
    interval: float = 0.03,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Press a single key one or more times."""
    return service.press_key(key, presses, interval, options)


@mcp.tool()
def hold_key(key: str, seconds: float, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hold a key for a duration."""
    return service.hold_key(key, seconds, options)


@mcp.tool()
def paste_text(text: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Paste text through clipboard plus keyboard fallback."""
    return service.paste_text(text, options)


@mcp.tool()
def select_all(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Press Ctrl+A."""
    return service.select_all(options)


@mcp.tool()
def list_windows() -> list[dict[str, Any]]:
    """List visible windows."""
    return service.list_windows()


@mcp.tool()
def get_active_window() -> dict[str, Any] | None:
    """Get the active window."""
    return service.get_active_window()


@mcp.tool()
def focus_window(title: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Focus a window by title substring."""
    return service.focus_window(title, options)


@mcp.tool()
def move_window(title: str, x: int, y: int, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Move a window by title substring."""
    return service.move_window(title, x, y, options)


@mcp.tool()
def resize_window(
    title: str,
    width: int,
    height: int,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resize a window by title substring."""
    return service.resize_window(title, width, height, options)


@mcp.tool()
def maximize_window(title: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Maximize a window by title substring."""
    return service.maximize_window(title, options)


@mcp.tool()
def minimize_window(title: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Minimize a window by title substring."""
    return service.minimize_window(title, options)


@mcp.tool()
def close_window(title: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Close a window by title substring. Requires dangerous permission."""
    return service.close_window(title, options)


@mcp.tool()
def set_permission_level(level: str) -> dict[str, Any]:
    """Set current permission level: read_only, standard, full_control, dangerous."""
    return service.set_permission_level(level)


@mcp.tool()
def get_permission_level() -> dict[str, str]:
    """Get the current permission level."""
    return service.get_permission_level()


@mcp.tool()
def get_memory() -> dict[str, Any]:
    """Return remembered element locations, workflow results, and user preferences."""
    return service.get_memory()


@mcp.tool()
def remember_preference(key: str, value: Any) -> dict[str, Any]:
    """Remember a user preference such as common panel location or preferred workflow option."""
    return service.remember_preference(key, value)


@mcp.tool()
def remember_element(key: str, element: dict[str, Any]) -> dict[str, Any]:
    """Store an element location or descriptor for future adaptive lookup."""
    return service.remember_element(key, element)


@mcp.tool()
def get_remembered_element(key: str) -> dict[str, Any]:
    """Get a remembered element by key."""
    return service.get_remembered_element(key)


@mcp.tool()
def read_logs(name: str = "actions", limit: int = 100) -> list[dict[str, Any]]:
    """Read recent structured logs: actions, screenshots, errors, or workflows."""
    return service.read_logs(name, limit)


@mcp.tool()
def start_recording(name: str) -> dict[str, Any]:
    """Start recording workflow events initiated through MCP tools."""
    return service.start_recording(name)


@mcp.tool()
def stop_recording() -> dict[str, Any]:
    """Stop recording and save the workflow."""
    return service.stop_recording()


@mcp.tool()
def list_workflows() -> list[dict[str, Any]]:
    """List saved macro and demonstration workflow recordings."""
    return service.list_workflows()


@mcp.tool()
def learn_from_user(name: str, duration_seconds: float = 30.0) -> dict[str, Any]:
    """Record a human demonstration for a fixed duration using mouse/keyboard hooks."""
    return service.learn_from_user(name, duration_seconds)


@mcp.tool()
def replay_workflow(path: str, speed: float = 1.0, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Replay a saved workflow through mouse and keyboard input."""
    return service.replay_workflow(path, speed, options)


@mcp.tool()
def execute_task(prompt: str, max_steps: int = 20, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a task using observe, plan, act, verify, and retry cycles."""
    return service.execute_task(prompt, max_steps, options)


@mcp.tool()
def plan_task(prompt: str) -> dict[str, Any]:
    """Break a GUI task prompt into one-action-at-a-time steps without executing them."""
    return service.plan_task(prompt)


def main() -> None:
    transport = os.getenv("WIN_PILOT_MCP_TRANSPORT", "stdio")
    mount_path = os.getenv("WIN_PILOT_MCP_MOUNT_PATH")
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError(
            "WIN_PILOT_MCP_TRANSPORT must be one of: stdio, sse, streamable-http"
        )
    mcp.run(transport=transport, mount_path=mount_path)


if __name__ == "__main__":
    main()
