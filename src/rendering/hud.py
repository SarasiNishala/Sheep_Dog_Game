"""
HUD - Pixel-art warm farm style.
Warm wood-panel cards, chunky borders, earthy palette.
"""

import math
import pygame

from ..core import settings as cfg
from . import ui_theme as ui

# sheep emoji fallback character
_SHEEP = "\u2665"   # heart — fallback if emoji not available


# =============================================================================
# Main entry point
# =============================================================================
def draw_hud(surface, world, fps: float, debug_on: bool, rubric_on: bool):
    _draw_stats_card(surface, world)
    _draw_dog_card(surface, world.dogs)
    _draw_environment_card(surface, world)
    _draw_controls_strip(surface, debug_on, rubric_on)
    if cfg.SHOW_FPS:
        _draw_fps(surface, fps)


# =============================================================================
# Stats card  (top-right)
# =============================================================================
def _draw_stats_card(surface, world):
    penned = sum(1 for s in world.sheep if s.alive and world.is_in_pen(s.pos))
    alive  = sum(1 for s in world.sheep if s.alive)
    lost   = len(world.sheep) - alive
    total  = len(world.sheep)

    w, h = 240, 118
    x = cfg.SCREEN_WIDTH - w - 14
    y = 14
    rect = pygame.Rect(x, y, w, h)
    ui.draw_glass_card(surface, rect, radius=8)

    # ── header row ──────────────────────────────────────────────────
    header_surf = ui.render_text("FLOCK", 9, ui.TEXT_MUTED, "bold")
    surface.blit(header_surf, (rect.x + 14, rect.y + 10))
    ui.draw_divider(surface, rect.x + 14, rect.y + 24, w - 28)

    # ── big penned number ────────────────────────────────────────────
    big = ui.render_text(str(penned), 34, ui.SUCCESS, "bold")
    surface.blit(big, (rect.x + 14, rect.y + 28))

    slash = ui.render_text(f"/ {total}", 14, ui.TEXT_MUTED)
    surface.blit(slash, (rect.x + 14 + big.get_width() + 5, rect.y + 48))

    saved_lbl = ui.render_text("SAVED", 9, ui.TEXT_MUTED, "bold")
    surface.blit(saved_lbl, (rect.x + 14, rect.y + 72))

    # progress bar — sheep pen progress
    bar = pygame.Rect(rect.x + 14, rect.y + 86, w - 28, 8)
    ui.draw_progress_bar(surface, bar, penned, total, fg=ui.SUCCESS)

    # ── mini stats right side ────────────────────────────────────────
    mx = rect.x + w - 72
    alive_lbl = ui.render_text("ALIVE", 9, ui.TEXT_MUTED, "bold")
    surface.blit(alive_lbl, (mx, rect.y + 10))
    alive_val = ui.render_text(str(alive), 22, ui.TEXT_PRIMARY, "bold")
    surface.blit(alive_val, (mx, rect.y + 26))

    lost_lbl = ui.render_text("LOST", 9, ui.TEXT_MUTED, "bold")
    surface.blit(lost_lbl, (mx, rect.y + 56))
    lc = ui.DANGER if lost > 0 else ui.TEXT_MUTED
    lost_val = ui.render_text(str(lost), 18, lc, "bold")
    surface.blit(lost_val, (mx, rect.y + 70))

    # small sheep icons along progress bar
    for i in range(total):
        ix = rect.x + 14 + int((w - 28) * i / max(1, total - 1))
        iy = rect.y + 84
        col = ui.SUCCESS if i < penned else (ui.DANGER if i >= alive else ui.TEXT_MUTED)
        pygame.draw.circle(surface, col, (ix, iy + 4), 4)
        pygame.draw.circle(surface, ui.BORDER_PIXEL, (ix, iy + 4), 4, 1)


# =============================================================================
# Dog card
# =============================================================================
def _draw_dog_card(surface, dogs):
    if not dogs:
        return

    w = 240
    row_h = 42
    pad_top = 30
    pad_bot = 12
    h = pad_top + row_h * len(dogs) + pad_bot
    x = cfg.SCREEN_WIDTH - w - 14
    y = 14 + 118 + 10
    rect = pygame.Rect(x, y, w, h)
    ui.draw_glass_card(surface, rect, radius=8)

    hdr = ui.render_text(f"DOGS ({len(dogs)})", 9, ui.TEXT_MUTED, "bold")
    surface.blit(hdr, (rect.x + 14, rect.y + 10))
    ui.draw_divider(surface, rect.x + 14, rect.y + 24, w - 28)

    row_y = rect.y + pad_top
    for d in dogs:
        # dog name
        name_col = ui.COLOR_DOG
        name_surf = ui.render_text(d.name.upper(), 11, name_col, "bold")
        surface.blit(name_surf, (rect.x + 14, row_y))

        # paw icon (small circle)
        pygame.draw.circle(surface, name_col, (rect.x + 14 + name_surf.get_width() + 8, row_y + 5), 4)
        pygame.draw.circle(surface, ui.BORDER_PIXEL, (rect.x + 14 + name_surf.get_width() + 8, row_y + 5), 4, 1)

        # state pill
        sc = _dog_state_color(d.fsm.state)
        # pill bg uses 4-tuple for transparency
        pill_bg = (sc[0], sc[1], sc[2], 55)
        ui.draw_pill(surface, d.fsm.state,
                     (rect.x + 14 + name_surf.get_width() + 18, row_y - 3),
                     size=9, bg=pill_bg, fg=sc, border=sc, padding=(7, 3))

        # stamina bar
        bar_col = (ui.SUCCESS if d.stamina > 40
                   else ui.WARNING if d.stamina > 15 else ui.DANGER)
        bar = pygame.Rect(rect.x + 14, row_y + 20, w - 28, 6)
        ui.draw_progress_bar(surface, bar, d.stamina, cfg.DOG_MAX_STAMINA,
                             fg=bar_col)

        row_y += row_h


# =============================================================================
# Environment card
# =============================================================================
def _draw_environment_card(surface, world):
    w = 240
    h = 76
    x = cfg.SCREEN_WIDTH - w - 14
    dogs_h = 30 + 42 * max(1, len(world.dogs)) + 12
    y = 14 + 118 + 10 + dogs_h + 10
    rect = pygame.Rect(x, y, w, h)
    ui.draw_glass_card(surface, rect, radius=8)

    hdr = ui.render_text("ENVIRONMENT", 9, ui.TEXT_MUTED, "bold")
    surface.blit(hdr, (rect.x + 14, rect.y + 10))
    ui.draw_divider(surface, rect.x + 14, rect.y + 24, w - 28)

    # weather pill
    weather = world.weather.state
    wc = _weather_color(weather)
    wpill = ui.draw_pill(surface, weather,
                          (rect.x + 14, rect.y + 30),
                          size=10, bg=(wc[0], wc[1], wc[2], 55),
                          fg=wc, border=wc, padding=(8, 3))

    # time of day pill
    tlabel = world.day_night.label()
    tc = _time_color(tlabel)
    ui.draw_pill(surface, tlabel,
                 (rect.x + 14 + wpill.w + 6, rect.y + 30),
                 size=10, bg=(tc[0], tc[1], tc[2], 55),
                 fg=tc, border=tc, padding=(8, 3))

    # timer
    t = int(world.elapsed_time)
    total = int(cfg.SIMULATION_TIME_LIMIT)
    mm, ss = t // 60, t % 60
    tmm, tss = total // 60, total % 60
    # colour goes amber then red as time runs out
    remaining = total - t
    tc2 = ui.DANGER if remaining < 30 else (ui.WARNING if remaining < 60 else ui.TEXT_SECONDARY)
    time_surf = ui.render_text(f"{mm:02d}:{ss:02d}  /  {tmm:02d}:{tss:02d}",
                                11, tc2, "bold")
    surface.blit(time_surf, (rect.x + 14, rect.y + h - time_surf.get_height() - 8))


# =============================================================================
# Controls strip  (bottom-center)
# =============================================================================
def _draw_controls_strip(surface, debug_on, rubric_on):
    controls = [
        ("LMB",   "Move you"),
        ("RMB",   "Command dog"),
        ("H",     "Herd mode"),
        ("SPACE", "Whistle"),
        ("F1",    "Debug"),
        ("F2",    "Rubric"),
        ("R",     "Reset"),
    ]

    cap_gap = 5
    group_gap = 16
    cap_size = 10
    lbl_size = 10
    pad_x = 14

    total_w = 0
    max_h = 0
    for key, lbl in controls:
        ks = ui.render_text(key, cap_size, ui.TEXT_PRIMARY, "bold")
        ls = ui.render_text(lbl, lbl_size, ui.TEXT_SECONDARY)
        kw = max(ks.get_width() + 14, 28)
        kh = ks.get_height() + 10
        total_w += kw + cap_gap + ls.get_width() + group_gap
        max_h = max(max_h, kh)
    total_w -= group_gap
    strip_h = max_h + 14

    card_w = total_w + pad_x * 2
    card_x = (cfg.SCREEN_WIDTH - card_w) // 2
    card_y = cfg.SCREEN_HEIGHT - strip_h - 12
    rect = pygame.Rect(card_x, card_y, card_w, strip_h)
    ui.draw_glass_card(surface, rect, radius=strip_h // 2)

    cx_draw = rect.x + pad_x
    cy = rect.y + rect.h // 2
    for key, lbl in controls:
        ks = ui.render_text(key, cap_size, ui.TEXT_PRIMARY, "bold")
        kw = max(ks.get_width() + 14, 28)
        kh = ks.get_height() + 10
        cap_rect = ui.draw_keycap(surface, key, (cx_draw, cy - kh // 2), size=cap_size)
        ls = ui.render_text(lbl, lbl_size, ui.TEXT_SECONDARY)
        surface.blit(ls, (cx_draw + kw + cap_gap, cy - ls.get_height() // 2))
        cx_draw += kw + cap_gap + ls.get_width() + group_gap


# =============================================================================
# FPS
# =============================================================================
def _draw_fps(surface, fps):
    t = ui.render_text(f"{int(fps)} fps", 10, ui.TEXT_MUTED)
    surface.blit(t, (cfg.SCREEN_WIDTH - t.get_width() - 14, 4))


# =============================================================================
# Color helpers
# =============================================================================
def _dog_state_color(state):
    return {
        "IDLE":         ui.TEXT_SECONDARY,
        "PATROLLING":   ui.INFO,
        "HERDING":      ui.ACCENT,
        "CHASING_WOLF": ui.DANGER,
        "RETURNING":    ui.WARNING,
        "RESTING":      ui.TEXT_MUTED,
        "EXHAUSTED":    ui.DANGER,
    }.get(state, ui.TEXT_SECONDARY)


def _weather_color(weather):
    return {
        "CLEAR":  ui.WARNING,
        "CLOUDY": ui.TEXT_SECONDARY,
        "RAIN":   ui.INFO,
        "STORM":  ui.DANGER,
        "FOG":    ui.TEXT_MUTED,
    }.get(weather, ui.TEXT_SECONDARY)


def _time_color(label):
    return {
        "DAY":   ui.WARNING,
        "DAWN":  (255, 165, 120),
        "DUSK":  (200, 120, 180),
        "NIGHT": (130, 140, 200),
    }.get(label, ui.TEXT_SECONDARY)


# =============================================================================
# Title screen
# =============================================================================
def draw_title_screen(surface):
    # warm earthy gradient background
    ui.draw_vertical_gradient(
        surface, surface.get_rect(),
        ui.BG_DEEP, (30, 50, 20),
    )

    # pixel-art fence post decoration (left and right)
    _draw_fence_decoration(surface)

    cx = cfg.SCREEN_WIDTH // 2
    cy = cfg.SCREEN_HEIGHT // 2

    # eyebrow
    _draw_centered_eyebrow(surface, "FARM  AI  SIMULATION", cy - 130,
                           size=11, color=ui.ACCENT)

    # title in warm cream
    title = ui.render_text("Sheep Dog", 80, ui.TEXT_PRIMARY, "bold")
    surface.blit(title, (cx - title.get_width() // 2, cy - 100))

    # subtitle
    sub = ui.render_text("Intelligent agents.  Dynamic weather.  No two runs alike.",
                         15, ui.TEXT_SECONDARY)
    surface.blit(sub, (cx - sub.get_width() // 2, cy + 0))

    # CTA — warm wood button
    cta_text = "Press  ENTER  to begin"
    cta_surf = ui.render_text(cta_text, 14, ui.TEXT_PRIMARY, "bold")
    pad = (22, 12)
    cta_w = cta_surf.get_width() + pad[0] * 2
    cta_h = cta_surf.get_height() + pad[1] * 2
    cta_rect = pygame.Rect(cx - cta_w // 2, cy + 52, cta_w, cta_h)
    ui.draw_card(surface, cta_rect, bg=ui.BG_ELEVATED,
                 border=ui.ACCENT, radius=cta_h // 2, shadow=True)
    surface.blit(cta_surf, (cta_rect.x + pad[0], cta_rect.y + pad[1]))

    # footer
    footer = ui.render_text("Built with pygame  -  Press ESC to quit",
                             11, ui.TEXT_MUTED)
    surface.blit(footer, (cx - footer.get_width() // 2,
                           cfg.SCREEN_HEIGHT - 32))


def _draw_fence_decoration(surface):
    """Draw simple pixel-art fence posts along left & right edges of title screen."""
    post_w, post_h = 18, 60
    gap = 80
    for y in range(0, cfg.SCREEN_HEIGHT, gap):
        # left post
        r = pygame.Rect(16, y + 10, post_w, post_h)
        pygame.draw.rect(surface, ui.BG_ELEVATED, r, border_radius=3)
        pygame.draw.rect(surface, ui.BORDER_PIXEL, r, 2, border_radius=3)
        # right post
        r2 = pygame.Rect(cfg.SCREEN_WIDTH - 16 - post_w, y + 10, post_w, post_h)
        pygame.draw.rect(surface, ui.BG_ELEVATED, r2, border_radius=3)
        pygame.draw.rect(surface, ui.BORDER_PIXEL, r2, 2, border_radius=3)
    # horizontal rails
    for ry in [cfg.SCREEN_HEIGHT // 3, cfg.SCREEN_HEIGHT * 2 // 3]:
        pygame.draw.rect(surface, ui.BG_CARD,
                         pygame.Rect(16 + post_w, ry, 40, 8), border_radius=2)
        pygame.draw.rect(surface, ui.BORDER_PIXEL,
                         pygame.Rect(16 + post_w, ry, 40, 8), 2, border_radius=2)
        pygame.draw.rect(surface, ui.BG_CARD,
                         pygame.Rect(cfg.SCREEN_WIDTH - 16 - post_w - 40, ry,
                                     40, 8), border_radius=2)
        pygame.draw.rect(surface, ui.BORDER_PIXEL,
                         pygame.Rect(cfg.SCREEN_WIDTH - 16 - post_w - 40, ry,
                                     40, 8), 2, border_radius=2)


def _draw_centered_eyebrow(surface, text, y, size, color):
    spacing = 2
    chars = []
    total_w = 0
    for ch in text:
        s = ui.render_text(ch, size, color, "bold")
        chars.append(s)
        total_w += s.get_width() + spacing
    total_w -= spacing
    x = cfg.SCREEN_WIDTH // 2 - total_w // 2
    for s in chars:
        surface.blit(s, (x, y))
        x += s.get_width() + spacing


# =============================================================================
# Ending screen
# =============================================================================
ENDING_DATA = {
    "ALL_SAVED":      {"title": "Perfect Run!",    "subtitle": "All sheep safely penned.",
                       "color": "SUCCESS", "icon": "OK"},
    "PARTIAL_WIN":    {"title": "Success!",         "subtitle": "Most of the flock made it home.",
                       "color": "SUCCESS", "icon": "OK"},
    "PARTIAL_LOSS":   {"title": "Too Few Saved",    "subtitle": "Not enough sheep reached the pen.",
                       "color": "WARNING", "icon": "!"},
    "WOLVES_WIN":     {"title": "The Wolves Won",   "subtitle": "Every sheep was lost.",
                       "color": "DANGER",  "icon": "X"},
    "DOG_EXHAUSTED":  {"title": "Dog Collapsed",    "subtitle": "Rex ran himself to exhaustion.",
                       "color": "WARNING", "icon": "!"},
}


def draw_ending_screen(surface, world):
    ui.draw_vertical_gradient(surface, surface.get_rect(),
                               ui.BG_DEEP, (25, 42, 18))

    data = ENDING_DATA.get(world.ending, ENDING_DATA["PARTIAL_LOSS"])
    color = {"SUCCESS": ui.SUCCESS, "WARNING": ui.WARNING,
             "DANGER": ui.DANGER}[data["color"]]
    cx = cfg.SCREEN_WIDTH // 2

    # icon circle — wood panel look
    icon_r = 38
    icon_cy = 148
    pygame.draw.circle(surface, ui.BG_CARD, (cx, icon_cy), icon_r)
    pygame.draw.circle(surface, color, (cx, icon_cy), icon_r, 4)
    icon_s = ui.render_text(data["icon"], 32, color, "bold")
    surface.blit(icon_s, (cx - icon_s.get_width() // 2,
                           icon_cy - icon_s.get_height() // 2))

    # title
    title_s = ui.render_text(data["title"], 46, ui.TEXT_PRIMARY, "bold")
    surface.blit(title_s, (cx - title_s.get_width() // 2, 208))

    sub_s = ui.render_text(data["subtitle"], 16, ui.TEXT_SECONDARY)
    surface.blit(sub_s, (cx - sub_s.get_width() // 2, 268))

    # stats cards
    alive  = sum(1 for s in world.sheep if s.alive)
    penned = sum(1 for s in world.sheep if s.alive and world.is_in_pen(s.pos))
    lost   = len(world.sheep) - alive
    wolves_alive = sum(1 for w in world.wolves if w.alive)

    stats = [
        ("PENNED", str(penned), ui.SUCCESS),
        ("LOST",   str(lost),   ui.DANGER),
        ("WOLVES", str(wolves_alive), ui.TEXT_SECONDARY),
        ("TIME",   f"{int(world.elapsed_time)}s", ui.TEXT_SECONDARY),
    ]
    card_w, card_h = 128, 96
    gap = 14
    total_w = card_w * len(stats) + gap * (len(stats) - 1)
    sx = cx - total_w // 2
    for i, (label, val, c) in enumerate(stats):
        r = pygame.Rect(sx + i * (card_w + gap), 328, card_w, card_h)
        ui.draw_card(surface, r, radius=8)
        ls = ui.render_text(label, 10, ui.TEXT_MUTED, "bold")
        surface.blit(ls, (r.x + (r.w - ls.get_width()) // 2, r.y + 12))
        vs = ui.render_text(val, 32, c, "bold")
        surface.blit(vs, (r.x + (r.w - vs.get_width()) // 2, r.y + 36))

    cta = ui.render_text("Press  R  to play again   —   ESC  to quit",
                          13, ui.TEXT_MUTED)
    surface.blit(cta, (cx - cta.get_width() // 2, cfg.SCREEN_HEIGHT - 72))