"""
Renderer - pixel-art style agent and world drawing.

Each agent has a hand-crafted pixel-art silhouette:
  Sheep : fluffy white body, black face, four stubby legs
  Dog   : brown/grey elongated body, pointed snout, perky ears, wagging tail
  Wolf  : dark menacing body, glowing eyes, raised hackles, pointed ears
  Owner : top-down farmer — hat, coat, visible arms
"""

import math
import pygame
from ..core import settings as cfg
from ..world import world as world_mod


# ── visual scale ─────────────────────────────────────────────────────────────
# Multiplier applied to agent.radius for DRAWING only.
# Collision radius in settings.py stays the same so gameplay is unaffected.
_DRAW_SCALE = 1.2    # increase this to make all characters bigger
_WOOL        = (242, 240, 228)
_WOOL_SHADE  = (200, 198, 186)
_SHEEP_FACE  = (50,  42,  36)
_SHEEP_LEG   = (80,  70,  60)

_DOG_BODY    = (160, 112, 64)
_DOG_DARK    = (110,  74, 38)
_DOG_MUZZLE  = (190, 148, 96)
_DEF_BODY    = (72,  58,  78)       # defender dog
_DEF_DARK    = (48,  36,  54)

_WOLF_BODY   = (78,  72,  88)
_WOLF_DARK   = (48,  44,  58)
_WOLF_BELLY  = (120, 110, 130)
_WOLF_EYE    = (230, 190,  30)
_WOLF_EYE_R  = (220,  60,  50)

_OWN_COAT    = (180,  60,  60)
_OWN_SKIN    = (228, 192, 148)
_OWN_HAT     = (72,  50,  28)
_OWN_HAT2    = (100,  70,  38)

_BLACK       = (20,  16,  14)
_WHITE       = (255, 255, 255)
_OUTLINE     = (30,  24,  18)


# ── helpers ──────────────────────────────────────────────────────────────────
def _rot(cx, cy, px, py, angle_rad):
    """Rotate point (px,py) around (cx,cy)."""
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    dx, dy = px - cx, py - cy
    return (cx + dx * cos_a - dy * sin_a,
            cy + dx * sin_a + dy * cos_a)


def _poly(surface, color, pts, width=0):
    if len(pts) >= 3:
        pygame.draw.polygon(surface, color,
                            [(int(p[0]), int(p[1])) for p in pts], width)


def _circ(surface, color, cx, cy, r, width=0):
    pygame.draw.circle(surface, color, (int(cx), int(cy)), max(1, r), width)


def _ellipse(surface, color, cx, cy, rx, ry, angle_rad=0, width=0):
    """Draw an axis-aligned ellipse (rotation via surface blit)."""
    if rx <= 0 or ry <= 0:
        return
    surf = pygame.Surface((rx * 2 + 2, ry * 2 + 2), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, color, surf.get_rect(), width)
    rotated = pygame.transform.rotate(surf, -math.degrees(angle_rad))
    rx2, ry2 = rotated.get_size()
    surface.blit(rotated, (int(cx - rx2 // 2), int(cy - ry2 // 2)))


# ============================================================================
# TILE / WORLD DRAWING
# ============================================================================
def draw_world(surface, world):
    surface.fill(cfg.GRASS_GREEN)

    ts = cfg.TILE_SIZE

    for row in range(cfg.WORLD_ROWS):
        for col in range(cfg.WORLD_COLS):
            tile = world.tiles[row][col]
            x, y = col * ts, row * ts
            rect = pygame.Rect(x, y, ts, ts)

            if tile == world_mod.GRASS:
                # subtle texture variation
                _draw_grass_tile(surface, x, y, ts, dark=False)

            elif tile == world_mod.GRASS_DARK:
                _draw_grass_tile(surface, x, y, ts, dark=True)

            elif tile == world_mod.DIRT:
                pygame.draw.rect(surface, cfg.DIRT, rect)
                # dirt pebble texture
                import random as _r
                rng = _r.Random(col * 1000 + row)
                for _ in range(3):
                    px = x + rng.randint(4, ts - 4)
                    py = y + rng.randint(4, ts - 4)
                    pygame.draw.circle(surface, (140, 110, 75), (px, py), 2)

            elif tile == world_mod.WATER:
                _draw_water_tile(surface, x, y, ts)

            elif tile == world_mod.PRECIPICE:
                pygame.draw.rect(surface, cfg.PRECIPICE, rect)
                pygame.draw.rect(surface, _BLACK, rect, 2)
                # hatching
                for i in range(0, ts, 6):
                    pygame.draw.line(surface, (20, 16, 14),
                                     (x + i, y), (x, y + i), 1)

            elif tile == world_mod.TREE:
                _draw_tree_tile(surface, x, y, ts)

            elif tile == world_mod.ROCK:
                _draw_rock_tile(surface, x, y, ts)

            elif tile == world_mod.FENCE:
                _draw_fence_tile(surface, x, y, ts)

            elif tile == world_mod.PEN:
                _draw_pen_tile(surface, x, y, ts)


def _draw_grass_tile(surface, x, y, ts, dark=False):
    base = cfg.GRASS_DARK if dark else cfg.GRASS_GREEN
    pygame.draw.rect(surface, base, pygame.Rect(x, y, ts, ts))
    # tiny grass blades
    blade = (max(0, base[0] - 12), min(255, base[1] + 8), max(0, base[2] - 8))
    import random as _r
    rng = _r.Random(x * 7 + y * 13)
    for _ in range(4):
        bx = x + rng.randint(3, ts - 3)
        by = y + rng.randint(3, ts - 3)
        pygame.draw.line(surface, blade, (bx, by), (bx, by - 3), 1)


def _draw_water_tile(surface, x, y, ts):
    # base water colour
    pygame.draw.rect(surface, cfg.WATER, pygame.Rect(x, y, ts, ts))
    # animated ripple shimmer using tile position as seed
    t = (pygame.time.get_ticks() // 600 + x + y) % 4
    ripple = (100 + t * 8, 160 + t * 4, 210)
    for oy in (6, 14, 22):
        pygame.draw.line(surface, ripple,
                         (x + 4, y + oy), (x + ts - 4, y + oy), 1)
    # sparkle dot
    pygame.draw.circle(surface, (200, 230, 255),
                       (x + 8 + t * 4, y + 10), 1)


def _draw_tree_tile(surface, x, y, ts):
    pygame.draw.rect(surface, cfg.GRASS_DARK, pygame.Rect(x, y, ts, ts))
    cx, cy = x + ts // 2, y + ts // 2
    # trunk
    pygame.draw.rect(surface, (90, 58, 30),
                     pygame.Rect(cx - 4, cy + 2, 8, 12))
    pygame.draw.rect(surface, (110, 72, 40),
                     pygame.Rect(cx - 3, cy + 3, 3, 10))
    # canopy layers (pixel-art concentric)
    for r, col in [
        (12, (56, 120, 56)),
        (10, (68, 148, 68)),
        (7,  (88, 172, 80)),
        (4,  (108, 196, 96)),
    ]:
        _circ(surface, col, cx, cy - 4, r)
    # highlight dot
    _circ(surface, (128, 210, 110), cx - 3, cy - 8, 2)


def _draw_rock_tile(surface, x, y, ts):
    pygame.draw.rect(surface, cfg.GRASS_DARK, pygame.Rect(x, y, ts, ts))
    cx, cy = x + ts // 2, y + ts // 2 + 2
    # shadow
    _circ(surface, (60, 58, 64), cx + 2, cy + 2, 10)
    # main rock body
    pts = [(cx - 10, cy + 6), (cx - 12, cy),
           (cx - 6, cy - 8), (cx + 4, cy - 10),
           (cx + 12, cy - 4), (cx + 10, cy + 6)]
    _poly(surface, (105, 100, 112), pts)
    _poly(surface, (80, 76, 88), pts, 2)
    # highlight facet
    _poly(surface, (155, 150, 165),
          [(cx - 6, cy - 6), (cx + 2, cy - 8), (cx - 2, cy - 2)])


def _draw_fence_tile(surface, x, y, ts):
    pygame.draw.rect(surface, cfg.GRASS_GREEN, pygame.Rect(x, y, ts, ts))
    # post
    pygame.draw.rect(surface, (140, 100, 52),
                     pygame.Rect(x + ts // 2 - 3, y + 2, 6, ts - 4))
    pygame.draw.rect(surface, (170, 128, 72),
                     pygame.Rect(x + ts // 2 - 2, y + 2, 2, ts - 4))
    pygame.draw.rect(surface, _OUTLINE,
                     pygame.Rect(x + ts // 2 - 3, y + 2, 6, ts - 4), 1)
    # rails
    for ry in (y + 7, y + ts - 12):
        pygame.draw.rect(surface, (160, 118, 62),
                         pygame.Rect(x, ry, ts, 4))
        pygame.draw.rect(surface, (185, 140, 80),
                         pygame.Rect(x, ry, ts, 1))
        pygame.draw.rect(surface, _OUTLINE,
                         pygame.Rect(x, ry, ts, 4), 1)


def _draw_pen_tile(surface, x, y, ts):
    # warm straw/hay floor
    pygame.draw.rect(surface, (165, 188, 128), pygame.Rect(x, y, ts, ts))
    # hay texture lines
    for i in range(0, ts, 5):
        col = (145, 168, 108) if (i // 5) % 2 == 0 else (175, 198, 138)
        pygame.draw.line(surface, col, (x, y + i), (x + ts, y + i), 1)


# ============================================================================
# AGENT DRAWING
# ============================================================================
def draw_agents(surface, world):
    for s in world.sheep:
        _draw_sheep(surface, s)
    for w in world.wolves:
        _draw_wolf(surface, w)
    for d in world.dogs:
        _draw_dog(surface, d)
    _draw_owner(surface, world.owner)


# ── SHEEP ────────────────────────────────────────────────────────────────────
def _draw_sheep(surface, sheep):
    if not sheep.alive:
        x, y = int(sheep.pos.x), int(sheep.pos.y)
        # skull X mark
        pygame.draw.line(surface, (160, 40, 40), (x-5, y-5), (x+5, y+5), 2)
        pygame.draw.line(surface, (160, 40, 40), (x-5, y+5), (x+5, y-5), 2)
        _circ(surface, (100, 30, 30), x, y, 6, 1)
        return

    x, y = int(sheep.pos.x), int(sheep.pos.y)
    r = int(sheep.radius * _DRAW_SCALE)          # visual only

    # shadow
    shadow = pygame.Surface((r*3, r*2), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 50), shadow.get_rect())
    surface.blit(shadow, (x - r*3//2, y + r - 2))

    # four stubby legs
    angle = math.radians(sheep.facing_deg)
    perp = angle + math.pi / 2
    fx, fy = math.cos(angle), math.sin(angle)
    px, py = math.cos(perp), math.sin(perp)
    for sign in (-1, 1):
        for fwd in (-0.3, 0.5):
            lx = int(x + fx * r * fwd + px * sign * r * 0.55)
            ly = int(y + fy * r * fwd + py * sign * r * 0.55)
            pygame.draw.line(surface, _SHEEP_LEG, (lx, ly), (lx, ly + 5), 3)

    # fluffy wool body (3 overlapping circles)
    _circ(surface, _WOOL_SHADE, x, y, r)
    _circ(surface, _WOOL, x - int(fx * 2), y - int(fy * 2), r - 1)
    _circ(surface, _WOOL, x + int(fx * 2), y + int(fy * 2), r - 2)
    # wool highlight
    _circ(surface, (255, 254, 245),
          x - int(fx * 2) - int(px * 1), y - int(fy * 2) - int(py * 1),
          max(2, r // 3))

    # head (small dark oval toward facing direction)
    hx = int(x + fx * (r + 3))
    hy = int(y + fy * (r + 3))
    _circ(surface, _SHEEP_FACE, hx, hy, 4)
    # ear nubs
    _circ(surface, (200, 160, 140),
          int(hx - px * 3), int(hy - py * 3), 2)
    _circ(surface, (200, 160, 140),
          int(hx + px * 3), int(hy + py * 3), 2)
    # eye
    _circ(surface, _WHITE, int(hx + fx * 1), int(hy + fy * 1), 2)
    _circ(surface, _BLACK, int(hx + fx * 1), int(hy + fy * 1), 1)

    # pen badge
    if sheep.fsm.state == "PENNED":
        _circ(surface, (80, 200, 80), x, y - r - 5, 3)
        _circ(surface, _WHITE, x, y - r - 5, 3, 1)

    _draw_emotion_tag(surface, sheep)
    _draw_speech(surface, sheep)


# ── DOG ──────────────────────────────────────────────────────────────────────
def _draw_dog(surface, dog):
    if dog is None:
        return
    x, y = int(dog.pos.x), int(dog.pos.y)

    if not dog.alive:
        _circ(surface, (80, 60, 40), x, y, dog.radius + 2, 2)
        return

    is_defender = getattr(dog, "role", "herder") == "defender"
    body  = _DOG_BODY
    dark  = _DOG_DARK
    muzz  = _DOG_MUZZLE

    angle = math.radians(dog.facing_deg)
    fx, fy = math.cos(angle), math.sin(angle)
    px, py = -math.sin(angle), math.cos(angle)
    r = int(dog.radius * _DRAW_SCALE)    # visual only

    # shadow
    shadow = pygame.Surface((r*3, r*2), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
    surface.blit(shadow, (x - r*3//2, y + r - 2))

    # tail (opposite facing, wagging offset)
    wag = math.sin(pygame.time.get_ticks() * 0.008) * 0.4
    tail_base_x = x - int(fx * r)
    tail_base_y = y - int(fy * r)
    tail_tip_x  = tail_base_x - int((fx * 0.3 + py * (0.8 + wag)) * r * 1.4)
    tail_tip_y  = tail_base_y - int((fy * 0.3 - px * (0.8 + wag)) * r * 1.4)
    pygame.draw.line(surface, dark,
                     (tail_base_x, tail_base_y),
                     (tail_tip_x, tail_tip_y), 3)

    # four legs
    for sign in (-1, 1):
        for fwd in (-0.4, 0.4):
            lx = int(x + fx * r * fwd + px * sign * r * 0.6)
            ly = int(y + fy * r * fwd + py * sign * r * 0.6)
            pygame.draw.line(surface, dark, (lx, ly), (lx + int(fy*4), ly + int(-fx*4) + 5), 3)

    # body (two overlapping circles)
    body_cx = x - int(fx * 2)
    body_cy = y - int(fy * 2)
    _circ(surface, body, body_cx, body_cy, r)
    _circ(surface, body, x + int(fx * 2), y + int(fy * 2), r - 2)

    # belly highlight
    _circ(surface, (min(255, body[0]+30), min(255, body[1]+22), min(255, body[2]+16)),
          body_cx - int(px), body_cy - int(py), max(2, r // 3))

    # head
    hx = int(x + fx * (r + 2))
    hy = int(y + fy * (r + 2))
    _circ(surface, body, hx, hy, r - 2)

    # ears (two triangles pointing up from head)
    for sign in (-1, 1):
        ex = int(hx + px * sign * 4 - fx * 2)
        ey = int(hy + py * sign * 4 - fy * 2)
        _circ(surface, dark, ex, ey, 4)
        _circ(surface, (200, 160, 130) if not is_defender else (160, 140, 170),
              ex, ey, 2)

    # muzzle
    mz_x = int(hx + fx * 5)
    mz_y = int(hy + fy * 5)
    _circ(surface, muzz, mz_x, mz_y, 3)
    # nose
    _circ(surface, _BLACK, mz_x, mz_y, 2)
    # eyes
    for sign in (-1, 1):
        ex = int(hx + fx * 2 + px * sign * 3)
        ey = int(hy + fy * 2 + py * sign * 3)
        _circ(surface, _WHITE, ex, ey, 2)
        _circ(surface, _BLACK, ex, ey, 1)

    # collar (state color ring)
    collar = _state_color_dog(dog.fsm.state)
    _circ(surface, collar, x, y, r + 4, 2)

    _draw_stamina_bar(surface, dog)
    _draw_emotion_tag(surface, dog)
    _draw_speech(surface, dog)


# ── WOLF ─────────────────────────────────────────────────────────────────────
def _draw_wolf(surface, wolf):
    if not wolf.alive:
        return

    x, y = int(wolf.pos.x), int(wolf.pos.y)
    angle = math.radians(wolf.facing_deg)
    fx, fy = math.cos(angle), math.sin(angle)
    px, py = -math.sin(angle), math.cos(angle)
    r = int(wolf.radius * _DRAW_SCALE)    # visual only

    is_charging = wolf.fsm.state in ("CHARGE", "STALK")
    eye_col = _WOLF_EYE_R if is_charging else _WOLF_EYE

    # shadow
    shadow = pygame.Surface((r*3, r*2), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
    surface.blit(shadow, (x - r*3//2, y + r - 2))

    # tail (straighter than dog, low and menacing)
    tail_tip_x = x - int(fx * r * 2.2) + int(py * r * 0.4)
    tail_tip_y = y - int(fy * r * 2.2) - int(px * r * 0.4)
    pygame.draw.line(surface, _WOLF_DARK,
                     (x - int(fx*r), y - int(fy*r)),
                     (tail_tip_x, tail_tip_y), 4)

    # legs (four, closer to body)
    for sign in (-1, 1):
        for fwd in (-0.3, 0.5):
            lx = int(x + fx * r * fwd + px * sign * r * 0.55)
            ly = int(y + fy * r * fwd + py * sign * r * 0.55)
            pygame.draw.line(surface, _WOLF_DARK, (lx, ly),
                             (lx + int(fy*5), ly + int(-fx*5) + 6), 3)

    # body
    body_cx = x - int(fx * 2)
    body_cy = y - int(fy * 2)
    _circ(surface, _WOLF_BODY, body_cx, body_cy, r)
    _circ(surface, _WOLF_BODY, x + int(fx*2), y + int(fy*2), r - 2)
    # belly (lighter underside)
    _circ(surface, _WOLF_BELLY, body_cx, body_cy, r - 4)

    # hackle ridge when stalking/charging
    if is_charging:
        for i in range(-2, 3):
            hk_x = int(body_cx + px * i * 3 - fx * 2)
            hk_y = int(body_cy + py * i * 3 - fy * 2)
            pygame.draw.line(surface, _WOLF_DARK,
                             (hk_x, hk_y), (hk_x - int(fy*4), hk_y + int(fx*4)), 2)

    # head (larger, more angular)
    hx = int(x + fx * (r + 3))
    hy = int(y + fy * (r + 3))
    _circ(surface, _WOLF_BODY, hx, hy, r - 1)

    # pointed ears
    for sign in (-1, 1):
        ear_base_x = int(hx + px * sign * 5)
        ear_base_y = int(hy + py * sign * 5)
        ear_tip_x  = int(ear_base_x - fx * 7 + px * sign * 3)
        ear_tip_y  = int(ear_base_y - fy * 7 + py * sign * 3)
        _poly(surface, _WOLF_DARK,
              [(ear_base_x - 3, ear_base_y),
               (ear_base_x + 3, ear_base_y),
               (ear_tip_x, ear_tip_y)])
        _poly(surface, (140, 80, 90),
              [(ear_base_x - 1, ear_base_y),
               (ear_base_x + 1, ear_base_y),
               (ear_tip_x, ear_tip_y)])

    # snout
    snout_x = int(hx + fx * 7)
    snout_y = int(hy + fy * 7)
    _circ(surface, _WOLF_BELLY, snout_x, snout_y, 4)
    _circ(surface, _BLACK, snout_x, snout_y, 2)   # nose

    # glowing eyes
    for sign in (-1, 1):
        ex = int(hx + fx * 3 + px * sign * 3)
        ey = int(hy + fy * 3 + py * sign * 3)
        if is_charging:
            _circ(surface, (*eye_col, 120) if False else eye_col, ex, ey, 3)
        _circ(surface, eye_col, ex, ey, 2)
        _circ(surface, _BLACK, ex, ey, 1)

    # state ring
    outline = _state_color_wolf(wolf.fsm.state)
    _circ(surface, outline, x, y, r + 4, 2)

    _draw_emotion_tag(surface, wolf)
    _draw_speech(surface, wolf)


# ── OWNER ─────────────────────────────────────────────────────────────────────
def _draw_owner(surface, owner):
    if owner is None:
        return
    x, y = int(owner.pos.x), int(owner.pos.y)
    r = int(owner.radius * _DRAW_SCALE)    # visual only

    # herd-mode aura
    if getattr(owner, "herd_mode", False):
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.004)) * 0.4 + 0.55
        aura_r = int(cfg.OWNER_HERD_RADIUS)
        aura_surf = pygame.Surface((aura_r*2+4, aura_r*2+4), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, (80, 220, 100, int(50*pulse)),
                           (aura_r+2, aura_r+2), aura_r)
        pygame.draw.circle(aura_surf, (80, 220, 100, int(100*pulse)),
                           (aura_r+2, aura_r+2), aura_r, 2)
        surface.blit(aura_surf, (x - aura_r - 2, y - aura_r - 2))

    angle = math.radians(owner.facing_deg)
    fx, fy = math.cos(angle), math.sin(angle)
    px, py = -math.sin(angle), math.cos(angle)

    # shadow
    shadow = pygame.Surface((r*3, r*2), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
    surface.blit(shadow, (x - r*3//2, y + r - 2))

    # legs
    for sign in (-1, 1):
        lx = int(x + px * sign * 4)
        ly = int(y + py * sign * 4 + 4)
        pygame.draw.line(surface, (80, 55, 30), (lx, ly), (lx, ly + 7), 4)
        # boot
        pygame.draw.line(surface, (50, 35, 18), (lx, ly + 7),
                         (lx + int(fx * 3), ly + 7), 3)

    # coat body (red circle)
    _circ(surface, _OWN_COAT, x, y, r)
    _circ(surface, (200, 75, 75), x - int(px*2), y - int(py*2), r - 3)

    # arms
    for sign in (-1, 1):
        arm_x = int(x + px * sign * r)
        arm_y = int(y + py * sign * r)
        end_x = int(arm_x + px * sign * 5 + fx * 3)
        end_y = int(arm_y + py * sign * 5 + fy * 3)
        pygame.draw.line(surface, _OWN_COAT, (arm_x, arm_y), (end_x, end_y), 4)
        _circ(surface, _OWN_SKIN, end_x, end_y, 3)

    # head
    hx = int(x - int(fx * 4))
    hy = int(y - int(fy * 4) - r)
    _circ(surface, _OWN_SKIN, hx, hy, 6)

    # hat brim
    pygame.draw.rect(surface, _OWN_HAT,
                     pygame.Rect(hx - 9, hy - 3, 18, 3))
    # hat crown
    pygame.draw.rect(surface, _OWN_HAT2,
                     pygame.Rect(hx - 6, hy - 10, 12, 8))
    pygame.draw.rect(surface, _OWN_HAT,
                     pygame.Rect(hx - 6, hy - 10, 12, 8), 1)
    # hat band
    pygame.draw.rect(surface, (60, 40, 18),
                     pygame.Rect(hx - 6, hy - 4, 12, 2))

    # eyes
    for sign in (-1, 1):
        _circ(surface, _BLACK, int(hx + px*sign*2), int(hy + py*sign*2 + 1), 1)

    # herd mode badge
    if getattr(owner, "herd_mode", False):
        _circ(surface, (60, 220, 80), x + r - 2, y - 3, 4)
        _circ(surface, _WHITE, x + r - 2, y - 3, 4, 1)

    _draw_speech(surface, owner)


# ============================================================================
# HELPER DRAWERS
# ============================================================================
def _state_color_dog(state):
    return {
        "IDLE":         cfg.GREEN,
        "PATROLLING":   (150, 220, 150),
        "HERDING":      cfg.YELLOW,
        "CHASING_WOLF": cfg.RED,
        "RETURNING":    cfg.BLUE,
        "RESTING":      cfg.GRAY,
        "EXHAUSTED":    cfg.DARK_GRAY,
    }.get(state, cfg.WHITE)


def _state_color_wolf(state):
    return {
        "PATROL":  cfg.GRAY,
        "STALK":   cfg.ORANGE,
        "CHARGE":  cfg.RED,
        "FLEE":    cfg.BLUE,
        "RESTING": cfg.DARK_GRAY,
    }.get(state, cfg.WHITE)


def _draw_stamina_bar(surface, dog):
    x, y = int(dog.pos.x), int(dog.pos.y)
    draw_r = int(dog.radius * _DRAW_SCALE)
    bar_w, bar_h = 28, 4
    bx = x - bar_w // 2
    by = y - draw_r - 10
    pct = dog.stamina / cfg.DOG_MAX_STAMINA
    # trough
    pygame.draw.rect(surface, (30, 22, 14), (bx, by, bar_w, bar_h))
    pygame.draw.rect(surface, (60, 46, 28), (bx, by, bar_w, bar_h), 1)
    # fill
    color = cfg.GREEN if pct > 0.4 else cfg.YELLOW if pct > 0.15 else cfg.RED
    fw = max(0, int(bar_w * pct))
    if fw:
        pygame.draw.rect(surface, color, (bx, by, fw, bar_h))
        # highlight
        pygame.draw.line(surface,
                         (min(255, color[0]+60), min(255, color[1]+60), min(255, color[2]+40)),
                         (bx, by+1), (bx+fw-1, by+1))


def _draw_emotion_tag(surface, agent):
    if agent.emotion.fear > 40:
        col = cfg.BLUE
    elif agent.emotion.anger > 40:
        col = cfg.RED
    elif agent.emotion.happiness > 70:
        col = cfg.GREEN
    else:
        return
    x = int(agent.pos.x)
    y = int(agent.pos.y - agent.radius - 15)
    _circ(surface, col, x, y, 3)
    _circ(surface, _WHITE, x, y, 3, 1)


def _draw_speech(surface, agent):
    if agent.speech is None:
        return
    from . import ui_theme as ui
    text = ui.render_text(agent.speech, 11, ui.TEXT_PRIMARY, "bold")
    tw, th = text.get_size()
    pad_x, pad_y = 7, 4
    w = tw + pad_x * 2
    h = th + pad_y * 2
    bx = int(agent.pos.x - w // 2)
    by = int(agent.pos.y - agent.radius - h - 16)

    panel = pygame.Surface((w + 4, h + 8), pygame.SRCALPHA)
    # shadow
    pygame.draw.rect(panel, (0, 0, 0, 80),
                     pygame.Rect(2, 3, w, h), border_radius=6)
    # bubble body — warm wood tone
    pygame.draw.rect(panel, (*ui.BG_ELEVATED, 235),
                     pygame.Rect(0, 0, w, h), border_radius=6)
    pygame.draw.rect(panel, (*ui.BORDER_PIXEL, 200),
                     pygame.Rect(0, 0, w, h), 2, border_radius=6)
    panel.blit(text, (pad_x, pad_y))
    # tail triangle
    tc = w // 2
    pygame.draw.polygon(panel, ui.BG_ELEVATED,
                        [(tc-4, h-1), (tc+4, h-1), (tc, h+5)])
    surface.blit(panel, (bx, by))