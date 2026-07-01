import pytest

from win_pilot_mcp.permissions import PermissionManager
from win_pilot_mcp.types import PermissionLevel


def test_permission_manager_blocks_higher_level_actions():
    manager = PermissionManager(PermissionLevel.STANDARD)

    with pytest.raises(PermissionError):
        manager.require(PermissionLevel.DANGEROUS, "close_window")


def test_permission_manager_allows_current_level_actions():
    manager = PermissionManager(PermissionLevel.FULL_CONTROL)

    manager.require(PermissionLevel.STANDARD, "click")
    manager.require(PermissionLevel.FULL_CONTROL, "draw_path")
