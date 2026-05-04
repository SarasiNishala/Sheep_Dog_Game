"""
Dog agent - the protagonist of the simulation.

State machine:
    IDLE           -> standing near owner; default
    PATROLLING     -> scanning for threats, moderate movement
    HERDING        -> actively driving the flock toward the pen
    CHASING_WOLF   -> detected wolf, running at full speed to intercept
    RETURNING      -> heard owner call; heading back to owner
    GOTO_POINT     -> player commanded a specific destination
    RESTING        -> stamina low, stationary while it regenerates
    EXHAUSTED      -> terminal: collapsed from overwork

Herding algorithm
-----------------
Based on the Stromback shepherding model:
    1. compute the flock's center of mass C
    2. compute the unit vector D from C toward the pen (the desired drive)
    3. choose a target point T = C - D * driving_distance
       (this is "behind" the flock relative to the pen)
    4. dog moves to T, which naturally pushes the flock forward
    5. when a sheep strays too far from C, switch to a "collecting" subgoal:
       go behind that stray sheep relative to the flock's center

Player commands (right-click)
-----------------------------
    - Right-click on map  -> dog goes to that point (GOTO_POINT)
    - Right-click on wolf -> dog chases that wolf (CHASING_WOLF, locked)
    - Right-click on sheep-> dog drives that sheep specifically
    - SPACE / whistle     -> dog returns to owner

Player commands have higher priority than autonomous decisions, so the
player is always in charge when they want to be.
"""

import math
import random
import pygame
from ..core import settings as cfg
from .agent import Agent
from ..ai.fsm import FSM
from ..ai.pathfinding import a_star, smooth_path


class Dog(Agent):

    STATES = [
        "IDLE", "PATROLLING", "HERDING", "CHASING_WOLF",
        "RETURNING", "GOTO_POINT", "RESTING", "EXHAUSTED",
    ]

    def __init__(self, pos, world, event_bus, name="dog"):
        super().__init__(pos, world, event_bus, name=name)
        self.radius = cfg.DOG_RADIUS
        self.speed = cfg.DOG_SPEED
        self.vision_range = cfg.DOG_VISION_RANGE
        self.vision_angle = cfg.DOG_VISION_ANGLE
        self.hearing_range = cfg.DOG_HEARING_RANGE

        self.stamina = cfg.DOG_MAX_STAMINA
        self.time_running = 0.0
        self.fsm = FSM("PATROLLING", self.STATES, agent_name=name)

        # path follow state
        self._path_cells = []
        self._path_idx = 0
        self._path_repath_timer = 0.0
        self._bark_timer = 0.0

        # Multi-dog coordination
        # role is set by World after spawning all dogs: "herder" or "defender"
        # Herder prioritizes pushing sheep toward pen; defender prioritizes wolves.
        # Both still respond to player commands which override role.
        self.role = "herder"

        # ---- Player commands ----
        # When set, player_command overrides autonomous behavior.
        # ('goto', Vector2)  -> go to that point
        # ('chase', wolf)    -> chase a specific wolf
        # ('drive', sheep)   -> drive a specific sheep toward pen
        self.player_command = None
        self._command_timeout = 0.0   # seconds remaining

        # Visual command marker (where the player just clicked)
        self._command_marker_pos = None
        self._command_marker_age = 999.0   # not visible by default

        # subscribe to events
        event_bus.subscribe("owner_whistle", self._on_whistle)
        event_bus.subscribe("wolf_howl", self._on_wolf_howl)
        event_bus.subscribe("sheep_killed", self._on_sheep_killed)

    # ------------------------------------------------------------------
    # Public API for the player
    # ------------------------------------------------------------------
    def command_goto(self, pos):
        """Player right-clicked a map cell - go there."""
        self.player_command = ("goto", pygame.Vector2(pos))
        self._command_timeout = 12.0
        self._command_marker_pos = pygame.Vector2(pos)
        self._command_marker_age = 0.0
        self.say("On it!", 1.2)

    def command_chase(self, wolf):
        """Player right-clicked on a wolf - hunt it."""
        if wolf is None or not wolf.alive:
            return
        self.player_command = ("chase", wolf)
        self._command_timeout = 15.0
        self._command_marker_pos = pygame.Vector2(wolf.pos)
        self._command_marker_age = 0.0
        self.say("After the wolf!", 1.2)

    def command_drive(self, sheep):
        """Player right-clicked a sheep - drive it specifically."""
        if sheep is None or not sheep.alive:
            return
        self.player_command = ("drive", sheep)
        self._command_timeout = 20.0
        self._command_marker_pos = pygame.Vector2(sheep.pos)
        self._command_marker_age = 0.0
        self.say("Driving!", 1.2)

    def cancel_command(self):
        self.player_command = None
        self._command_timeout = 0.0

    # ------------------------------------------------------------------
    # Event reactions
    # ------------------------------------------------------------------
    def _on_whistle(self, pos=None, loudness=80, **kwargs):
        if pos and self.hear(pos, loudness):
            # whistle clears any active command and pulls the dog back
            self.cancel_command()
            self.memory.remember("owner_call", pos, ttl=15.0)
            self.fsm.change_state("RETURNING", "heard whistle")
            self.say("Coming!", 1.5)

    def _on_wolf_howl(self, pos=None, loudness=85, **kwargs):
        if pos and self.hear(pos, loudness):
            self.memory.remember("wolf_sound", pos, ttl=10.0)
            self.emotion.bump_anger(15)

    def _on_sheep_killed(self, sheep=None, **kwargs):
        if sheep is not None and self.pos.distance_to(sheep.pos) < 400:
            self.emotion.bump_anger(40)
            self.emotion.bump_happiness(-20)
            self.say("NO!", 1.5)

    # ------------------------------------------------------------------
    # Main AI tick
    # ------------------------------------------------------------------
    def update(self, dt: float):
        if not self.alive:
            super().update(dt)
            return

        # --- stamina accounting ---
        if self.velocity.length() > cfg.DOG_SPEED * 0.5:
            self.stamina -= cfg.DOG_STAMINA_DRAIN * dt
            self.time_running += dt
        else:
            self.stamina = min(cfg.DOG_MAX_STAMINA,
                               self.stamina + cfg.DOG_STAMINA_REGEN * dt)
            # also cool down the running-time counter while resting
            self.time_running = max(0.0, self.time_running - dt * 0.5)

        if self.stamina <= 0 and self.fsm.state != "EXHAUSTED":
            self.fsm.change_state("EXHAUSTED", "no stamina")
            self.say("*panting*", 2.0)
            self.event_bus.publish("dog_exhausted", pos=tuple(self.pos))
            return
        if self.time_running > cfg.DOG_EXHAUSTION_LIMIT:
            self.fsm.change_state("EXHAUSTED", "timed out")
            self.event_bus.publish("dog_exhausted", pos=tuple(self.pos))
            return

        # --- player command timeout ---
        if self.player_command is not None:
            self._command_timeout -= dt
            # cancel chase / drive if target died
            kind = self.player_command[0]
            target = self.player_command[1] if len(self.player_command) > 1 else None
            if kind in ("chase", "drive") and (target is None
                                                or not target.alive):
                self.cancel_command()
            elif self._command_timeout <= 0:
                self.cancel_command()

        # tick command marker age (for fade-out animation)
        self._command_marker_age += dt

        # --- gather context ---
        visible_wolves = [w for w in self.world.wolves
                          if w.alive and self.see(w.pos)]
        sheep_alive = [s for s in self.world.sheep if s.alive]
        scattered = [s for s in sheep_alive
                     if not self.world.is_in_pen(s.pos)]
        owner_call = self.memory.recall("owner_call")

        # --- decide state ---
        new_state = self._choose_state(visible_wolves, scattered, owner_call)
        if new_state != self.fsm.state:
            self.fsm.change_state(new_state, reason="utility pick")

        # --- act ---
        if self.fsm.state == "IDLE":
            self.stop()

        elif self.fsm.state == "RESTING":
            self.stop()

        elif self.fsm.state == "PATROLLING":
            self._patrol(dt)

        elif self.fsm.state == "HERDING":
            self._herd_smart(dt, scattered)

        elif self.fsm.state == "CHASING_WOLF":
            self._chase_wolf(dt, visible_wolves)
            self._bark_timer -= dt
            if self._bark_timer <= 0:
                self._bark_timer = 1.5
                self.say("WOOF!", 0.8)
                self.event_bus.publish(
                    "dog_bark", pos=tuple(self.pos), loudness=80
                )

        elif self.fsm.state == "RETURNING":
            if owner_call is not None:
                self._go_to(owner_call["pos"], dt)
                if self.pos.distance_to(owner_call["pos"]) < 30:
                    self.memory.forget("owner_call")
                    self.fsm.change_state("IDLE", "reached owner")
            else:
                # memory expired before we got there — stop freezing, resume duty
                self.fsm.change_state("PATROLLING", "lost owner signal")

        elif self.fsm.state == "GOTO_POINT":
            if self.player_command is None:
                # command expired mid-frame — bail out safely
                self.fsm.change_state("PATROLLING", "command expired")
            else:
                kind, target = self.player_command[0], self.player_command[1]
                if kind == "goto":
                    self._go_to(target, dt)
                    if self.pos.distance_to(target) < 24:
                        self.cancel_command()
                        self.fsm.change_state("PATROLLING", "reached point")

        super().update(dt)

    # ------------------------------------------------------------------
    # State chooser
    # ------------------------------------------------------------------
    def _choose_state(self, visible_wolves, scattered, owner_call):
        """Player commands have highest priority, then survival, then duty."""

        # 1. player commands override autonomous logic - including stamina rest
        # (player should always feel in control; stamina=0 forces EXHAUSTED
        # earlier in update() so we never get here in that case)
        if self.player_command is not None:
            kind = self.player_command[0]
            if kind == "goto":
                return "GOTO_POINT"
            elif kind == "chase":
                target_wolf = self.player_command[1]
                if target_wolf and target_wolf.alive:
                    return "CHASING_WOLF"
            elif kind == "drive":
                target_sheep = self.player_command[1]
                if target_sheep and target_sheep.alive:
                    return "HERDING"

        # 2. stamina critical -> rest
        if self.stamina < 12:
            return "RESTING"

        # 3. owner whistle is high priority
        if owner_call is not None:
            return "RETURNING"

        # 4. wolf reaction - but ONLY if it's threatening sheep nearby
        threatening_wolves = [
            w for w in visible_wolves
            if self._is_wolf_threatening(w)
        ]

        # filter out wolves another dog is already chasing
        threatening_wolves = [
            w for w in threatening_wolves
            if not self._other_dog_already_chasing(w)
        ]

        # role-based priority
        if self.role == "defender":
            # defenders react to ANY threatening wolf, even far from herd
            if threatening_wolves:
                if len(threatening_wolves) > 2 and self.emotion.fear > 70:
                    return "HERDING" if scattered else "PATROLLING"
                return "CHASING_WOLF"
            # if no wolves to chase, fall back to herding/patrol
            if scattered:
                return "HERDING"
            return "PATROLLING"

        # herder dogs only chase wolves that are really close to sheep
        if threatening_wolves:
            # only break off herding for wolves within 150px of any sheep
            urgent = [
                w for w in threatening_wolves
                if any(w.pos.distance_to(s.pos) < 150
                       for s in self.world.sheep
                       if s.alive and not self.world.is_in_pen(s.pos))
            ]
            if urgent:
                if len(urgent) > 2 and self.emotion.fear > 70:
                    return "HERDING" if scattered else "PATROLLING"
                return "CHASING_WOLF"

        # 5. herd if any sheep are out of the pen
        if scattered:
            return "HERDING"

        # 6. nothing to do
        return "PATROLLING"

    def _other_dog_already_chasing(self, wolf) -> bool:
        """Coordination: don't double up on the same wolf."""
        for d in self.world.dogs:
            if d is self or not d.alive:
                continue
            if d.fsm.state == "CHASING_WOLF":
                # check both player-commanded chase and autonomous chase
                if (d.player_command is not None
                        and d.player_command[0] == "chase"
                        and d.player_command[1] is wolf):
                    return True
                # for autonomous chase, look at current_target proximity
                if d.current_target is not None:
                    cx, cy = d.current_target
                    if math.hypot(cx - wolf.pos.x, cy - wolf.pos.y) < 30:
                        return True
        return False

    def _is_wolf_threatening(self, wolf) -> bool:
        """A wolf is threatening if it's actively hunting (STALK/CHARGE) or
        close to any alive sheep. Idle/fleeing wolves don't justify an abandon-
        herd reaction."""
        if wolf.fsm.state in ("STALK", "CHARGE"):
            return True
        # otherwise only react if wolf is within 180px of any alive sheep
        for s in self.world.sheep:
            if s.alive and not self.world.is_in_pen(s.pos):
                if wolf.pos.distance_to(s.pos) < 180:
                    return True
        return False

    # ------------------------------------------------------------------
    # State actions
    # ------------------------------------------------------------------
    def _patrol(self, dt):
        owner = self.world.owner
        if owner is None:
            self.stop()
            return
        # slow circle around owner
        angle = self.fsm.time_in_state * 0.6
        target = owner.pos + pygame.Vector2(
            math.cos(angle) * 90, math.sin(angle) * 90
        )
        self.steer_toward(target, cfg.DOG_SPEED * 0.5)

    def _chase_wolf(self, dt, visible_wolves):
        """Chase a wolf - either the player's commanded target, or the
        closest threatening one."""
        target_wolf = None

        # if player commanded a specific wolf, use it
        if (self.player_command is not None
                and self.player_command[0] == "chase"):
            cmd_wolf = self.player_command[1]
            if cmd_wolf and cmd_wolf.alive:
                target_wolf = cmd_wolf

        if target_wolf is None and visible_wolves:
            target_wolf = min(
                visible_wolves,
                key=lambda w: self.pos.distance_to(w.pos),
            )

        if target_wolf is None:
            return

        self.steer_toward(target_wolf.pos, cfg.DOG_SPEED * 1.4)
        self.current_target = target_wolf.pos

    def _herd_smart(self, dt, scattered):
        """Smart herding using a Stromback-style driving algorithm.

        Computes flock center of mass, then positions the dog 'behind'
        the flock relative to the pen. The flock's flee-from-dog
        behavior naturally pushes them toward the pen.

        If a sheep has strayed far from the flock, switches to a
        'collecting' sub-goal where the dog goes behind the stray to
        push it back to the flock first.
        """
        if not scattered:
            return

        pen = self.world.pen_center()

        # if player has commanded a specific sheep, focus on driving it
        if (self.player_command is not None
                and self.player_command[0] == "drive"):
            target_sheep = self.player_command[1]
            if target_sheep and target_sheep.alive:
                # use a shorter driving distance for player commands so
                # the dog stays visually close to the targeted sheep
                target_pos = self._behind_sheep_relative_to(
                    target_sheep.pos, pen, driving_distance=45.0,
                )
                self._go_to(target_pos, dt, repath_interval=0.5)
                self.current_target = target_pos
                return

        # 1. compute flock center of mass
        center = pygame.Vector2(0, 0)
        for s in scattered:
            center += s.pos
        center /= len(scattered)

        # 2. find a stray sheep (>120px from center)
        strays = [
            s for s in scattered
            if s.pos.distance_to(center) > 130
        ]
        if strays:
            # collect: drive the farthest stray back toward the flock
            stray = max(strays, key=lambda s: s.pos.distance_to(center))
            # behind the stray, relative to the flock center
            target_pos = self._behind_sheep_relative_to(stray.pos, center)
        else:
            # 3. driving subgoal: behind the FLOCK, relative to the pen
            target_pos = self._behind_sheep_relative_to(center, pen)

        self._go_to(target_pos, dt, repath_interval=0.8)
        self.current_target = target_pos

    def _behind_sheep_relative_to(self, sheep_pos, target_pos,
                                   driving_distance: float = 75.0):
        """Compute a point 'behind' sheep_pos with respect to target_pos.

        That is, on the line from target through sheep, extended past
        sheep by driving_distance. Result is clamped to world bounds.
        """
        sp = pygame.Vector2(sheep_pos)
        tp = pygame.Vector2(target_pos)
        away = sp - tp
        if away.length() < 1.0:
            return sp
        away = away.normalize()
        result = sp + away * driving_distance
        # clamp inside world bounds with a small inset so the cell-lookup
        # in _go_to never reads outside the grid
        inset = cfg.TILE_SIZE
        result.x = max(inset, min(cfg.WORLD_PIXEL_WIDTH - inset, result.x))
        result.y = max(inset, min(cfg.WORLD_PIXEL_HEIGHT - inset, result.y))
        return result

    # ------------------------------------------------------------------
    # Path follow
    # ------------------------------------------------------------------
    def _go_to(self, target_pos, dt, repath_interval: float = 1.5):
        # apply precipice avoidance steering
        avoid = self._precipice_avoidance()
        if avoid.length() > 0.1:
            self.velocity += avoid * cfg.DOG_SPEED * dt * 10.0

        self._path_repath_timer -= dt
        target_pos = pygame.Vector2(target_pos)

        need_repath = (not self._path_cells
                       or self._path_repath_timer <= 0
                       or self._path_idx >= len(self._path_cells))

        if need_repath:
            start_cell = self.world.world_to_cell(self.pos)
            goal_cell = self.world.world_to_cell(target_pos)
            # clamp both into the grid - prevents IndexError when an agent
            # has been pushed slightly outside world bounds by physics
            start_cell = (
                max(0, min(cfg.WORLD_COLS - 1, start_cell[0])),
                max(0, min(cfg.WORLD_ROWS - 1, start_cell[1])),
            )
            goal_cell = (
                max(0, min(cfg.WORLD_COLS - 1, goal_cell[0])),
                max(0, min(cfg.WORLD_ROWS - 1, goal_cell[1])),
            )
            grid = self.world.passable_grid()
            path = a_star(grid, start_cell, goal_cell)
            if path:
                self._path_cells = smooth_path(path, grid)
                self._path_idx = 1
                self._path_repath_timer = repath_interval
                self.current_path = self._path_cells
            else:
                self.steer_toward(target_pos, cfg.DOG_SPEED)
                return

        if self._path_idx < len(self._path_cells):
            wp_cell = self._path_cells[self._path_idx]
            wp = self.world.cell_to_world(wp_cell)
            if self.pos.distance_to(wp) < cfg.TILE_SIZE * 0.7:
                self._path_idx += 1
            else:
                self.steer_toward(wp, cfg.DOG_SPEED)

    def _precipice_avoidance(self) -> pygame.Vector2:
        """Steer away from precipices and water tiles. The dog uses A*
        which already avoids them, but tile-level corner cases can still
        clip the dog into a chasm cell."""
        avoid = pygame.Vector2(0, 0)
        c0 = int(self.pos.x // cfg.TILE_SIZE)
        r0 = int(self.pos.y // cfg.TILE_SIZE)
        for dr in range(-2, 3):
            for dc in range(-2, 3):
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
                    if d < cfg.TILE_SIZE * 2.5:
                        strength = (cfg.TILE_SIZE * 2.5 - d) / (cfg.TILE_SIZE * 2.5)
                        avoid += away.normalize() * strength
        if avoid.length() > 0:
            return avoid.normalize()
        return avoid