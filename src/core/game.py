"""
Game - main loop, scene management, input handling.

Scenes:
    TITLE    - splash / press-to-start
    PLAYING  - active simulation
    ENDED    - results screen (press R to restart)

Fonts are managed centrally by rendering/ui_theme.py, so we no longer
pass font objects around.
"""

import random
import pygame

from . import settings as cfg
from .event_bus import EventBus
from ..world.world import World
from ..rendering import renderer, hud, debug_draw, tutorial, ui_theme as ui


class Game:

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(cfg.TITLE)

        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)
        )
        self.clock = pygame.time.Clock()

        # scene state
        self.scene = "TITLE"
        self.running = True
        self.show_welcome = True
        self.show_compact_legend = True

        # overlays
        self.debug_on = cfg.DEBUG_DEFAULT_ON
        self.rubric_on = False

        # world + event bus (created on sim start)
        self.event_bus = None
        self.world = None
        self.notifications = None

        # visual feedback when player issues a right-click command:
        # (pos, kind, lifetime_remaining_seconds)
        self._command_marker = None

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------
    def start_new_simulation(self):
        self.event_bus = EventBus()
        seed = random.randint(0, 1_000_000)
        self.world = World(self.event_bus, seed=seed)
        self.notifications = tutorial.NotificationManager(self.event_bus)
        self.show_welcome = True
        self.scene = "PLAYING"

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(cfg.FPS) / 1000.0
            dt = min(dt, 0.05)  # clamp spikes

            self.handle_events()

            if self.scene == "PLAYING":
                if not self.show_welcome:
                    self.world.update(dt)
                    self.notifications.update(dt)
                    # decay any active command marker
                    if self._command_marker is not None:
                        pos, kind, ttl = self._command_marker
                        ttl -= dt
                        if ttl <= 0:
                            self._command_marker = None
                        else:
                            self._command_marker = (pos, kind, ttl)
                if self.world.game_over:
                    self.scene = "ENDED"

            self.draw()

        pygame.quit()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                elif self.scene == "TITLE":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_new_simulation()

                elif self.scene == "PLAYING":
                    if self.show_welcome:
                        self.show_welcome = False
                        continue

                    if event.key == pygame.K_F1:
                        self.debug_on = not self.debug_on
                    elif event.key == pygame.K_F2:
                        self.rubric_on = not self.rubric_on
                    elif event.key == pygame.K_F3:
                        self.show_compact_legend = not self.show_compact_legend
                    elif event.key == pygame.K_SPACE:
                        self.world.owner.whistle()
                    elif event.key == pygame.K_h:
                        self.world.owner.toggle_herd_mode()
                    elif event.key == pygame.K_r:
                        self.start_new_simulation()

                elif self.scene == "ENDED":
                    if event.key == pygame.K_r:
                        self.start_new_simulation()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if (self.scene == "PLAYING"
                        and not self.show_welcome):
                    mx, my = event.pos
                    if event.button == 1:
                        # left-click moves the shepherd
                        self.world.owner.walk_to((mx, my))
                    elif event.button == 3:
                        # right-click commands the dog
                        self._handle_dog_command((mx, my))

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def _handle_dog_command(self, click_pos):
        """Right-click commands the dog. Picks the closest entity within
        a generous click radius and dispatches the right command:
            - on a wolf  -> chase that wolf
            - on a sheep -> drive that sheep specifically
            - on empty   -> go to that point
        """
        click_vec = pygame.Vector2(click_pos)
        # pick the closest alive dog to receive the command
        candidates = [d for d in self.world.dogs if d.alive]
        if not candidates:
            return
        dog = min(candidates, key=lambda d: d.pos.distance_to(click_vec))

        # tight snap radius - players who actually click ON a creature
        # get the targeted command. Click in empty space = goto, even if
        # there's a creature ~30px away.
        click_radius = 22
        nearest_wolf = None
        nd = float("inf")
        for w in self.world.wolves:
            if not w.alive:
                continue
            d = click_vec.distance_to(w.pos)
            if d < click_radius and d < nd:
                nearest_wolf = w
                nd = d

        if nearest_wolf is not None:
            dog.command_chase(nearest_wolf)
            self._command_marker = (tuple(nearest_wolf.pos), "chase", 1.5)
            return

        # check sheep
        nearest_sheep = None
        nd = float("inf")
        for s in self.world.sheep:
            if not s.alive:
                continue
            d = click_vec.distance_to(s.pos)
            if d < click_radius and d < nd:
                nearest_sheep = s
                nd = d

        if nearest_sheep is not None:
            dog.command_drive(nearest_sheep)
            self._command_marker = (tuple(nearest_sheep.pos), "drive", 1.5)
            return

        # otherwise treat it as a "go to point" command
        dog.command_goto(click_pos)
        self._command_marker = (click_pos, "goto", 1.5)

    def draw(self):
        if self.scene == "TITLE":
            hud.draw_title_screen(self.screen)

        elif self.scene == "PLAYING":
            self._draw_playing()

        elif self.scene == "ENDED":
            hud.draw_ending_screen(self.screen, self.world)

        pygame.display.flip()

    def _draw_command_marker(self, surface):
        """Animated ring at the click position to confirm a command landed."""
        import math
        from ..rendering import ui_theme as ui
        pos, kind, ttl = self._command_marker
        max_ttl = 1.5
        progress = 1.0 - (ttl / max_ttl)  # 0..1

        # color and label depend on command kind
        if kind == "chase":
            color = ui.DANGER
            label = "CHASE"
        elif kind == "drive":
            color = ui.ACCENT
            label = "DRIVE"
        else:
            color = ui.WARNING
            label = "GO"

        cx, cy = int(pos[0]), int(pos[1])
        # outer expanding ring (faster pulse twice)
        for i in range(2):
            phase = (progress + i * 0.5) % 1.0
            radius = int(10 + 30 * phase)
            alpha = int(220 * (1 - phase))
            ring = pygame.Surface(
                (radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA,
            )
            pygame.draw.circle(
                ring, (*color, alpha),
                (radius + 2, radius + 2), radius, 2,
            )
            surface.blit(ring, (cx - radius - 2, cy - radius - 2))

        # solid center dot
        pygame.draw.circle(surface, color, (cx, cy), 5)
        pygame.draw.circle(surface, ui.BG_DEEP, (cx, cy), 5, 1)

        # label pill above
        text = ui.render_text(label, 10, color, "bold")
        pad_x, pad_y = 8, 3
        w = text.get_width() + pad_x * 2
        h = text.get_height() + pad_y * 2
        x = cx - w // 2
        y = cy - 36
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(
            panel, (*ui.BG_DEEP, 220),
            panel.get_rect(), border_radius=h // 2,
        )
        pygame.draw.rect(
            panel, color,
            panel.get_rect(), 1, border_radius=h // 2,
        )
        panel.blit(text, (pad_x, pad_y))
        surface.blit(panel, (x, y))

    def _draw_playing(self):
        # 1. world tiles
        renderer.draw_world(self.screen, self.world)

        # 2. weather particles
        self.world.weather.draw(self.screen)

        # 3. agents
        renderer.draw_agents(self.screen, self.world)

        # 4. day/night overlay
        self.world.day_night.draw(self.screen)

        # 5. pen arrow (above everything so it stays visible at night)
        tutorial.draw_pen_arrow(
            self.screen, self.world, self.world.elapsed_time,
        )

        # 6. command marker (visual feedback for right-click)
        if self._command_marker is not None:
            self._draw_command_marker(self.screen)

        # 7. floating notifications
        self.notifications.draw(self.screen)

        # 7. in-world debug visualizations
        if self.debug_on:
            debug_draw.draw_debug(self.screen, self.world)

        # 8. HUD cards (top-right, bottom strip)
        fps = self.clock.get_fps()
        hud.draw_hud(self.screen, self.world, fps,
                     self.debug_on, self.rubric_on)

        # 9. optional side panels
        if self.debug_on:
            debug_draw.draw_event_log(self.screen, self.event_bus)

        if self.rubric_on:
            debug_draw.draw_rubric_checklist(self.screen)

        # 10. compact legend (top-left)
        if self.show_compact_legend:
            tutorial.draw_compact_legend(self.screen)

        # 11. objective banner (top-center)
        tutorial.draw_objective_banner(self.screen, self.world)

        # 12. welcome overlay on top (first-frame only)
        if self.show_welcome:
            tutorial.draw_welcome_overlay(self.screen)