"""
Sheep agent.

State machine:
    GRAZING   -> default, slow wander
    ALERT     -> saw/heard something suspicious
    FLEEING   -> wolf nearby, panic mode
    HERDED    -> being pushed by dog, follow boids toward pen
    PENNED    -> safely inside the enclosure (terminal happy state)
    DEAD      -> eaten by wolf or fell into precipice

Intelligence traits exposed:
    - Perception (short-range vision + hearing)
    - Decision making (simple utility: what to do given threats)
    - Emotion (fear spikes when wolf spotted, happiness when penned)
"""

import random
import pygame
from ..core import settings as cfg
from .agent import Agent
from ..ai.fsm import FSM
from ..ai.boids import compute_boids_force


class Sheep(Agent):

    STATES = ["GRAZING", "ALERT", "FLEEING", "HERDED", "PENNED", "DEAD"]

    def __init__(self, pos, world, event_bus, name="sheep"):
        super().__init__(pos, world, event_bus, name=name)
        self.radius = cfg.SHEEP_RADIUS
        self.speed = cfg.SHEEP_SPEED
        self.vision_range = cfg.SHEEP_VISION_RANGE
        self.vision_angle = cfg.SHEEP_VISION_ANGLE
        self.hearing_range = cfg.SHEEP_HEARING_RANGE

        self.fsm = FSM("GRAZING", self.STATES, agent_name=name)
        self.panicking = False

        # wander behavior
        self._wander_timer = 0.0
        self._wander_target = None

        # whistle recall: when owner whistles, sheep move toward owner
        self._whistle_ttl = 0.0  # seconds remaining of recall pull
        event_bus.subscribe("owner_whistle", self._on_owner_whistle)

    def _on_owner_whistle(self, pos=None, loudness=95, **kwargs):
        """React to owner whistle - be drawn toward the owner."""
        if pos is None:
            return
        whistle_pos = pygame.Vector2(pos)
        # Sheep hear the whistle if it's loud enough (all sheep in range)
        if self.pos.distance_to(whistle_pos) <= loudness * 4.5:
            self._whistle_ttl = 5.0  # pull toward owner for 5 seconds
            # Move out of FLEEING only if not wolf-panicking
            if self.fsm.state not in ("FLEEING", "PENNED", "DEAD"):
                self.fsm.change_state("HERDED", "heard whistle")

    def update(self, dt: float):
        if not self.alive:
            if self.fsm.state != "DEAD":
                self.fsm.change_state("DEAD", "died")
            return

        # decay whistle recall timer
        prev_whistle_ttl = self._whistle_ttl
        self._whistle_ttl = max(0.0, self._whistle_ttl - dt)
        # when whistle recall expires, release sheep back to normal wandering
        if prev_whistle_ttl > 0.0 and self._whistle_ttl == 0.0:
            if self.fsm.state == "HERDED":
                self.fsm.change_state("GRAZING", "whistle over")

        # in-pen check: terminal happy state
        if self.world.is_in_pen(self.pos):
            if self.fsm.state != "PENNED":
                self.fsm.change_state("PENNED", "entered pen")
                self.emotion.bump_happiness(50)
                self.event_bus.publish("sheep_penned", sheep=self)
            self.stop()
            super().update(dt)
            return

        # gather context from the world
        dog = self.world.get_dog()
        owner = self.world.owner
        wolves = [w for w in self.world.wolves if w.alive]
        flock = self.world.sheep

        nearest_wolf = self._nearest_visible(wolves)

        # --- decision: state transitions -------------------------------------
        if nearest_wolf is not None:
            self.emotion.bump_fear(30 * dt)
            self.memory.remember("last_wolf", nearest_wolf.pos, ttl=6.0)
            if self.fsm.state != "FLEEING":
                self.fsm.change_state("FLEEING", "saw wolf")
                if random.random() < 0.4:
                    self.say("BAAAH!", 1.0)
                    # bleating is audible - alerts others
                    self.event_bus.publish(
                        "sheep_bleat", pos=tuple(self.pos), loudness=50
                    )
        elif dog is not None and (self.pos.distance_to(dog.pos)
                                  < cfg.BOIDS_HERDING_DISTANCE * 1.2):
            if self.fsm.state not in ("FLEEING", "HERDED"):
                self.fsm.change_state("HERDED", "dog close")
        elif (owner is not None and owner.herd_mode
              and self.pos.distance_to(owner.pos) < cfg.OWNER_HERD_RADIUS):
            # owner is actively herding and close enough
            if self.fsm.state not in ("FLEEING", "HERDED"):
                self.fsm.change_state("HERDED", "owner herding")
        elif self.emotion.fear > 30 or self.memory.recall("last_wolf"):
            if self.fsm.state != "ALERT":
                self.fsm.change_state("ALERT", "still scared")
        else:
            if self.fsm.state not in ("GRAZING",):
                self.fsm.change_state("GRAZING", "calm")

        # --- movement: boids + state-specific bias ---------------------------
        force = compute_boids_force(self, flock, dog, wolves, owner=owner)

        if self.fsm.state == "GRAZING":
            # suppress boids grouping force; wander independently
            force *= 0.05
            self._wander_timer -= dt
            if self._wander_timer <= 0:
                self._wander_timer = random.uniform(1.5, 3.5)
                angle = random.uniform(0, 360)
                self._wander_target = self.pos + pygame.Vector2(
                    pygame.math.Vector2(
                        pygame.math.Vector2(1, 0).rotate(angle)
                    ) * 80
                )
            if self._wander_target is not None:
                wdir = self._wander_target - self.pos
                if wdir.length() > 3:
                    force += wdir.normalize() * cfg.SHEEP_SPEED * 0.6

        elif self.fsm.state == "ALERT":
            # heightened boids, toward herd center for safety
            force *= 1.2

        elif self.fsm.state == "HERDED":
            # let the dog push them toward the pen
            pen_center = self.world.pen_center()
            to_pen = pen_center - self.pos
            if to_pen.length() > 1:
                force += to_pen.normalize() * cfg.SHEEP_SPEED * 0.5

        elif self.fsm.state == "FLEEING":
            # strong wolf-flee component already in boids
            force *= 1.4
            self.speed = cfg.SHEEP_PANIC_SPEED
        else:
            self.speed = cfg.SHEEP_SPEED

        # apply the steering force by blending into velocity
        self.velocity += force * dt * 4.0

        # Whistle recall: pull sheep toward owner when Space was pressed
        if self._whistle_ttl > 0.0 and owner is not None:
            to_owner = owner.pos - self.pos
            dist_to_owner = to_owner.length()
            if dist_to_owner > 20:
                pull_strength = min(1.0, self._whistle_ttl / 2.5)
                self.velocity += to_owner.normalize() * cfg.SHEEP_SPEED * 1.2 * pull_strength

        # Boundary repulsion: push sheep away from screen/world edges
        # This is the main fix for corner-stuck behavior
        margin = cfg.TILE_SIZE * 2.5
        repulse = pygame.Vector2(0, 0)
        if self.pos.x < margin:
            repulse.x += (margin - self.pos.x) / margin
        if self.pos.x > cfg.WORLD_PIXEL_WIDTH - margin:
            repulse.x -= (self.pos.x - (cfg.WORLD_PIXEL_WIDTH - margin)) / margin
        if self.pos.y < margin:
            repulse.y += (margin - self.pos.y) / margin
        if self.pos.y > cfg.WORLD_PIXEL_HEIGHT - margin:
            repulse.y -= (self.pos.y - (cfg.WORLD_PIXEL_HEIGHT - margin)) / margin
        if repulse.length() > 0.01:
            self.velocity += repulse.normalize() * cfg.SHEEP_SPEED * 2.0

        # Precipice avoidance - look ahead and steer away from holes
        # (real-world physics: sheep don't want to die)
        avoid = self._precipice_avoidance()
        if avoid.length() > 0.1:
            self.velocity += avoid * cfg.SHEEP_PANIC_SPEED * dt * 12.0
        # cap speed
        max_speed = (cfg.SHEEP_PANIC_SPEED
                     if self.fsm.state == "FLEEING"
                     else cfg.SHEEP_SPEED)
        if self.velocity.length() > max_speed:
            self.velocity = self.velocity.normalize() * max_speed

        super().update(dt)

    def _nearest_visible(self, targets):
        nearest, ndist = None, float("inf")
        for t in targets:
            if self.see(t.pos) or self.pos.distance_to(t.pos) < 60:
                d = self.pos.distance_to(t.pos)
                if d < ndist:
                    nearest, ndist = t, d
        return nearest

    def _precipice_avoidance(self) -> pygame.Vector2:
        """Look at nearby cells, return a vector pointing away from any
        precipice / water tile. Used to keep sheep from walking off cliffs."""
        avoid = pygame.Vector2(0, 0)
        c0 = int(self.pos.x // cfg.TILE_SIZE)
        r0 = int(self.pos.y // cfg.TILE_SIZE)
        # 7x7 neighborhood (look 3 tiles out in each direction)
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                if dr == 0 and dc == 0:
                    continue
                tile = self.world.tile_at(c0 + dc, r0 + dr)
                if tile in ("PRECIPICE", "WATER"):
                    cell_center = pygame.Vector2(
                        (c0 + dc) * cfg.TILE_SIZE + cfg.TILE_SIZE // 2,
                        (r0 + dr) * cfg.TILE_SIZE + cfg.TILE_SIZE // 2,
                    )
                    away = self.pos - cell_center
                    d = max(away.length(), 1.0)
                    if d < cfg.TILE_SIZE * 3.5:
                        # closer = stronger (inverse-square)
                        strength = (cfg.TILE_SIZE * 3.5 - d) / (cfg.TILE_SIZE * 3.5)
                        strength = strength * strength
                        avoid += away.normalize() * strength
        if avoid.length() > 0:
            return avoid.normalize()
        return avoid

    def kill(self, killer=None):
        if not self.alive:
            return
        self.alive = False
        self.fsm.change_state("DEAD", "killed")
        self.event_bus.publish(
            "sheep_killed", sheep=self, killer=killer, pos=tuple(self.pos)
        )