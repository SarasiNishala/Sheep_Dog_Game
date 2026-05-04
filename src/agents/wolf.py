"""
Wolf agent - predator with strategy LEARNING.

State machine:
    PATROL       -> wander on edges of the map
    STALK        -> chosen a sheep target, moving quietly
    CHARGE       -> full speed attack
    FLEE         -> dog close enough to scare us off
    RESTING      -> low-energy recovery after failed hunt or fleeing
    DEAD         -> killed by dog (stretch: currently disabled)

Learning:
    Each wolf tries one of four hunting strategies:
        charge_frontal, sneak_flank, ambush_bush, howl_scatter
    We track a 'failure counter' per strategy.  When choosing a strategy
    we sample with probabilities inversely proportional to failures.
    Failure counters decay over time so ancient mistakes are forgotten.

This is a tabular, interpretable learning scheme that demonstrably
adapts across a single game session without needing RL training loops.
"""

import math
import random
import pygame
from ..core import settings as cfg
from .agent import Agent
from ..ai.fsm import FSM


STRATEGIES = ["charge_frontal", "sneak_flank", "ambush_bush", "howl_scatter"]


class Wolf(Agent):

    STATES = ["PATROL", "STALK", "CHARGE", "FLEE", "RESTING", "DEAD"]

    def __init__(self, pos, world, event_bus, name="wolf"):
        super().__init__(pos, world, event_bus, name=name)
        self.radius = cfg.WOLF_RADIUS
        self.speed = cfg.WOLF_SPEED
        self.vision_range = cfg.WOLF_VISION_RANGE
        self.vision_angle = cfg.WOLF_VISION_ANGLE
        self.hearing_range = cfg.WOLF_HEARING_RANGE

        self.fsm = FSM("PATROL", self.STATES, agent_name=name)

        self.current_strategy = "charge_frontal"
        # number of recent failures per strategy
        self.strategy_failures = {s: 0.0 for s in STRATEGIES}
        # the sheep we're hunting this round
        self.target_sheep = None
        # state local timers
        self._patrol_target = None
        self._patrol_timer = 0.0
        self._hunt_start_time = 0.0
        self._howl_cooldown = 0.0

    # ------------------------------------------------------------------
    # Learning: strategy chooser
    # ------------------------------------------------------------------
    def choose_strategy(self) -> str:
        """Weighted random choice: strategies with fewer failures picked more."""
        # weight = 1 / (1 + failures)
        weights = [1.0 / (1.0 + self.strategy_failures[s]) for s in STRATEGIES]
        total = sum(weights)
        r = random.random() * total
        cum = 0.0
        for s, w in zip(STRATEGIES, weights):
            cum += w
            if r <= cum:
                return s
        return STRATEGIES[-1]

    def record_failure(self):
        """Called when a hunt aborts without kill."""
        self.strategy_failures[self.current_strategy] += 1.0

    def record_success(self):
        """A kill lightly resets this strategy's failure count."""
        self.strategy_failures[self.current_strategy] = max(
            0.0, self.strategy_failures[self.current_strategy] - 1.5
        )

    # ------------------------------------------------------------------
    # Main tick
    # ------------------------------------------------------------------
    def update(self, dt: float):
        if not self.alive:
            super().update(dt)
            return

        # decay all failure counters slowly (forgiveness / forgetting)
        for s in STRATEGIES:
            self.strategy_failures[s] = max(
                0.0, self.strategy_failures[s] - cfg.WOLF_STRATEGY_DECAY * dt
            )

        self._howl_cooldown -= dt

        # check ALL dogs - wolves should flee from any nearby dog
        all_dogs = [d for d in self.world.dogs if d.alive]
        close_dogs = [
            d for d in all_dogs
            if self.pos.distance_to(d.pos) < cfg.WOLF_FEAR_DISTANCE
            and d.fsm.state in ("CHASING_WOLF", "PATROLLING", "HERDING")
        ]
        dog_close = len(close_dogs) > 0
        # pick the closest dog for flee direction
        dog = (min(close_dogs, key=lambda d: self.pos.distance_to(d.pos))
               if close_dogs else self.world.get_dog())

        # Wolves can only hunt sheep that are NOT safely in the pen.
        # Penned sheep are off-limits — wolves cannot enter the pen or kill inside it.
        visible_sheep = [s for s in self.world.sheep
                         if s.alive
                         and not self.world.is_in_pen(s.pos)
                         and self.see(s.pos)]

        # If the wolf's current target has reached the pen, abort the hunt.
        if self.target_sheep is not None and self.target_sheep.alive:
            if self.world.is_in_pen(self.target_sheep.pos):
                self.record_failure()
                self.target_sheep = None
                if self.fsm.state in ("STALK", "CHARGE"):
                    self.fsm.change_state("PATROL", "target penned")

        # --- state transitions ----------------------------------------------
        if dog_close:
            if self.fsm.state != "FLEE":
                self.fsm.change_state("FLEE", "dog close")
                # if we were in the middle of a hunt, count as a failure
                if self.target_sheep is not None:
                    self.record_failure()
                    self.target_sheep = None
                self.emotion.bump_fear(50)

        elif self.fsm.state == "FLEE":
            # wait until dog is far enough then resume
            if dog is None or self.pos.distance_to(dog.pos) > cfg.WOLF_FEAR_DISTANCE * 2:
                self.fsm.change_state("RESTING", "lost dog")

        elif self.fsm.state == "RESTING":
            if self.fsm.time_in_state > 3.0:
                self.fsm.change_state("PATROL", "recovered")

        elif self.fsm.state == "PATROL":
            if visible_sheep:
                # pick sheep and strategy
                self.target_sheep = min(
                    visible_sheep, key=lambda s: self.pos.distance_to(s.pos)
                )
                self.current_strategy = self.choose_strategy()
                self._hunt_start_time = 0.0
                if self.current_strategy == "howl_scatter":
                    self.fsm.change_state("STALK", "howling plan")
                else:
                    self.fsm.change_state("STALK", self.current_strategy)
                self.say(f"[{self.current_strategy}]", 2.0)

        elif self.fsm.state == "STALK":
            self._hunt_start_time += dt
            if self.target_sheep is None or not self.target_sheep.alive:
                self.record_failure()
                self.target_sheep = None
                self.fsm.change_state("PATROL", "target lost")
            elif self.pos.distance_to(self.target_sheep.pos) < cfg.WOLF_ATTACK_RANGE * 4:
                self.fsm.change_state("CHARGE", "in range")
            elif self._hunt_start_time > 10.0:
                # timed out - failure
                self.record_failure()
                self.target_sheep = None
                self.fsm.change_state("PATROL", "stalk timeout")

        elif self.fsm.state == "CHARGE":
            if self.target_sheep is None or not self.target_sheep.alive:
                self.record_failure()
                self.target_sheep = None
                self.fsm.change_state("PATROL", "target gone")
            elif self.pos.distance_to(self.target_sheep.pos) < cfg.WOLF_ATTACK_RANGE:
                # final safety check: never kill a sheep that made it into the pen
                if self.world.is_in_pen(self.target_sheep.pos):
                    self.record_failure()
                    self.target_sheep = None
                    self.fsm.change_state("PATROL", "sheep safe in pen")
                else:
                    self.target_sheep.kill(killer=self)
                    self.record_success()
                    self.emotion.bump_happiness(30)
                    self.target_sheep = None
                    self.fsm.change_state("RESTING", "ate sheep")

        # --- movement -------------------------------------------------------
        if self.fsm.state == "PATROL":
            self._patrol_timer -= dt
            if self._patrol_timer <= 0 or self._patrol_target is None:
                self._patrol_timer = random.uniform(3.0, 6.0)
                # Keep patrol targets away from the pen so wolves don't wander in
                for _ in range(10):
                    candidate = pygame.Vector2(
                        random.uniform(40, cfg.WORLD_PIXEL_WIDTH - 40),
                        random.uniform(40, cfg.WORLD_PIXEL_HEIGHT - 40),
                    )
                    if not self.world.is_in_pen(candidate):
                        self._patrol_target = candidate
                        break
                else:
                    self._patrol_target = pygame.Vector2(
                        cfg.WORLD_PIXEL_WIDTH * 0.3,
                        cfg.WORLD_PIXEL_HEIGHT * 0.5,
                    )
            self.steer_toward(self._patrol_target, cfg.WOLF_SPEED * 0.6)

        elif self.fsm.state == "STALK":
            if self.target_sheep is not None and self.target_sheep.alive:
                target = self._stalk_waypoint(self.target_sheep)
                self.current_target = target
                # if strategy is howl and we're in range, howl once
                if (self.current_strategy == "howl_scatter"
                        and self._howl_cooldown <= 0
                        and self.pos.distance_to(self.target_sheep.pos) < 200):
                    self._howl_cooldown = 5.0
                    self.say("AWOOO!", 1.8)
                    self.event_bus.publish(
                        "wolf_howl", pos=tuple(self.pos), loudness=90, source=self
                    )
                    self.target_sheep.emotion.bump_fear(60)

                self.steer_toward(target, cfg.WOLF_SPEED)

        elif self.fsm.state == "CHARGE":
            if self.target_sheep is not None and self.target_sheep.alive:
                self.steer_toward(self.target_sheep.pos, cfg.WOLF_CHARGE_SPEED)
                self.current_target = self.target_sheep.pos

        elif self.fsm.state == "FLEE":
            if dog is not None:
                self.steer_away_from(dog.pos, cfg.WOLF_CHARGE_SPEED)

        elif self.fsm.state == "RESTING":
            self.stop()

        super().update(dt)

    def _stalk_waypoint(self, target_sheep):
        """Produce a waypoint based on current strategy."""
        if self.current_strategy == "charge_frontal":
            return target_sheep.pos

        if self.current_strategy == "sneak_flank":
            # approach from the side relative to the sheep's velocity
            side = target_sheep.velocity.rotate(90)
            if side.length() < 1:
                side = pygame.Vector2(1, 0)
            side = side.normalize() * 40
            return target_sheep.pos + side

        if self.current_strategy == "ambush_bush":
            # come from behind relative to sheep velocity
            back = -target_sheep.velocity
            if back.length() < 1:
                back = pygame.Vector2(-1, 0)
            back = back.normalize() * 40
            return target_sheep.pos + back

        if self.current_strategy == "howl_scatter":
            # stay back at a distance; sheep will scatter into us
            return target_sheep.pos + (self.pos - target_sheep.pos).normalize() * 80

        return target_sheep.pos