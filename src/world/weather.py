"""
Weather system - a finite-state machine over five weather types plus
drawable particle effects (rain, storm, fog, lightning).

States: CLEAR, CLOUDY, RAIN, STORM, FOG

Transitions are stochastic (Markov-chain style): every
WEATHER_TRANSITION_MIN..MAX seconds we pick a next weather based on the
current weather.  Storm is always followed by clear/cloudy (catharsis).

Also flashes lightning at random during STORM which publishes a 'thunder'
sound event agents can hear.
"""

import random
import pygame
from ..core import settings as cfg


WEATHERS = ["CLEAR", "CLOUDY", "RAIN", "STORM", "FOG"]

# probability matrix: rows = current, cols = next weather
# each row must sum to 1.0
TRANSITIONS = {
    "CLEAR":  [0.25, 0.40, 0.20, 0.05, 0.10],
    "CLOUDY": [0.25, 0.25, 0.30, 0.15, 0.05],
    "RAIN":   [0.05, 0.30, 0.35, 0.25, 0.05],
    "STORM":  [0.10, 0.45, 0.40, 0.05, 0.00],
    "FOG":    [0.30, 0.35, 0.15, 0.00, 0.20],
}


class Weather:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.state = "CLEAR"
        self.next_change = random.uniform(
            cfg.WEATHER_TRANSITION_MIN, cfg.WEATHER_TRANSITION_MAX
        )

        # particle arrays reused across frames
        self._rain_drops = []
        self._lightning_timer = 0.0
        self._lightning_alpha = 0  # 0..255 white flash
        self._ensure_particles()

        # state log for the debug overlay
        self.history = ["CLEAR"]

    # ------------------------------------------------------------------
    # Transition + update
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.next_change -= dt
        if self.next_change <= 0:
            self._transition()

        # spawn / update rain drops
        if self.state in ("RAIN", "STORM"):
            speed = cfg.RAIN_SPEED if self.state == "RAIN" else cfg.STORM_SPEED
            for drop in self._rain_drops:
                drop[1] += speed * dt
                drop[0] += (speed * 0.2) * dt  # slight wind slant
                if drop[1] > cfg.WORLD_PIXEL_HEIGHT:
                    drop[1] = -20
                    drop[0] = random.uniform(-40, cfg.WORLD_PIXEL_WIDTH)
                if drop[0] > cfg.WORLD_PIXEL_WIDTH:
                    drop[0] = -20

        # lightning in storms
        if self.state == "STORM":
            self._lightning_timer -= dt
            if self._lightning_timer <= 0 and self._lightning_alpha == 0:
                if random.random() < 0.012:  # flash chance per frame
                    self._lightning_alpha = 200
                    self._lightning_timer = random.uniform(5.0, 15.0)
                    self.event_bus.publish(
                        "thunder",
                        pos=(
                            random.uniform(0, cfg.WORLD_PIXEL_WIDTH),
                            random.uniform(0, cfg.WORLD_PIXEL_HEIGHT),
                        ),
                        loudness=100,
                    )

            # decay flash
            if self._lightning_alpha > 0:
                self._lightning_alpha = max(0, self._lightning_alpha - int(800 * dt))

    def _transition(self):
        row = TRANSITIONS[self.state]
        r = random.random()
        cum = 0.0
        new_state = self.state
        for w, p in zip(WEATHERS, row):
            cum += p
            if r <= cum:
                new_state = w
                break
        if new_state != self.state:
            self.state = new_state
            self.history.append(new_state)
            if len(self.history) > 10:
                self.history.pop(0)
            self.event_bus.publish("weather_changed", weather=new_state)
            self._ensure_particles()

        self.next_change = random.uniform(
            cfg.WEATHER_TRANSITION_MIN, cfg.WEATHER_TRANSITION_MAX
        )

    def _ensure_particles(self):
        desired = 0
        if self.state == "RAIN":
            desired = cfg.RAIN_DROP_COUNT
        elif self.state == "STORM":
            desired = cfg.STORM_DROP_COUNT

        while len(self._rain_drops) < desired:
            self._rain_drops.append([
                random.uniform(-40, cfg.WORLD_PIXEL_WIDTH),
                random.uniform(-cfg.WORLD_PIXEL_HEIGHT, 0),
            ])
        if desired == 0:
            self._rain_drops.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def is_wet(self) -> bool:
        return self.state in ("RAIN", "STORM")

    def vision_multiplier(self) -> float:
        return cfg.WEATHER_VISION_PENALTY.get(self.state, 1.0)

    def hearing_multiplier(self) -> float:
        return cfg.WEATHER_HEARING_PENALTY.get(self.state, 1.0)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        if self.state == "CLOUDY":
            overlay = pygame.Surface(
                (cfg.WORLD_PIXEL_WIDTH, cfg.WORLD_PIXEL_HEIGHT),
                pygame.SRCALPHA,
            )
            overlay.fill((30, 30, 40, 55))
            surface.blit(overlay, (0, 0))

        elif self.state in ("RAIN", "STORM"):
            color = (170, 180, 210) if self.state == "RAIN" else (110, 120, 160)
            overlay = pygame.Surface(
                (cfg.WORLD_PIXEL_WIDTH, cfg.WORLD_PIXEL_HEIGHT),
                pygame.SRCALPHA,
            )
            overlay.fill((30, 35, 55, 100 if self.state == "RAIN" else 140))
            surface.blit(overlay, (0, 0))
            for drop in self._rain_drops:
                pygame.draw.line(
                    surface, color,
                    (int(drop[0]), int(drop[1])),
                    (int(drop[0]) + 3, int(drop[1]) + 14),
                    1,
                )

        elif self.state == "FOG":
            overlay = pygame.Surface(
                (cfg.WORLD_PIXEL_WIDTH, cfg.WORLD_PIXEL_HEIGHT),
                pygame.SRCALPHA,
            )
            overlay.fill((200, 200, 200, 130))
            surface.blit(overlay, (0, 0))

        # lightning flash goes on top
        if self._lightning_alpha > 0:
            flash = pygame.Surface(
                (cfg.WORLD_PIXEL_WIDTH, cfg.WORLD_PIXEL_HEIGHT),
                pygame.SRCALPHA,
            )
            flash.fill((255, 255, 240, self._lightning_alpha))
            surface.blit(flash, (0, 0))
