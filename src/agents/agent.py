import math
import pygame
from ..core import settings as cfg
from ..ai.perception import can_see, can_hear


class Memory:

    def __init__(self, max_items: int = 10, default_ttl: float = 8.0):
        self.items = []  # list of dicts: {tag, pos, ttl, data}
        self.max_items = max_items
        self.default_ttl = default_ttl

    def remember(self, tag: str, pos, ttl: float = None, **data):
        entry = {
            "tag": tag,
            "pos": pygame.Vector2(pos),
            "ttl": ttl if ttl is not None else self.default_ttl,
            "data": data,
        }
        # replace existing entry with same tag
        self.items = [i for i in self.items if i["tag"] != tag]
        self.items.append(entry)
        if len(self.items) > self.max_items:
            self.items.pop(0)

    def recall(self, tag: str):
        for i in self.items:
            if i["tag"] == tag:
                return i
        return None

    def forget(self, tag: str):
        self.items = [i for i in self.items if i["tag"] != tag]

    def update(self, dt: float):
        for item in self.items:
            item["ttl"] -= dt
        self.items = [i for i in self.items if i["ttl"] > 0]


class Emotion:

    def __init__(self):
        self.fear = 0.0
        self.anger = 0.0
        self.happiness = 50.0   # neutral baseline

    def update(self, dt: float):
        # decay toward baseline (0 for fear/anger, 50 for happiness)
        self.fear = max(0.0, self.fear - cfg.EMOTION_DECAY * dt)
        self.anger = max(0.0, self.anger - cfg.EMOTION_DECAY * dt)
        if self.happiness > 50:
            self.happiness = max(50, self.happiness - cfg.EMOTION_DECAY * dt * 0.5)
        elif self.happiness < 50:
            self.happiness = min(50, self.happiness + cfg.EMOTION_DECAY * dt * 0.5)

    def bump_fear(self, amount: float):
        self.fear = min(cfg.EMOTION_MAX, self.fear + amount)

    def bump_anger(self, amount: float):
        self.anger = min(cfg.EMOTION_MAX, self.anger + amount)

    def bump_happiness(self, amount: float):
        self.happiness = min(cfg.EMOTION_MAX, self.happiness + amount)


class Agent:

    def __init__(self, pos, world, event_bus, name: str = "agent"):
        self.pos = pygame.Vector2(pos)
        self.velocity = pygame.Vector2(0, 0)
        self.facing_deg = 0.0        # 0 = east, 90 = south
        self.world = world
        self.event_bus = event_bus
        self.name = name
        self.alive = True
        self.radius = 10
        self.speed = 100.0
        self.vision_range = 200.0
        self.vision_angle = 120.0
        self.hearing_range = 250.0

        self.emotion = Emotion()
        self.memory = Memory()

        self.speech = None
        self._speech_ttl = 0.0

        self.current_path = []     # list of (col, row) cells if we path-finded
        self.current_target = None # Vector2 for target-line debug draw

        self.fsm = None

    def update(self, dt: float):
        self.emotion.update(dt)
        self.memory.update(dt)

        if self.fsm is not None:
            self.fsm.update(dt)
        friction = cfg.RAIN_FRICTION if self.world.weather.is_wet() else cfg.FRICTION
        self.pos += self.velocity * dt
        self.velocity *= friction

        if self.velocity.length_squared() > 25:
            self.facing_deg = math.degrees(
                math.atan2(self.velocity.y, self.velocity.x)
            )

        self._resolve_world_bounds()
        self._resolve_tile_collisions()

        if self.speech is not None:
            self._speech_ttl -= dt
            if self._speech_ttl <= 0:
                self.speech = None

    def say(self, text: str, ttl: float = 2.5):
        self.speech = text
        self._speech_ttl = ttl

    def see(self, target_pos, extra_range_mul: float = 1.0) -> bool:
        world_range = self.vision_range * extra_range_mul
        world_range *= self.world.vision_multiplier()
        return can_see(
            self.pos, self.facing_deg, target_pos,
            world_range, self.vision_angle
        )

    def hear(self, sound_pos, loudness: float) -> bool:
        hearing = self.hearing_range * self.world.hearing_multiplier()
        return can_hear(self.pos, sound_pos, loudness, hearing)

    def steer_toward(self, target_pos, speed: float = None):
        if speed is None:
            speed = self.speed
        diff = pygame.Vector2(target_pos) - self.pos
        if diff.length_squared() > 0.001:
            self.velocity = diff.normalize() * speed

    def steer_away_from(self, origin_pos, speed: float = None):
        if speed is None:
            speed = self.speed
        diff = self.pos - pygame.Vector2(origin_pos)
        if diff.length_squared() > 0.001:
            self.velocity = diff.normalize() * speed

    def stop(self):
        self.velocity *= 0.0

    def _resolve_world_bounds(self):
        r = self.radius
        self.pos.x = max(r, min(cfg.WORLD_PIXEL_WIDTH - r, self.pos.x))
        self.pos.y = max(r, min(cfg.WORLD_PIXEL_HEIGHT - r, self.pos.y))

    def _resolve_tile_collisions(self):
        col = int(self.pos.x // cfg.TILE_SIZE)
        row = int(self.pos.y // cfg.TILE_SIZE)
        tile = self.world.tile_at(col, row)

        if tile is None:
            return

        if tile == "PRECIPICE":
            tile_center = pygame.Vector2(
                col * cfg.TILE_SIZE + cfg.TILE_SIZE // 2,
                row * cfg.TILE_SIZE + cfg.TILE_SIZE // 2,
            )
            diff = self.pos - tile_center
            if diff.length_squared() > 0.001:
                push = diff.normalize() * (cfg.TILE_SIZE * 1.2)
                self.pos = tile_center + push
            self.velocity *= -0.5  # bounce back
            if cfg.PRECIPICE_FALL_DANGER and self.alive:
                self.alive = False
                self.event_bus.publish(
                    "agent_fell", agent=self, pos=tuple(self.pos)
                )
            else:
                self.event_bus.publish(
                    "agent_tripped", agent=self, pos=tuple(self.pos)
                )
            return

        if tile in ("TREE", "ROCK"):
            tile_center = pygame.Vector2(
                col * cfg.TILE_SIZE + cfg.TILE_SIZE // 2,
                row * cfg.TILE_SIZE + cfg.TILE_SIZE // 2,
            )
            diff = self.pos - tile_center
            if diff.length_squared() > 0.001:
                push = diff.normalize() * (cfg.TILE_SIZE * 0.6)
                self.pos = tile_center + push
            self.velocity *= 0.4
