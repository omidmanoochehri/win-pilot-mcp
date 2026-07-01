from win_pilot_mcp.planner.engine import TaskPlanner


def test_plan_task_for_open_app():
    planner = TaskPlanner(None, None, None, None)

    plan = planner.plan_task("open Photoshop")

    assert plan["requiresPolicyLoop"] is False
    assert plan["steps"][0] == {"type": "press_key", "key": "win"}
    assert plan["steps"][1] == {"type": "type_text", "text": "photoshop"}
    assert plan["steps"][-1] == {"type": "focus_window", "title": "photoshop"}


def test_plan_task_for_focus_app():
    planner = TaskPlanner(None, None, None, None)

    plan = planner.plan_task("focus Chrome")

    assert plan["requiresPolicyLoop"] is False
    assert plan["steps"] == [{"type": "focus_window", "title": "chrome"}]


def test_plan_task_for_url_navigation():
    planner = TaskPlanner(None, None, None, None)

    plan = planner.plan_task("go to https://example.com")

    assert plan["steps"][0] == {"type": "hotkey", "keys": ["ctrl", "l"]}
    assert plan["steps"][1] == {"type": "type_text", "text": "https://example.com"}


def test_plan_task_for_app_shortcuts():
    planner = TaskPlanner(None, None, None, None)

    assert planner.plan_task("word bold")["steps"] == [
        {"type": "app_shortcut", "application": "word", "action": "bold", "keys": ["ctrl", "b"]}
    ]
    assert planner.plan_task("vscode command palette")["steps"] == [
        {
            "type": "app_shortcut",
            "application": "vscode",
            "action": "command_palette",
            "keys": ["ctrl", "shift", "p"],
        }
    ]
    assert planner.plan_task("run format document in vscode")["steps"] == [
        {
            "type": "app_shortcut",
            "application": "vscode",
            "action": "format_document",
            "keys": ["shift", "alt", "f"],
        }
    ]


def test_plan_task_for_settings_and_player_shortcuts():
    planner = TaskPlanner(None, None, None, None)

    assert planner.plan_task("open settings")["steps"] == [
        {"type": "app_shortcut", "application": "settings", "action": "open_settings", "keys": ["win", "i"]}
    ]
    assert planner.plan_task("player play pause")["steps"] == [
        {"type": "app_shortcut", "application": "player", "action": "play_pause", "keys": ["space"]}
    ]


def test_plan_task_for_type_into_field():
    planner = TaskPlanner(None, None, None, None)

    plan = planner.plan_task('type "hello" into Search')

    assert plan["steps"][0] == {"type": "click_by_text", "text": "Search", "elementType": "input"}
    assert plan["steps"][1] == {"type": "type_text", "text": "hello"}
