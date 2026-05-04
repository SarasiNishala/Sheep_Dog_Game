"""
UI Theme - Pixel-art warm farm style.

Palette: warm creams, earthy browns, mossy greens, soft amber.
All cards use chunky pixel-style borders with a parchment/wood feel.
"""

import pygame

# =============================================================================
# COLOR TOKENS  —  warm pixel-art farm palette
# =============================================================================

# Backgrounds — parchment / wood layers
BG_DEEP      = (44,  33,  22)
BG_CANVAS    = (58,  44,  28)
BG_CARD      = (92,  72,  48)
BG_ELEVATED  = (118, 94,  62)
BG_OVERLAY   = (22,  16,  10, 210)
BG_GLASS     = (52,  40,  22, 225)

# Borders
BORDER_SUBTLE = (80,  60,  36)
BORDER_STRONG = (140, 100, 55)
BORDER_PIXEL  = (180, 130, 70)

# Text
TEXT_PRIMARY   = (255, 248, 220)
TEXT_SECONDARY = (210, 188, 148)
TEXT_MUTED     = (148, 120,  80)

# Accent
ACCENT         = (100, 190, 120)
ACCENT_BRIGHT  = (140, 220, 150)
ACCENT_DIM     = (60,  130,  75)

# Semantic
SUCCESS        = (130, 210, 110)
SUCCESS_DIM    = (70,  140,  70)
WARNING        = (240, 185,  60)
WARNING_DIM    = (160, 118,  30)
DANGER         = (220,  90,  80)
DANGER_DIM     = (150,  50,  40)
INFO           = (120, 180, 220)
INFO_DIM       = (70,  130, 180)

# Agent colours
COLOR_OWNER = (180, 70, 70)
COLOR_DOG   = (160, 110, 60)
COLOR_SHEEP = (235, 235, 220)
COLOR_WOLF  = (100, 90, 110)
COLOR_PEN   = (130, 200, 100)

# =============================================================================
# FONTS
# =============================================================================
_CLEAN_FONTS = "sfprodisplay,inter,segoeui,segoe ui,roboto,arial"

_font_cache = {}


def font(size: int, weight: str = "regular", pixel: bool = False):
    key = (size, weight, pixel)
    if key not in _font_cache:
        bold = (weight == "bold")
        try:
            f = pygame.font.SysFont(_CLEAN_FONTS, size, bold=bold)
        except Exception:
            f = pygame.font.Font(None, size)
        _font_cache[key] = f
    return _font_cache[key]


def render_text(text: str, size: int, color, weight: str = "regular",
                pixel: bool = False):
    return font(size, weight, pixel).render(text, True, color)


# =============================================================================
# PRIMITIVE COMPONENTS
# =============================================================================

def draw_card(surface, rect, bg=BG_CARD, border=BORDER_PIXEL,
              radius: int = 6, shadow: bool = True):
    if shadow:
        sh = pygame.Surface((rect.w + 6, rect.h + 6), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 100),
                         pygame.Rect(4, 4, rect.w, rect.h), border_radius=radius)
        surface.blit(sh, (rect.x - 2, rect.y - 1))
    pygame.draw.rect(surface, bg, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, 3, border_radius=radius)
    # inner highlight line
    inner = pygame.Rect(rect.x + 2, rect.y + 2, rect.w - 4, rect.h - 4)
    pygame.draw.rect(surface,
                     (min(255, bg[0]+22), min(255, bg[1]+22), min(255, bg[2]+18)),
                     inner, 1, border_radius=max(0, radius - 2))


def draw_glass_card(surface, rect, tint=BG_GLASS,
                    border=BORDER_PIXEL, radius: int = 6):
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, tint, panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, (*border, 230), panel.get_rect(),
                     3, border_radius=radius)
    surface.blit(panel, (rect.x, rect.y))


def draw_pill(surface, text: str, pos, size: int = 11,
              bg=BG_ELEVATED, fg=TEXT_PRIMARY, border=None,
              padding=(10, 4), weight: str = "bold",
              center: bool = False) -> pygame.Rect:
    text_surf = render_text(text, size, fg, weight)
    w = text_surf.get_width() + padding[0] * 2
    h = text_surf.get_height() + padding[1] * 2
    radius = 4
    x, y = pos
    if center:
        x -= w // 2
        y -= h // 2
    rect = pygame.Rect(int(x), int(y), w, h)
    if len(bg) == 4:
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, bg, panel.get_rect(), border_radius=radius)
        if border:
            pygame.draw.rect(panel, border, panel.get_rect(),
                             2, border_radius=radius)
        surface.blit(panel, (rect.x, rect.y))
    else:
        pygame.draw.rect(surface, bg, rect, border_radius=radius)
        if border:
            pygame.draw.rect(surface, border, rect, 2, border_radius=radius)
    surface.blit(text_surf, (rect.x + padding[0], rect.y + padding[1]))
    return rect


def draw_keycap(surface, key_text: str, pos, size: int = 11) -> pygame.Rect:
    text_surf = render_text(key_text, size, TEXT_PRIMARY, "bold")
    w = max(text_surf.get_width() + 14, 28)
    h = text_surf.get_height() + 10
    x, y = pos
    rect = pygame.Rect(x, y, w, h)
    # pixel shadow
    shadow_rect = pygame.Rect(x + 3, y + 3, w, h)
    pygame.draw.rect(surface, (22, 14, 8), shadow_rect, border_radius=4)
    # body
    pygame.draw.rect(surface, BG_ELEVATED, rect, border_radius=4)
    pygame.draw.line(surface, BORDER_PIXEL, (x + 4, y + 1), (x + w - 5, y + 1))
    pygame.draw.line(surface, (50, 36, 20), (x + 4, y + h - 2), (x + w - 5, y + h - 2))
    pygame.draw.rect(surface, BORDER_PIXEL, rect, 2, border_radius=4)
    surface.blit(text_surf,
                 (x + (w - text_surf.get_width()) // 2,
                  y + (h - text_surf.get_height()) // 2))
    return rect


def draw_progress_bar(surface, rect, value: float, max_value: float = 100.0,
                      fg=ACCENT, bg=BG_DEEP, radius: int = None):
    if radius is None:
        radius = 3
    pygame.draw.rect(surface, bg, rect, border_radius=radius)
    pygame.draw.rect(surface, BORDER_SUBTLE, rect, 1, border_radius=radius)
    if value > 0 and max_value > 0:
        pct = max(0.0, min(1.0, value / max_value))
        fill_w = max(rect.h, int(rect.w * pct)) if pct > 0.02 else 0
        if fill_w > 0:
            filled = pygame.Rect(rect.x, rect.y, fill_w, rect.h)
            pygame.draw.rect(surface, fg, filled, border_radius=radius)
            pygame.draw.line(
                surface,
                (min(255, fg[0]+60), min(255, fg[1]+60), min(255, fg[2]+40)),
                (rect.x + 1, rect.y + 1), (rect.x + fill_w - 2, rect.y + 1)
            )


def draw_dot(surface, pos, color, size: int = 5, glow: bool = False):
    x, y = int(pos[0]), int(pos[1])
    if glow:
        glow_surf = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 50), (size*3, size*3), size*3)
        surface.blit(glow_surf, (x - size*3, y - size*3))
    pygame.draw.circle(surface, color, (x, y), size)
    pygame.draw.circle(surface, (min(255, color[0]+50), min(255, color[1]+50),
                                  min(255, color[2]+40)), (x, y), max(1, size-2), 1)


def draw_swatch(surface, pos, color, size: int = 8, outline=BORDER_PIXEL):
    pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), size)
    pygame.draw.circle(surface, outline, (int(pos[0]), int(pos[1])), size, 2)


def draw_section_title(surface, text: str, pos, size: int = 10, color=TEXT_MUTED):
    x, y = pos
    spacing = 1
    total_w = 0
    for ch in text.upper():
        ch_surf = render_text(ch, size, color, "bold")
        surface.blit(ch_surf, (x + total_w, y))
        total_w += ch_surf.get_width() + spacing
    return total_w


def draw_divider(surface, x, y, width, color=BORDER_SUBTLE):
    pygame.draw.line(surface, color, (x, y), (x + width, y), 1)
    pygame.draw.line(surface,
                     (max(0, color[0]-20), max(0, color[1]-20), max(0, color[2]-20)),
                     (x, y+1), (x + width, y+1), 1)


def draw_vertical_gradient(surface, rect, top_color, bottom_color):
    h = rect.h
    for i in range(h):
        t = i / max(1, h - 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        pygame.draw.line(surface, (r, g, b),
                         (rect.x, rect.y + i), (rect.x + rect.w, rect.y + i))


def draw_radial_glow(surface, pos, color, radius: int, steps: int = 10):
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(steps, 0, -1):
        alpha = int(60 * (i / steps) ** 2)
        pygame.draw.circle(glow, (*color, alpha), (radius, radius),
                           int(radius * (i / steps)))
    surface.blit(glow, (pos[0] - radius, pos[1] - radius))