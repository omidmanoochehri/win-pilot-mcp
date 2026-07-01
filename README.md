# WinPilot Computer Use MCP

WinPilot is a Windows computer-use MCP server for Codex-style agents. It operates GUI
applications the same way a human does:

- screen capture
- computer vision
- OCR
- mouse movement
- keyboard input
- window management

It intentionally avoids application APIs, browser automation APIs, plugins, extensions, and
application integrations. Chrome, Photoshop, Elementor, file dialogs, installers, and desktop
apps are all treated as pixels plus OS input.

## Status

This repository contains the first production-oriented implementation skeleton:

- MCP tools for observation, element lookup, waiting, input, windows, screenshots, workflows,
  permissions, and task execution.
- A vision pipeline with OCR, UI primitive detection, scrollable/dialog heuristics, screenshot
  diffing, annotated screenshots, and a semantic desktop model.
- A guarded executor with per-action safety options, before/after screenshots, human-like mouse
  motion, keyboard entry, and structured logging.
- Memory and workflow recording so successful layouts and demonstrations can be reused.

Optional advanced detectors such as PaddleOCR, YOLO, OmniParser, Florence2, and Grounding DINO
are wired through extension points. The baseline works with local screenshots, OpenCV, Tesseract,
and Windows input primitives.

## Install

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Install Tesseract OCR separately and make sure `tesseract.exe` is on `PATH`.

Optional vision stack:

```powershell
pip install -e ".[vision]"
```

## Run MCP Server

```powershell
win-pilot-mcp
```

Or:

```powershell
python -m win_pilot_mcp.mcp.server
```

For a background/local HTTP MCP endpoint:

```powershell
$env:WIN_PILOT_MCP_TRANSPORT="streamable-http"
$env:WIN_PILOT_MCP_HOST="127.0.0.1"
$env:WIN_PILOT_MCP_PORT="8765"
python -m win_pilot_mcp.mcp.server
```

Endpoint:

```text
http://127.0.0.1:8765/mcp
```

## Core Loop

Every task is executed as:

1. Observe the screen.
2. Think and choose one next action.
3. Act through mouse, keyboard, or window controls.
4. Re-observe.
5. Verify the result.
6. Retry or recover if needed.

The planner never executes long blind action sequences.

## Safety Levels

Actions are classified into:

- `read_only`
- `standard`
- `full_control`
- `dangerous`

Each action accepts:

```json
{
  "dryRun": false,
  "requireConfirmation": true,
  "takeScreenshotBefore": null,
  "takeScreenshotAfter": null,
  "verificationMode": "auto"
}
```

The server defaults to `standard`, which allows normal navigation/input but blocks dangerous
actions unless the permission level is raised. Screenshot verification defaults to `auto`: low
value actions such as mouse move, scroll, focus, key press, hotkey, and wait skip before/after
screenshots, while uncertain targets, text entry, clicks, drags, window changes, full-control,
and dangerous actions still capture screenshots for accuracy. Set `verificationMode` to
`always` or explicit `takeScreenshotBefore` / `takeScreenshotAfter` booleans to override.

## MCP Tools

Representative tools:

- `analyze_screen`
- `configure_optimization`
- `clear_observation_cache`
- `get_performance_stats`
- `analyze_application`
- `get_desktop_model`
- `get_canvas_state`
- `get_photoshop_state`
- `get_elementor_state`
- `get_browser_state`
- `get_vision_providers`
- `detect_objects`
- `find_element`
- `wait_for_element`
- `wait_until_disappears`
- `wait_until_stable`
- `detect_state_changes`
- `compare_screenshots`
- `capture_screen`
- `capture_region`
- `create_annotated_screenshot`
- `move_mouse`, `click`, `double_click`, `right_click`, `drag`, `drag_and_drop`, `draw_path`
- `scroll`
- `type_text`, `press_key`, `hotkey`, `hold_key`, `paste_text`, `select_all`
- `list_windows`, `focus_window`, `maximize_window`, `resize_window`
- `get_permission_level`, `set_permission_level`
- `get_memory`, `remember_preference`, `remember_element`, `get_remembered_element`
- `start_recording`, `stop_recording`, `list_workflows`, `learn_from_user`, `replay_workflow`
- `read_logs`
- `recover_from_unexpected_state`
- `decide_next_action`
- `plan_task`
- `execute_task`

## Feature Coverage

- Screen understanding: OCR text, buttons, icons, toolbars, menus, tabs, dropdowns,
  checkboxes, radio buttons, inputs, dialogs, images, canvas areas, loading indicators,
  context menus, notifications, file pickers, scrollables, selected elements, and a semantic
  desktop model.
- Element lookup: text, type, description, image template, color, position, and remembered
  locations.
- Vision stack: Tesseract/PaddleOCR OCR, OpenCV primitives and similarity, YOLO adapter,
  and explicit provider hooks for OmniParser, Florence2, and Grounding DINO.
- Input: human-like mouse movement, click variants, scroll, drag/drop, drawing paths, text
  typing, key presses, hotkeys, key holds, paste, and select-all.
- Windows: list, active window, focus, move, resize, maximize, minimize, and close.
- Screenshots: full screen, region, window, comparison, change detection, annotated captures,
  and stability waits.
- Agent loop: observe, plan one step, act, verify, recover, and retry. `plan_task` exposes the
  planned steps; `execute_task` executes one action at a time with re-observation.
- Recovery: detects loading, dialogs, crashes, visible errors, and authentication blocks, then
  recommends the next recovery action.
- Photoshop and Elementor: screenshot/OCR-only semantic state helpers for panels, canvas,
  widgets, navigator, publish controls, layers/properties/export dialogs, active tool, and
  inferred document size.
- Memory and workflows: remembered elements, preferences, action logs, macro recording,
  human demonstration capture, workflow listing, and replay.
- Safety: read-only, standard, full-control, and dangerous permission levels, plus `dryRun`,
  `requireConfirmation`, and before/after screenshots on mutating actions.

## Project Layout

```text
src/win_pilot_mcp/
  mcp/
  agent/
  vision/
  executor/
  planner/
  memory/
  tools/
  workflows/
  permissions/
  logs/
  screenshots/
```

Runtime artifacts are written to `runtime/` by default.
