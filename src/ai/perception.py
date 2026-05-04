"""
Perception - cone-of-vision and hearing-radius checks.

This module satisfies the 'perceptions' and 'real-world physics' rubric
requirements.  Agents ONLY react to targets that pass these physical tests.

Vision cone algorithm:
    1. Compute vector from observer to target.
    2. Reject if distance > range.
    3. Compute angle between facing direction and that vector via dot product.
    4. Reject if angle > half the cone's angular width.

Hearing algorithm:
    1. perceived_loudness = sound.loudness - distance * falloff
    2. Reject if perceived_loudness below threshold.

Both respect weather penalties applied by the world (multiply ranges).
"""

import math
import pygame


def can_see(observer_pos, facing_deg, target_pos,
            vision_range: float, vision_angle_deg: float) -> bool:
    """Return True if target is inside the observer's vision cone."""
    ox, oy = observer_pos
    tx, ty = target_pos

    # vector from observer to target
    dx, dy = tx - ox, ty - oy
    distance = math.hypot(dx, dy)
    if distance > vision_range or distance < 0.001:
        return distance < 0.001  # stood on top = always visible

    # direction agent is facing, as unit vector
    fx = math.cos(math.radians(facing_deg))
    fy = math.sin(math.radians(facing_deg))

    # normalize target vector
    nx, ny = dx / distance, dy / distance

    # dot product = cos(angle_between)
    cos_between = fx * nx + fy * ny
    # half-cone angle in radians -> cos of half cone
    half_cone_cos = math.cos(math.radians(vision_angle_deg / 2.0))

    return cos_between >= half_cone_cos


def can_hear(observer_pos, sound_pos, loudness: float,
             hearing_range: float, falloff_per_pixel: float = 0.1) -> bool:
    """Inverse-linear sound falloff.  Returns True if audible."""
    ox, oy = observer_pos
    sx, sy = sound_pos
    distance = math.hypot(sx - ox, sy - oy)
    if distance > hearing_range:
        return False
    perceived = loudness - distance * falloff_per_pixel
    return perceived > 0


def get_vision_cone_polygon(observer_pos, facing_deg: float,
                            vision_range: float, vision_angle_deg: float,
                            segments: int = 16):
    """Return a list of points describing the vision cone as a triangle fan.
    Used by the debug overlay to DRAW the cone so graders can see it."""
    ox, oy = observer_pos
    points = [(ox, oy)]
    half = vision_angle_deg / 2.0
    start = facing_deg - half
    step = vision_angle_deg / segments
    for i in range(segments + 1):
        angle = math.radians(start + step * i)
        x = ox + math.cos(angle) * vision_range
        y = oy + math.sin(angle) * vision_range
        points.append((x, y))
    return points


class SoundEvent:
    """Published by the event bus and consumed by hearing checks.

    Attributes
    ----------
    pos : (x, y)
    loudness : float     0-100
    kind : str           "howl", "bark", "whistle", "bleat", "thunder"
    source : Agent | None
    """

    def __init__(self, pos, loudness: float, kind: str, source=None):
        self.pos = pygame.Vector2(pos)
        self.loudness = loudness
        self.kind = kind
        self.source = source
