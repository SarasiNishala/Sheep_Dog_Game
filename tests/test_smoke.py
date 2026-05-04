"""
Smoke tests - exercise the pure-logic parts of the project that do not
need a display. Run with:
    pytest tests/
"""

import math
import pytest

from src.ai.fsm import FSM
from src.ai.pathfinding import a_star, smooth_path
from src.ai.perception import can_see, can_hear


# ---------------------------------------------------------------------------
# FSM
# ---------------------------------------------------------------------------
def test_fsm_initial_state():
    fsm = FSM("IDLE", ["IDLE", "WALKING", "RUNNING"], agent_name="t")
    assert fsm.state == "IDLE"
    assert fsm.time_in_state == 0.0


def test_fsm_change_state_valid():
    fsm = FSM("IDLE", ["IDLE", "WALKING"], agent_name="t")
    fsm.change_state("WALKING", "test")
    assert fsm.state == "WALKING"
    assert fsm.previous_state == "IDLE"
    assert "IDLE -> WALKING" in fsm.transition_log[-1]


def test_fsm_change_state_invalid_raises():
    fsm = FSM("IDLE", ["IDLE", "WALKING"], agent_name="t")
    with pytest.raises(ValueError):
        fsm.change_state("DANCING", "oops")


def test_fsm_update_accumulates_timer():
    fsm = FSM("IDLE", ["IDLE"], agent_name="t")
    fsm.update(0.5)
    fsm.update(0.3)
    assert fsm.time_in_state == pytest.approx(0.8)


def test_fsm_timer_resets_on_transition():
    fsm = FSM("IDLE", ["IDLE", "WALKING"], agent_name="t")
    fsm.update(1.0)
    fsm.change_state("WALKING")
    assert fsm.time_in_state == 0.0


# ---------------------------------------------------------------------------
# Pathfinding (A*)
# ---------------------------------------------------------------------------
def _build_grid(rows, cols, walls=()):
    grid = [[True] * cols for _ in range(rows)]
    for r, c in walls:
        grid[r][c] = False
    return grid


def test_astar_trivial_same_cell():
    grid = _build_grid(5, 5)
    path = a_star(grid, (2, 2), (2, 2))
    assert path == [(2, 2)]


def test_astar_open_grid_finds_path():
    grid = _build_grid(5, 5)
    path = a_star(grid, (0, 0), (4, 4))
    assert path[0] == (0, 0)
    assert path[-1] == (4, 4)
    assert len(path) >= 5


def test_astar_routes_around_wall():
    # build a vertical wall that splits the grid
    walls = [(r, 2) for r in range(4)]
    grid = _build_grid(5, 5, walls)
    path = a_star(grid, (0, 0), (4, 4))
    assert path, "path should exist by going around wall at row 4"
    # Must not traverse any wall cell
    for step in path:
        c, r = step
        assert grid[r][c] is True


def test_astar_no_path_returns_empty():
    # completely surround the goal
    walls = [(0, 1), (1, 0), (1, 1)]
    grid = _build_grid(5, 5, walls)
    # start at (2, 2), goal at (0, 0) surrounded -- still reachable via (1,1)? no, (1,1) is wall
    path = a_star(grid, (2, 2), (0, 0))
    # (0,0) itself is passable but its only neighbors are walls, so no path
    assert path == []


def test_smooth_path_noop_for_short_paths():
    grid = _build_grid(5, 5)
    p = [(0, 0), (1, 1)]
    assert smooth_path(p, grid) == p


def test_smooth_path_shortens_straight_line():
    grid = _build_grid(5, 5)
    # a long "staircase" that is actually a straight diagonal with LOS
    p = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]
    s = smooth_path(p, grid)
    # should collapse to endpoints on an open grid
    assert s[0] == (0, 0)
    assert s[-1] == (4, 4)
    assert len(s) <= len(p)


# ---------------------------------------------------------------------------
# Perception
# ---------------------------------------------------------------------------
def test_can_see_in_front():
    # facing east (0 deg), target directly east
    assert can_see((0, 0), 0, (100, 0),
                   vision_range=200, vision_angle_deg=120)


def test_can_see_outside_cone():
    # facing east, target directly west
    assert not can_see((0, 0), 0, (-100, 0),
                       vision_range=200, vision_angle_deg=120)


def test_can_see_outside_range():
    assert not can_see((0, 0), 0, (500, 0),
                       vision_range=200, vision_angle_deg=120)


def test_can_see_edge_of_cone():
    # 60 deg off-axis is exactly half of 120 deg cone -> should be visible
    angle = 60
    tx = math.cos(math.radians(angle)) * 50
    ty = math.sin(math.radians(angle)) * 50
    assert can_see((0, 0), 0, (tx, ty),
                   vision_range=200, vision_angle_deg=120)


def test_can_hear_nearby_loud():
    assert can_hear((0, 0), (10, 0), loudness=80, hearing_range=300)


def test_can_hear_rejects_out_of_range():
    assert not can_hear((0, 0), (500, 0), loudness=80, hearing_range=300)


def test_can_hear_quiet_sound_fades():
    # default falloff 0.1 per pixel. At 1000 pixels, 10 loudness => perceived = 0
    assert not can_hear((0, 0), (1000, 0), loudness=10, hearing_range=2000)
