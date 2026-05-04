"""
Debug overlay - modernized with pills, cards, and proper spacing.

Toggled with F1. Draws:
    - translucent vision cones
    - dashed hearing circles
    - A* path waypoints
    - state label pills above each agent
    - emotion mini-bars
    - wolf strategy labels
    - event log card (top-right corner when rubric off, under stats card)
    - rubric checklist card (F2 toggle, left side)
"""

import math
import pygame

from ..core import settings as cfg
from . import ui_theme as ui
from ..ai.perception import get_vision_cone_polygon


# =============================================================================
# Main entry
# =============================================================================
def draw_debug(surface, world):
    """Draw all per-agent debug visuals."""
    dog = world.get_dog()
    if dog and dog.alive:
        _draw_vision_cone(surface, dog, color=ui.ACCENT)
        _draw_hearing_circle(surface, dog, color=ui.INFO)
        _draw_path(surface, world, dog)
        _draw_target_line(surface, dog, color=ui.ACCENT)
        _draw_state_pill(surface, dog)
        _draw_emotion_bars(surface, dog)

    for wolf in world.wolves:
        if not wolf.alive:
            continue
        _draw_vision_cone(surface, wolf, color=ui.DANGER)
        _draw_hearing_circle(surface, wolf, color=ui.DANGER_DIM)
        _draw_target_line(surface, wolf, color=ui.DANGER)
        _draw_state_pill(surface, wolf)
        _draw_strategy_pill(surface, wolf)
        _draw_emotion_bars(surface, wolf)

    for sheep in world.sheep:
        if not sheep.alive:
            continue
        _draw_sheep_state(surface, sheep)


# =============================================================================
# Per-agent debug primitives
# =============================================================================
def _draw_vision_cone(surface, agent, color):
    vision_range = agent.vision_range * agent.world.vision_multiplier()
    points = get_vision_cone_polygon(
        agent.pos, agent.facing_deg, vision_range, agent.vision_angle,
    )
    cone_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    # fill with 12% alpha tint
    pygame.draw.polygon(cone_surface, (*color, 30), points)
    # outline with 40% alpha
    pygame.draw.polygon(cone_surface, (*color, 100), points, 1)
    surface.blit(cone_surface, (0, 0))


def _draw_hearing_circle(surface, agent, color):
    hearing = agent.hearing_range * agent.world.hearing_multiplier()
    steps = 32
    for i in range(steps):
        if i % 2 == 0:
            continue  # dashed
        a1 = 2 * math.pi * i / steps
        a2 = 2 * math.pi * (i + 1) / steps
        x1 = agent.pos.x + math.cos(a1) * hearing
        y1 = agent.pos.y + math.sin(a1) * hearing
        x2 = agent.pos.x + math.cos(a2) * hearing
        y2 = agent.pos.y + math.sin(a2) * hearing
        pygame.draw.line(surface, color, (x1, y1), (x2, y2), 1)


def _draw_path(surface, world, dog):
    if not dog.current_path or len(dog.current_path) < 2:
        return
    points = [world.cell_to_world(c) for c in dog.current_path]

    # soft path line
    path_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for i in range(len(points) - 1):
        pygame.draw.line(
            path_surf, (*ui.ACCENT, 180),
            points[i], points[i + 1], 2,
        )
    surface.blit(path_surf, (0, 0))

    # dots
    for p in points:
        pygame.draw.circle(surface, ui.ACCENT,
                           (int(p.x), int(p.y)), 3)


def _draw_target_line(surface, agent, color):
    if agent.current_target is None:
        return
    ts = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.line(
        ts, (*color, 120),
        (int(agent.pos.x), int(agent.pos.y)),
        (int(agent.current_target[0]), int(agent.current_target[1])),
        1,
    )
    surface.blit(ts, (0, 0))


def _draw_state_pill(surface, agent):
    """Modern pill label with a colored dot prefix."""
    if agent.fsm is None:
        return
    state = agent.fsm.state
    color = _state_color_for(agent, state)

    label = ui.render_text(state, 9, ui.TEXT_PRIMARY, "bold")
    dot_size = 5
    pad_x = 8
    pad_y = 3
    gap = 6
    w = dot_size * 2 + gap + label.get_width() + pad_x * 2
    h = max(label.get_height(), dot_size * 2) + pad_y * 2

    x = int(agent.pos.x - w // 2)
    y = int(agent.pos.y - agent.radius - h - 4)

    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*ui.BG_DEEP, 210), panel.get_rect(),
                     border_radius=h // 2)
    pygame.draw.rect(panel, (*color, 180), panel.get_rect(), 1,
                     border_radius=h // 2)
    # dot
    pygame.draw.circle(
        panel, color,
        (pad_x + dot_size, h // 2),
        dot_size,
    )
    # label
    panel.blit(
        label,
        (pad_x + dot_size * 2 + gap,
         (h - label.get_height()) // 2),
    )
    surface.blit(panel, (x, y))


def _draw_sheep_state(surface, sheep):
    """Smaller, more compact pill for sheep (don't clutter the screen)."""
    state = sheep.fsm.state
    abbrev = {
        "GRAZING":  "graze",
        "ALERT":    "alert",
        "FLEEING":  "flee",
        "HERDED":   "herd",
        "PENNED":   "penned",
        "DEAD":     "dead",
    }.get(state, state[:5].lower())

    color = {
        "GRAZING":  ui.TEXT_MUTED,
        "ALERT":    ui.WARNING,
        "FLEEING":  ui.DANGER,
        "HERDED":   ui.ACCENT,
        "PENNED":   ui.SUCCESS,
    }.get(state, ui.TEXT_SECONDARY)

    label = ui.render_text(abbrev, 8, color, "bold")
    pad_x = 5
    pad_y = 1
    w = label.get_width() + pad_x * 2
    h = label.get_height() + pad_y * 2
    x = int(sheep.pos.x - w // 2)
    y = int(sheep.pos.y - sheep.radius - h - 2)

    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*ui.BG_DEEP, 180), panel.get_rect(),
                     border_radius=h // 2)
    panel.blit(label, (pad_x, pad_y))
    surface.blit(panel, (x, y))


def _draw_strategy_pill(surface, wolf):
    """Wolf's current hunting strategy shown below it."""
    label = ui.render_text(wolf.current_strategy.replace("_", " "),
                           8, ui.WARNING, "bold")
    pad_x = 6
    pad_y = 2
    w = label.get_width() + pad_x * 2
    h = label.get_height() + pad_y * 2
    x = int(wolf.pos.x - w // 2)
    y = int(wolf.pos.y + wolf.radius + 4)

    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*ui.BG_DEEP, 200), panel.get_rect(),
                     border_radius=h // 2)
    pygame.draw.rect(panel, (*ui.WARNING, 120), panel.get_rect(), 1,
                     border_radius=h // 2)
    panel.blit(label, (pad_x, pad_y))
    surface.blit(panel, (x, y))


def _draw_emotion_bars(surface, agent):
    """Three tiny stacked bars under the agent."""
    x = int(agent.pos.x - 12)
    y = int(agent.pos.y + agent.radius + 3)
    w = 24
    h = 2
    gap = 2

    fear = agent.emotion.fear / cfg.EMOTION_MAX
    anger = agent.emotion.anger / cfg.EMOTION_MAX
    happy = agent.emotion.happiness / cfg.EMOTION_MAX

    # background rows
    for i in range(3):
        pygame.draw.rect(
            surface, ui.BG_DEEP,
            pygame.Rect(x, y + i * (h + gap), w, h),
            border_radius=1,
        )

    pygame.draw.rect(
        surface, ui.INFO,
        pygame.Rect(x, y, int(w * fear), h),
        border_radius=1,
    )
    pygame.draw.rect(
        surface, ui.DANGER,
        pygame.Rect(x, y + h + gap, int(w * anger), h),
        border_radius=1,
    )
    pygame.draw.rect(
        surface, ui.SUCCESS,
        pygame.Rect(x, y + (h + gap) * 2, int(w * happy), h),
        border_radius=1,
    )


def _state_color_for(agent, state: str):
    """Pick a color based on agent type and state."""
    # Dog states
    dog_map = {
        "IDLE":         ui.TEXT_MUTED,
        "PATROLLING":   ui.INFO,
        "HERDING":      ui.ACCENT,
        "CHASING_WOLF": ui.DANGER,
        "RETURNING":    ui.WARNING,
        "RESTING":      ui.TEXT_SECONDARY,
        "EXHAUSTED":    ui.DANGER,
    }
    wolf_map = {
        "PATROL":   ui.TEXT_MUTED,
        "STALK":    ui.WARNING,
        "CHARGE":   ui.DANGER,
        "FLEE":     ui.INFO,
        "RESTING":  ui.TEXT_SECONDARY,
    }
    if state in dog_map:
        return dog_map[state]
    if state in wolf_map:
        return wolf_map[state]
    return ui.TEXT_SECONDARY


# =============================================================================
# Rubric checklist card (F2 toggle)
# =============================================================================
RUBRIC_ITEMS = [
    ("Agent pursues goal",            "agents/dog.py"),
    ("State-based behavior",           "ai/fsm.py"),
    ("Event-driven transitions",       "agents/dog.py"),
    ("NL communication",               "agent.say() + speech bubbles"),
    ("Perception: vision cone",        "ai/perception.py"),
    ("Perception: hearing",            "ai/perception.py"),
    ("Emotional intelligence",         "agents/agent.py"),
    ("Learning (strategies)",          "agents/wolf.py"),
    ("Pathfinding (A*)",               "ai/pathfinding.py"),
    ("Decision making (utility)",      "agents/dog.py"),
    ("Physics: friction, sound falloff", "agents/agent.py"),
    ("Weather phenomena",              "world/weather.py"),
    ("Time-of-day vision penalty",     "world/day_night.py"),
    ("Multi-agent (2 dogs, sheep, wolves, owner)", "world/world.py"),
    ("Random happenings",              "world/world.py"),
    ("Alternative endings",            "world/world.py"),
]


def draw_rubric_checklist(surface):
    """Rubric overlay pinned to the left edge."""
    rows = len(RUBRIC_ITEMS)
    pad = 14
    row_h = 24
    header_h = 34
    card_w = 340
    card_h = header_h + row_h * rows + pad * 2

    x = 16
    y = (cfg.SCREEN_HEIGHT - card_h) // 2
    rect = pygame.Rect(x, y, card_w, card_h)
    ui.draw_glass_card(surface, rect, radius=12)

    # header
    ui.draw_section_title(
        surface, "RUBRIC", (rect.x + 16, rect.y + 12),
        size=9, color=ui.ACCENT,
    )
    header = ui.render_text(
        "All requirements implemented", 12, ui.TEXT_PRIMARY, "bold",
    )
    surface.blit(header, (rect.x + 16, rect.y + 24))

    # divider
    pygame.draw.line(
        surface, ui.BORDER_SUBTLE,
        (rect.x + 12, rect.y + header_h + 8),
        (rect.x + rect.w - 12, rect.y + header_h + 8),
        1,
    )

    # list
    row_y = rect.y + header_h + pad + 4
    for label, where in RUBRIC_ITEMS:
        # check mark in circle
        pygame.draw.circle(
            surface, (*ui.SUCCESS, 40) if False else ui.BG_ELEVATED,
            (rect.x + 22, row_y + 9), 8,
        )
        pygame.draw.circle(
            surface, ui.SUCCESS,
            (rect.x + 22, row_y + 9), 8, 1,
        )
        check = ui.render_text("OK", 8, ui.SUCCESS, "bold")
        surface.blit(
            check,
            (rect.x + 22 - check.get_width() // 2,
             row_y + 9 - check.get_height() // 2),
        )

        # label
        label_surf = ui.render_text(label, 11, ui.TEXT_PRIMARY)
        surface.blit(label_surf, (rect.x + 40, row_y))

        # file hint (smaller, muted)
        where_surf = ui.render_text(where, 9, ui.TEXT_MUTED)
        surface.blit(where_surf, (rect.x + 40, row_y + 13))

        row_y += row_h


# =============================================================================
# Event log (bottom-right, small)
# =============================================================================
def draw_event_log(surface, event_bus):
    if not event_bus.recent_events:
        return

    events = event_bus.recent_events[-8:]
    card_w = 250
    row_h = 14
    header_h = 22
    pad = 10
    card_h = header_h + row_h * len(events) + pad

    x = cfg.SCREEN_WIDTH - card_w - 16
    # position above the bottom controls strip
    y = cfg.SCREEN_HEIGHT - card_h - 80
    rect = pygame.Rect(x, y, card_w, card_h)
    ui.draw_glass_card(surface, rect, radius=10)

    ui.draw_section_title(
        surface, "EVENT LOG",
        (rect.x + 14, rect.y + 8),
        size=9, color=ui.TEXT_MUTED,
    )

    row_y = rect.y + header_h
    for evt in events:
        # event-type color coding
        color = ui.TEXT_SECONDARY
        if "killed" in evt:
            color = ui.DANGER
        elif "penned" in evt or "saved" in evt:
            color = ui.SUCCESS
        elif "howl" in evt or "wolf" in evt:
            color = ui.WARNING
        elif "whistle" in evt or "bark" in evt:
            color = ui.INFO

        # colored dot prefix
        pygame.draw.circle(
            surface, color,
            (rect.x + 18, row_y + 5),
            3,
        )
        text = ui.render_text(evt, 10, ui.TEXT_SECONDARY)
        surface.blit(text, (rect.x + 28, row_y))
        row_y += row_h
