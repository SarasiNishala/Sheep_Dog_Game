"""
Owner agent - human controlled (mouse).

The owner:
    - walks where the player left-clicks
    - whistles (publishes owner_whistle) on SPACE — calls dogs back
    - can toggle HERD MODE with H key:
        When herd mode is ON the owner actively pushes nearby sheep
        toward the pen, just like a dog would.  Sheep treat the owner
        as a weaker herding pressure (boids flee_owner vector).
        The owner also periodically claps / shouts to keep sheep moving.
"""

import pygame
from ..core import settings as cfg
from .agent import Agent
from ..ai.fsm import FSM


class Owner(Agent):

    STATES = ["STANDING", "CALLING", "HERDING"]

    def __init__(self, pos, world, event_bus, name="owner"):
        super().__init__(pos, world, event_bus, name=name)
        self.radius = cfg.OWNER_RADIUS
        self.speed = 120.0
        self.fsm = FSM("STANDING", self.STATES, agent_name=name)

        self._call_cd = 0.0
        self._clap_cd = 0.0
        self._move_target = None

        # Herd-mode flag — toggled by H key via game.py
        self.herd_mode = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def toggle_herd_mode(self):
        """Toggle owner herding on/off.  Returns the new state."""
        self.herd_mode = not self.herd_mode
        if self.herd_mode:
            self.say("HEY! HYA!", 1.5)
            self.fsm.change_state("HERDING", "herd mode on")
        else:
            self.say("*at ease*", 1.2)
            self.fsm.change_state("STANDING", "herd mode off")
        return self.herd_mode

    def walk_to(self, target_pos):
        self._move_target = pygame.Vector2(target_pos)

    def whistle(self):
        if self._call_cd > 0:
            return False
        self._call_cd = cfg.OWNER_CALL_COOLDOWN
        self.fsm.change_state("CALLING", "whistled")
        self.say("*whistles*", 1.5)
        self.event_bus.publish(
            "owner_whistle",
            pos=tuple(self.pos),
            loudness=95,
            source=self,
        )
        return True

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._call_cd = max(0.0, self._call_cd - dt)
        self._clap_cd = max(0.0, self._clap_cd - dt)

        # Walk toward any click target
        if self._move_target is not None:
            dir_vec = self._move_target - self.pos
            if dir_vec.length() < 4:
                self._move_target = None
                self.stop()
            else:
                self.steer_toward(self._move_target, self.speed)

        # Whistle animation ends
        if self.fsm.state == "CALLING" and self.fsm.time_in_state > 0.8:
            if self.herd_mode:
                self.fsm.change_state("HERDING", "done whistling")
            else:
                self.fsm.change_state("STANDING", "done calling")

        # --- Herd mode behaviour ------------------------------------------
        if self.herd_mode and self.fsm.state == "HERDING":
            self._do_herding(dt)

        super().update(dt)

    # ------------------------------------------------------------------
    # Herding logic
    # ------------------------------------------------------------------
    def _do_herding(self, dt):
        """Periodically shout/clap to push nearby sheep.

        The actual sheep-steering happens inside boids (flee_owner vector).
        Here we just emit a clap event so sheep know the owner is active,
        and we display speech bubbles so it reads clearly on screen.
        """
        sheep_nearby = [
            s for s in self.world.sheep
            if s.alive
            and not self.world.is_in_pen(s.pos)
            and self.pos.distance_to(s.pos) < cfg.OWNER_HERD_RADIUS
        ]

        if sheep_nearby and self._clap_cd <= 0:
            self._clap_cd = cfg.OWNER_CLAP_COOLDOWN
            clap_phrases = ["HYA!", "GO ON!", "MOVE IT!", "YA! YA!"]
            import random
            self.say(random.choice(clap_phrases), 1.2)
            # Publish an event so sheep react (fear bump)
            self.event_bus.publish(
                "owner_clap",
                pos=tuple(self.pos),
                loudness=60,
                source=self,
            )