"""
Day / night cycle.

A single simulated day lasts DAY_CYCLE_SECONDS real seconds.  The
'time_of_day' is expressed as a normalized float in [0, 1) where
    0.00 = midnight
    0.25 = sunrise
    0.50 = noon
    0.75 = sunset
The darkness alpha value is derived from this using a triangular
function so night is fully dark and day is fully lit.
"""

import math
import pygame
from ..core import settings as cfg


class DayNight:
    def __init__(self, start_time: float = 0.30):
        self.time_of_day = start_time      # start shortly after sunrise
        self.elapsed = 0.0

    def update(self, dt: float):
        self.elapsed += dt
        self.time_of_day = (self.elapsed / cfg.DAY_CYCLE_SECONDS) + 0.3
        self.time_of_day = self.time_of_day % 1.0

    def darkness_alpha(self) -> int:
        """0 = day (no overlay), NIGHT_DARKNESS_MAX = full midnight."""
        # use a sine wave so transitions are smooth
        # peak of lightness at noon (0.5)
        brightness = 0.5 + 0.5 * math.cos(2 * math.pi * (self.time_of_day - 0.5))
        darkness = 1.0 - brightness
        return int(darkness * cfg.NIGHT_DARKNESS_MAX)

    def is_night(self) -> bool:
        return self.time_of_day < 0.2 or self.time_of_day > 0.85

    def vision_multiplier(self) -> float:
        """Agents see less at night (real-world physics)."""
        if self.is_night():
            return cfg.NIGHT_VISION_PENALTY
        return 1.0

    def label(self) -> str:
        t = self.time_of_day
        if t < 0.15:
            return "NIGHT"
        if t < 0.30:
            return "DAWN"
        if t < 0.70:
            return "DAY"
        if t < 0.85:
            return "DUSK"
        return "NIGHT"

    def draw(self, surface: pygame.Surface):
        alpha = self.darkness_alpha()
        if alpha <= 5:
            return
        overlay = pygame.Surface(
            (cfg.WORLD_PIXEL_WIDTH, cfg.WORLD_PIXEL_HEIGHT),
            pygame.SRCALPHA,
        )
        # slightly blue at night, slightly orange at dawn/dusk
        label = self.label()
        if label in ("DAWN", "DUSK"):
            color = (80, 40, 20, alpha)
        else:
            color = (10, 10, 40, alpha)
        overlay.fill(color)
        surface.blit(overlay, (0, 0))
