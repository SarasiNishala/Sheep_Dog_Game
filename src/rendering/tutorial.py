import math
import pygame

from ..core import settings as cfg
from . import ui_theme as ui

def draw_welcome_overlay(surface):
    """Full-screen modal explaining how to play."""
    # Dim backdrop
    bg = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    bg.fill(ui.BG_OVERLAY)
    surface.blit(bg, (0, 0))

    # Panel geometry
    panel_w = 720
    panel_h = 580
    px = (cfg.SCREEN_WIDTH - panel_w) // 2
    py = (cfg.SCREEN_HEIGHT - panel_h) // 2
    panel_rect = pygame.Rect(px, py, panel_w, panel_h)

    ui.draw_card(surface, panel_rect, radius=16)

    # Accent corner bar
    bar = pygame.Surface((4, 80), pygame.SRCALPHA)
    bar.fill(ui.ACCENT)
    surface.blit(bar, (px, py + 36))

    # Eyebrow
    ui.draw_section_title(
        surface, "AI AGENT SIMULATION",
        (px + 32, py + 38), size=10, color=ui.ACCENT,
    )

    # Title
    title_surf = ui.render_text(
        "Sheep Dog", 42, ui.TEXT_PRIMARY, "bold",
    )
    surface.blit(title_surf, (px + 32, py + 56))

    # Subtitle
    sub_surf = ui.render_text(
        "Herd the flock into the pen before the wolves arrive.",
        15, ui.TEXT_SECONDARY,
    )
    surface.blit(sub_surf, (px + 32, py + 114))

    # Two-column section: Legend | Controls
    col_y = py + 170
    col_w = (panel_w - 96) // 2

    _draw_legend_column(surface, px + 32, col_y, col_w)
    _draw_controls_column(surface, px + 64 + col_w, col_y, col_w)

    # Bottom: tip
    tip_y = py + panel_h - 100
    tip_rect = pygame.Rect(px + 32, tip_y, panel_w - 64, 52)
    tip_overlay = pygame.Surface((tip_rect.w, tip_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(
        tip_overlay, (*ui.ACCENT, 18),
        tip_overlay.get_rect(), border_radius=8,
    )
    pygame.draw.rect(
        tip_overlay, ui.ACCENT,
        tip_overlay.get_rect(), 1, border_radius=8,
    )
    surface.blit(tip_overlay, (tip_rect.x, tip_rect.y))

    tip_label = ui.render_text("HOW TO PLAY", 10, ui.ACCENT, "bold")
    surface.blit(tip_label, (tip_rect.x + 16, tip_rect.y + 10))
    tip_text = ui.render_text(
        "Left-click to move yourself.  Right-click a sheep / wolf / spot to command the dog.",
        13, ui.TEXT_PRIMARY,
    )
    surface.blit(tip_text, (tip_rect.x + 16, tip_rect.y + 28))

    # CTA
    cta_y = py + panel_h - 38
    cta_text = ui.render_text(
        "Press any key to begin", 13, ui.TEXT_MUTED,
    )
    surface.blit(
        cta_text,
        ((cfg.SCREEN_WIDTH - cta_text.get_width()) // 2, cta_y),
    )


def _draw_legend_column(surface, x, y, w):
    """Left column of the welcome modal: what's on screen."""
    ui.draw_section_title(
        surface, "ON SCREEN", (x, y), size=10, color=ui.TEXT_MUTED,
    )

    items = [
        (cfg.SHEEP_COLOR,  "Sheep",      "Herd these home"),
        (cfg.DOG_COLOR,    "Dog (Rex)",  "Autonomous"),
        (cfg.WOLF_COLOR,   "Wolf",       "Hunts sheep"),
        (cfg.OWNER_COLOR,  "Shepherd",   "You control this"),
        ((155, 180, 120),  "Pen",        "Deliver sheep here"),
    ]

    row_y = y + 24
    for color, name, desc in items:
        ui.draw_swatch(surface, (x + 10, row_y + 9), color, size=7)
        name_surf = ui.render_text(name, 14, ui.TEXT_PRIMARY, "bold")
        surface.blit(name_surf, (x + 28, row_y))
        desc_surf = ui.render_text(desc, 12, ui.TEXT_MUTED)
        surface.blit(desc_surf, (x + 28, row_y + 16))
        row_y += 40


def _draw_controls_column(surface, x, y, w):
    """Right column of the welcome modal: keyboard controls."""
    ui.draw_section_title(
        surface, "CONTROLS", (x, y), size=10, color=ui.TEXT_MUTED,
    )

    controls = [
        ("CLICK",  "Move shepherd"),
        ("RIGHT",  "Command the dog"),
        ("SPACE",  "Whistle (recall)"),
        ("H",      "Herd mode (owner)"),
        ("F1",     "Debug overlay"),
        ("F2",     "Rubric checklist"),
        ("R",      "Reset"),
    ]

    row_y = y + 24
    for key, desc in controls:
        rect = ui.draw_keycap(surface, key, (x, row_y + 3), size=11)
        desc_surf = ui.render_text(desc, 13, ui.TEXT_SECONDARY)
        surface.blit(desc_surf, (x + 80, row_y + 10))
        row_y += 40


# ---------------------------------------------------------------------------
# Compact legend (top-left corner, always visible)
# ---------------------------------------------------------------------------
def draw_compact_legend(surface):
    """Compact floating legend card in the top-left corner."""
    items = [
        (cfg.OWNER_COLOR, "You"),
        (cfg.DOG_COLOR,   "Dog"),
        (cfg.SHEEP_COLOR, "Sheep"),
        (cfg.WOLF_COLOR,  "Wolf"),
        ((155, 180, 120), "Pen"),
    ]

    row_h = 18
    header_h = 20
    pad = 12
    card_w = 124
    card_h = header_h + row_h * len(items) + pad

    rect = pygame.Rect(16, 16, card_w, card_h)
    ui.draw_glass_card(surface, rect, radius=10)

    ui.draw_section_title(
        surface, "LEGEND",
        (rect.x + 12, rect.y + 10),
        size=9, color=ui.TEXT_MUTED,
    )

    row_y = rect.y + header_h + 8
    for color, name in items:
        ui.draw_swatch(surface, (rect.x + 18, row_y + 7), color, size=5)
        name_surf = ui.render_text(name, 12, ui.TEXT_SECONDARY)
        surface.blit(name_surf, (rect.x + 32, row_y))
        row_y += row_h


# ---------------------------------------------------------------------------
# Floating arrow indicating the current goal (the pen)
# ---------------------------------------------------------------------------
def draw_pen_arrow(surface, world, elapsed_time: float):
    """Pulsing marker above the pen - disappears after first sheep penned."""
    penned = sum(
        1 for s in world.sheep
        if s.alive and world.is_in_pen(s.pos)
    )
    if penned > 0:
        return

    pen_center = world.pen_center()
    cx = int(pen_center.x)
    cy = int(pen_center.y)

    # breathing glow
    pulse = (math.sin(elapsed_time * 2.4) + 1) / 2  # 0..1

    # soft radial glow above pen
    ui.draw_radial_glow(
        surface, (cx, cy - 90),
        color=ui.ACCENT,
        radius=int(36 + 6 * pulse),
    )

    # downward-pointing chevron above pen
    chev_y = cy - 80
    chev_size = 12
    points = [
        (cx, chev_y + chev_size),
        (cx - chev_size, chev_y),
        (cx, chev_y + 4),
        (cx + chev_size, chev_y),
    ]
    pygame.draw.polygon(surface, ui.ACCENT, points)
    pygame.draw.polygon(surface, ui.BG_DEEP, points, 1)

    # label pill above chevron - skip if it would sit behind the right-edge
    # HUD cards (which occupy roughly the right 250px for the top 300px)
    pill_hidden_by_hud = (
        cx > cfg.SCREEN_WIDTH - 260 and chev_y - 24 < 310
    )
    if not pill_hidden_by_hud:
        ui.draw_pill(
            surface, "BRING SHEEP HERE",
            (cx, chev_y - 24),
            size=10,
            bg=ui.BG_CARD, fg=ui.ACCENT,
            border=ui.ACCENT,
            padding=(12, 5),
            weight="bold",
            center=True,
        )


# ---------------------------------------------------------------------------
# Objective banner (top-center)
# ---------------------------------------------------------------------------
def draw_objective_banner(surface, world):
    """Context-sensitive single-line objective at top-center of screen."""
    penned = sum(
        1 for s in world.sheep
        if s.alive and world.is_in_pen(s.pos)
    )
    alive = sum(1 for s in world.sheep if s.alive)
    wolves_near = any(
        w.alive and w.fsm.state in ("STALK", "CHARGE")
        for w in world.wolves
    )

    if world.elapsed_time < 4:
        msg = "RIGHT-click on a sheep to send the dog to herd it"
        status = ui.ACCENT
        icon = "1"
    elif penned == 0 and world.elapsed_time < 12:
        msg = "Right-click multiple sheep - the dog will drive them home"
        status = ui.ACCENT
        icon = "2"
    elif wolves_near and penned < alive:
        msg = "Wolves attacking - RIGHT-click the wolf to attack it"
        status = ui.DANGER
        icon = "!"
    elif penned < cfg.MIN_SHEEP_TO_WIN:
        msg = f"Keep herding - {penned} of {len(world.sheep)} penned"
        status = ui.WARNING
        icon = str(penned)
    else:
        msg = "Almost there - pen them all for a perfect run"
        status = ui.SUCCESS
        icon = "+"

    text_surf = ui.render_text(msg, 13, ui.TEXT_PRIMARY, "bold")
    badge_size = 24
    pad_x = 14
    pad_y = 9
    banner_w = text_surf.get_width() + badge_size + pad_x * 2 + 10
    banner_h = max(text_surf.get_height() + pad_y * 2, badge_size + pad_y)

    bx = (cfg.SCREEN_WIDTH - banner_w) // 2
    by = 16
    rect = pygame.Rect(bx, by, banner_w, banner_h)
    ui.draw_glass_card(surface, rect, radius=banner_h // 2)

    # status badge
    badge_cx = rect.x + pad_x + badge_size // 2
    badge_cy = rect.y + rect.h // 2
    badge_surf = pygame.Surface((badge_size * 2, badge_size * 2),
                                pygame.SRCALPHA)
    pygame.draw.circle(
        badge_surf, (*status, 50),
        (badge_size, badge_size), badge_size // 2 + 2,
    )
    pygame.draw.circle(
        badge_surf, status,
        (badge_size, badge_size), badge_size // 2, 1,
    )
    surface.blit(
        badge_surf,
        (badge_cx - badge_size, badge_cy - badge_size),
    )
    icon_surf = ui.render_text(icon, 11, status, "bold")
    surface.blit(
        icon_surf,
        (badge_cx - icon_surf.get_width() // 2,
         badge_cy - icon_surf.get_height() // 2),
    )

    # text
    surface.blit(
        text_surf,
        (rect.x + pad_x + badge_size + 10,
         rect.y + (rect.h - text_surf.get_height()) // 2),
    )


# ---------------------------------------------------------------------------
# Floating toast notifications
# ---------------------------------------------------------------------------
class Toast:
    """A single floating toast notification."""

    def __init__(self, text: str, pos, color, icon: str = "",
                 size: int = 13, duration: float = 2.2):
        self.text = text
        self.pos = pygame.Vector2(pos)
        self.color = color
        self.icon = icon
        self.size = size
        self.lifetime = duration
        self.max_lifetime = duration

    def update(self, dt: float):
        self.lifetime -= dt
        self.pos.y -= 30 * dt

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    def draw(self, surface):
        age = self.max_lifetime - self.lifetime
        if age < 0.12:
            alpha = int(255 * (age / 0.12))
        elif self.lifetime < 0.45:
            alpha = int(255 * (self.lifetime / 0.45))
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        label = (self.icon + "  " + self.text) if self.icon else self.text
        text_surf = ui.render_text(label, self.size, ui.TEXT_PRIMARY, "bold")
        pad_x = 14
        pad_y = 7
        w = text_surf.get_width() + pad_x * 2
        h = text_surf.get_height() + pad_y * 2

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(
            panel, (*ui.BG_CARD, int(235 * alpha / 255)),
            panel.get_rect(), border_radius=h // 2,
        )
        pygame.draw.rect(
            panel, (*self.color, alpha),
            panel.get_rect(), 1, border_radius=h // 2,
        )
        # accent left stripe
        stripe_rect = pygame.Rect(4, pad_y, 3, h - pad_y * 2)
        pygame.draw.rect(panel, (*self.color, alpha), stripe_rect,
                         border_radius=2)

        text_surf.set_alpha(alpha)
        panel.blit(text_surf, (pad_x, pad_y))

        x = int(self.pos.x - w // 2)
        y = int(self.pos.y)
        surface.blit(panel, (x, y))


class NotificationManager:
    """Owns the active toasts and subscribes to world events."""

    def __init__(self, event_bus):
        self.items = []
        event_bus.subscribe("sheep_penned", self._on_sheep_penned)
        event_bus.subscribe("sheep_killed", self._on_sheep_killed)
        event_bus.subscribe("wolf_howl",    self._on_wolf_howl)
        event_bus.subscribe("owner_whistle", self._on_whistle)
        event_bus.subscribe("dog_exhausted", self._on_dog_exhausted)

    def _on_sheep_penned(self, sheep=None, **kw):
        if sheep is not None:
            self.items.append(Toast(
                "Sheep saved", sheep.pos, ui.SUCCESS,
                icon="+",
            ))

    def _on_sheep_killed(self, sheep=None, **kw):
        if sheep is not None:
            self.items.append(Toast(
                "Sheep lost", sheep.pos, ui.DANGER,
                icon="-",
            ))

    def _on_wolf_howl(self, pos=None, **kw):
        if pos:
            self.items.append(Toast(
                "Wolf howl", pos, ui.WARNING, size=11, duration=1.5,
            ))

    def _on_whistle(self, pos=None, **kw):
        if pos:
            self.items.append(Toast(
                "Whistle", pos, ui.INFO, size=11, duration=1.2,
            ))

    def _on_dog_exhausted(self, pos=None, **kw):
        if pos:
            self.items.append(Toast(
                "Dog exhausted", pos, ui.DANGER, duration=3.0,
            ))

    def update(self, dt: float):
        for item in self.items:
            item.update(dt)
        self.items = [i for i in self.items if i.alive]

    def draw(self, surface):
        for item in self.items:
            item.draw(surface)