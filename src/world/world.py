"""
World - central state container and coordinator.

Responsibilities:
    - Generate and store the tile map
    - Spawn all agents at sensible positions
    - Own the weather and day/night objects
    - Drive random events (weather changes trigger automatically; this
      module adds scripted random happenings like extra wolf packs, etc.)
    - Expose query helpers used by agents (tile_at, passable_grid,
      world_to_cell, cell_to_world, is_in_pen, pen_center)
"""

import random
import pygame
from ..core import settings as cfg
from ..agents.sheep import Sheep
from ..agents.dog import Dog
from ..agents.wolf import Wolf
from ..agents.owner import Owner
from .weather import Weather
from .day_night import DayNight


# Tile ids
GRASS = "GRASS"
GRASS_DARK = "GRASS_DARK"
DIRT = "DIRT"
WATER = "WATER"
PRECIPICE = "PRECIPICE"
TREE = "TREE"
ROCK = "ROCK"
FENCE = "FENCE"
PEN = "PEN"

SOLID_TILES = {TREE, ROCK, FENCE}
BLOCKING_TILES = SOLID_TILES | {WATER, PRECIPICE}


class World:
    def __init__(self, event_bus, seed: int = None):
        self.event_bus = event_bus
        if seed is not None:
            random.seed(seed)

        # core subsystems
        self.weather = Weather(event_bus)
        self.day_night = DayNight()

        # agents
        self.sheep: list = []
        self.wolves: list = []
        self.dogs: list = []        # all dog agents
        self.owner: Owner = None
        self._dog: Dog = None       # primary dog (first in self.dogs)

        # tile map
        self.tiles = self._generate_map()

        # game state
        self.elapsed_time = 0.0
        self.game_over = False
        self.ending = None
        self._random_event_timer = cfg.RANDOM_EVENT_CHECK_INTERVAL

        self._spawn_agents()

        # subscribe: track when sheep get penned or killed
        event_bus.subscribe("sheep_penned", self._on_sheep_penned)
        event_bus.subscribe("sheep_killed", self._on_sheep_killed)
        event_bus.subscribe("dog_exhausted", self._on_dog_exhausted)
        event_bus.subscribe("agent_fell", self._on_agent_fell)

    # ==================================================================
    # Map generation
    # ==================================================================
    def _generate_map(self):
        """Return a 2-D list [row][col] of tile type strings."""
        rows, cols = cfg.WORLD_ROWS, cfg.WORLD_COLS
        tiles = [[GRASS for _ in range(cols)] for _ in range(rows)]

        # dirt patches
        for _ in range(6):
            cx, cy = random.randint(3, cols - 3), random.randint(3, rows - 3)
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    if random.random() < 0.5:
                        r, c = cy + dr, cx + dc
                        if 0 <= r < rows and 0 <= c < cols:
                            tiles[r][c] = GRASS_DARK

        # sparse trees
        for _ in range(18):
            c = random.randint(1, cols - 2)
            r = random.randint(1, rows - 2)
            # leave some breathing room around spawn areas
            if c < 6 and r < 6:
                continue
            if c >= cfg.PEN_COL - 1 and r >= cfg.PEN_ROW - 1:
                continue
            tiles[r][c] = TREE

        # rocks
        for _ in range(8):
            c = random.randint(1, cols - 2)
            r = random.randint(1, rows - 2)
            if tiles[r][c] == GRASS:
                tiles[r][c] = ROCK

        # a precipice chasm running vertically (kept short and biased to one side)
        chasm_col = random.randint(cols // 2 - 4, cols // 2 - 1)
        chasm_top = random.randint(2, max(3, rows // 2 - 2))
        chasm_bottom = chasm_top + random.randint(2, 4)
        for r in range(chasm_top, min(rows - 1, chasm_bottom)):
            tiles[r][chasm_col] = PRECIPICE

        # a water puddle
        wc, wr = random.randint(4, cols - 6), random.randint(4, rows - 4)
        for dr in range(0, 2):
            for dc in range(0, 3):
                if 0 <= wr + dr < rows and 0 <= wc + dc < cols:
                    if tiles[wr + dr][wc + dc] == GRASS:
                        tiles[wr + dr][wc + dc] = WATER

        # the pen (enclosure) on the right side.  fence around a grass area
        for r in range(cfg.PEN_ROW, cfg.PEN_ROW + cfg.PEN_HEIGHT):
            for c in range(cfg.PEN_COL, cfg.PEN_COL + cfg.PEN_WIDTH):
                if (r == cfg.PEN_ROW or r == cfg.PEN_ROW + cfg.PEN_HEIGHT - 1
                        or c == cfg.PEN_COL + cfg.PEN_WIDTH - 1):
                    tiles[r][c] = FENCE
                else:
                    tiles[r][c] = PEN
        # gate opening on left side of the pen (middle row, col = PEN_COL)
        gate_row = cfg.PEN_ROW + cfg.PEN_HEIGHT // 2
        tiles[gate_row][cfg.PEN_COL] = PEN

        return tiles

    # ==================================================================
    # Agent spawning
    # ==================================================================
    def _spawn_agents(self):
        # owner near the left edge
        owner_pos = self._find_spawn_near(3, cfg.WORLD_ROWS // 2)
        self.owner = Owner(owner_pos, self, self.event_bus, name="owner")

        # spawn the configured number of dogs near the owner
        dog_names = ["Rex", "Buddy", "Max", "Luna"]
        for i in range(cfg.NUM_DOGS):
            offset_row = (-1 if i % 2 == 0 else 1) * (1 + i // 2)
            dog_pos = self._find_spawn_near(
                5 + i, cfg.WORLD_ROWS // 2 + offset_row
            )
            name = dog_names[i] if i < len(dog_names) else f"Dog{i}"
            d = Dog(dog_pos, self, self.event_bus, name=name)
            # First dog is the herder (player's primary dog).
            # Additional dogs are defenders that focus on wolves.
            d.role = "herder" if i == 0 else "defender"
            self.dogs.append(d)
        # keep _dog as the primary (first) dog for backward compatibility
        self._dog = self.dogs[0] if self.dogs else None

        # sheep clustered in the centre-left
        for i in range(cfg.NUM_SHEEP):
            for _ in range(20):
                c = random.randint(6, cfg.WORLD_COLS // 2 + 4)
                r = random.randint(4, cfg.WORLD_ROWS - 4)
                if self.tiles[r][c] in (GRASS, GRASS_DARK):
                    self.sheep.append(
                        Sheep(self.cell_to_world((c, r)), self,
                              self.event_bus, name=f"sheep_{i}")
                    )
                    break

        # wolves scattered on the right/top/bottom edges
        for i in range(cfg.NUM_WOLVES):
            for _ in range(30):
                side = random.choice(["top", "bottom", "right"])
                if side == "top":
                    c, r = random.randint(4, cfg.WORLD_COLS - 4), random.randint(1, 2)
                elif side == "bottom":
                    c, r = (random.randint(4, cfg.WORLD_COLS - 4),
                            cfg.WORLD_ROWS - random.randint(2, 3))
                else:
                    c, r = (cfg.WORLD_COLS - random.randint(2, 4),
                            random.randint(2, cfg.WORLD_ROWS - 2))
                if self.tiles[r][c] in (GRASS, GRASS_DARK):
                    self.wolves.append(
                        Wolf(self.cell_to_world((c, r)), self,
                             self.event_bus, name=f"wolf_{i}")
                    )
                    break

    def _find_spawn_near(self, col: int, row: int):
        rows, cols = cfg.WORLD_ROWS, cfg.WORLD_COLS
        for radius in range(0, 6):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    r, c = row + dr, col + dc
                    if 0 <= r < rows and 0 <= c < cols:
                        if self.tiles[r][c] in (GRASS, GRASS_DARK, DIRT):
                            return self.cell_to_world((c, r))
        return self.cell_to_world((col, row))

    # ==================================================================
    # Update
    # ==================================================================
    def update(self, dt: float):
        if self.game_over:
            return

        self.elapsed_time += dt

        # subsystems
        self.weather.update(dt)
        self.day_night.update(dt)

        # update agents
        self.owner.update(dt)
        for d in self.dogs:
            d.update(dt)
        for s in self.sheep:
            s.update(dt)
        for w in self.wolves:
            w.update(dt)

        # random events
        self._random_event_timer -= dt
        if self._random_event_timer <= 0:
            self._random_event_timer = cfg.RANDOM_EVENT_CHECK_INTERVAL
            if random.random() < cfg.RANDOM_EVENT_CHANCE:
                self._fire_random_event()

        # ending checks
        self._check_endings()

    def _fire_random_event(self):
        """Pick a random happening to spice things up."""
        alive_wolves = [w for w in self.wolves if w.alive]
        alive_sheep = [s for s in self.sheep if s.alive]

        choices = []
        # add options based on what's plausible
        if len(alive_wolves) < cfg.MAX_WOLVES_TOTAL and self.elapsed_time > 60:
            choices.append("extra_wolf")
        if alive_sheep:
            choices.append("straying_sheep")
        choices.append("wolf_howl_from_distance")
        if self.day_night.is_night():
            choices.append("owl_hoot")

        ev = random.choice(choices)

        if ev == "extra_wolf":
            side_x = random.choice([30, cfg.WORLD_PIXEL_WIDTH - 30])
            pos = (side_x, random.uniform(60, cfg.WORLD_PIXEL_HEIGHT - 60))
            self.wolves.append(
                Wolf(pos, self, self.event_bus, name=f"wolf_extra_{len(self.wolves)}")
            )
            self.event_bus.publish("random_event",
                                   name="extra wolf appeared", pos=pos)

        elif ev == "straying_sheep":
            s = random.choice(alive_sheep)
            s.emotion.bump_fear(10)
            offset = pygame.Vector2(
                random.uniform(-40, 40), random.uniform(-40, 40)
            )
            s.pos += offset
            self.event_bus.publish("random_event",
                                   name="sheep strays", pos=tuple(s.pos))

        elif ev == "wolf_howl_from_distance":
            pos = (random.uniform(cfg.WORLD_PIXEL_WIDTH * 0.6,
                                  cfg.WORLD_PIXEL_WIDTH - 30),
                   random.uniform(30, cfg.WORLD_PIXEL_HEIGHT - 30))
            self.event_bus.publish("wolf_howl", pos=pos, loudness=80)
            self.event_bus.publish("random_event",
                                   name="distant howl", pos=pos)

        elif ev == "owl_hoot":
            self.event_bus.publish(
                "random_event",
                name="owl hoots",
                pos=(random.uniform(0, cfg.WORLD_PIXEL_WIDTH),
                     random.uniform(0, cfg.WORLD_PIXEL_HEIGHT))
            )

    # ==================================================================
    # Ending conditions
    # ==================================================================
    def _on_sheep_penned(self, sheep=None, **kwargs):
        # just a trigger to re-check
        pass

    def _on_sheep_killed(self, sheep=None, killer=None, **kwargs):
        pass

    def _on_dog_exhausted(self, **kwargs):
        if not self.game_over:
            self.game_over = True
            self.ending = "DOG_EXHAUSTED"

    def _on_agent_fell(self, agent=None, **kwargs):
        if agent in self.dogs and not self.game_over:
            self.game_over = True
            self.ending = "DOG_EXHAUSTED"  # reuse ending screen

    def _check_endings(self):
        penned = [s for s in self.sheep if s.alive and self.is_in_pen(s.pos)]
        alive = [s for s in self.sheep if s.alive]
        dead = len(self.sheep) - len(alive)

        # all sheep dead => wolves win immediately (no need to wait for time)
        if not alive:
            self.game_over = True
            self.ending = "WOLVES_WIN"
            return

        # wolves killed enough that winning is mathematically impossible
        # (fewer alive sheep than the minimum needed, and not enough already penned)
        if len(alive) < cfg.MIN_SHEEP_TO_WIN and len(penned) < cfg.MIN_SHEEP_TO_WIN:
            self.game_over = True
            self.ending = "WOLVES_WIN"
            return

        # all alive sheep penned => perfect!
        if len(penned) == len(alive) and len(penned) >= cfg.MIN_SHEEP_TO_WIN:
            self.game_over = True
            self.ending = "ALL_SAVED"
            return

        # time limit reached
        if self.elapsed_time > cfg.SIMULATION_TIME_LIMIT:
            if len(penned) >= cfg.MIN_SHEEP_TO_WIN:
                self.game_over = True
                self.ending = "PARTIAL_WIN"
            else:
                self.game_over = True
                self.ending = "PARTIAL_LOSS"
            return

    # ==================================================================
    # Queries
    # ==================================================================
    def tile_at(self, col: int, row: int):
        if row < 0 or row >= cfg.WORLD_ROWS:
            return None
        if col < 0 or col >= cfg.WORLD_COLS:
            return None
        return self.tiles[row][col]

    def passable_grid(self):
        """Return a 2-D list of booleans: True if passable (used by A*)."""
        return [
            [self.tiles[r][c] not in BLOCKING_TILES
             for c in range(cfg.WORLD_COLS)]
            for r in range(cfg.WORLD_ROWS)
        ]

    def world_to_cell(self, pos) -> tuple:
        return (int(pos[0] // cfg.TILE_SIZE),
                int(pos[1] // cfg.TILE_SIZE))

    def cell_to_world(self, cell) -> pygame.Vector2:
        c, r = cell
        return pygame.Vector2(
            c * cfg.TILE_SIZE + cfg.TILE_SIZE // 2,
            r * cfg.TILE_SIZE + cfg.TILE_SIZE // 2,
        )

    def is_in_pen(self, pos) -> bool:
        c, r = self.world_to_cell(pos)
        if c is None:
            return False
        return self.tile_at(c, r) == PEN

    def pen_center(self) -> pygame.Vector2:
        return pygame.Vector2(
            (cfg.PEN_COL + cfg.PEN_WIDTH // 2) * cfg.TILE_SIZE,
            (cfg.PEN_ROW + cfg.PEN_HEIGHT // 2) * cfg.TILE_SIZE,
        )

    def get_dog(self):
        return self._dog

    # ------------------------------------------------------------------
    # Global modifiers used by agents' perception
    # ------------------------------------------------------------------
    def vision_multiplier(self) -> float:
        return self.weather.vision_multiplier() * self.day_night.vision_multiplier()

    def hearing_multiplier(self) -> float:
        return self.weather.hearing_multiplier()