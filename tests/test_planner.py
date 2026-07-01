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


def test_plan_task_for_type_into_field():
    planner = TaskPlanner(None, None, None, None)

    plan = planner.plan_task('type "hello" into Search')

    assert plan["steps"][0] == {"type": "click_by_text", "text": "Search", "elementType": "input"}
    assert plan["steps"][1] == {"type": "type_text", "text": "hello"}
