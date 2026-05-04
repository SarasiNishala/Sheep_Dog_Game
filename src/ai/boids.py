"""
Boids flocking (Reynolds 1987) for the sheep flock.

Three classical rules plus two predator-avoidance vectors:

    separation  : avoid crowding close neighbors
    alignment   : steer toward average heading of neighbors
    cohesion    : steer toward average position of neighbors
    flee_dog    : steer away from dog when close (herding pressure)
    flee_wolf   : steer away from wolves much more strongly (panic)

The force is returned as a pygame Vector2 that callers scale by dt
and add to sheep velocity.
"""

import pygame
from ..core import settings as cfg


def compute_boids_force(sheep, flock, dog, wolves, owner=None) -> pygame.Vector2:
    """Sum of the five steering vectors (+ optional owner herding).

    Parameters
    ----------
    sheep   : Sheep         - the agent we are steering
    flock   : list[Sheep]   - other sheep (may include self; we'll skip it)
    dog     : Dog           - single dog agent (or None)
    wolves  : list[Wolf]    - active wolves
    owner   : Owner         - the human player (or None); only active in herd mode
    """
    sep = pygame.Vector2(0, 0)
    ali = pygame.Vector2(0, 0)
    coh = pygame.Vector2(0, 0)

    sep_count = ali_count = coh_count = 0

    for other in flock:
        if other is sheep or not other.alive:
            continue
        diff = sheep.pos - other.pos
        distance = diff.length()

        if 0 < distance < cfg.BOIDS_SEPARATION_RADIUS:
            # push away, weighted by closeness
            sep += diff.normalize() / max(distance, 1.0)
            sep_count += 1

        if distance < cfg.BOIDS_ALIGNMENT_RADIUS:
            ali += other.velocity
            ali_count += 1

        if distance < cfg.BOIDS_COHESION_RADIUS:
            coh += other.pos
            coh_count += 1

    # finalize each vector
    if sep_count > 0:
        sep /= sep_count
    if ali_count > 0:
        ali /= ali_count
        ali = _limit(ali, cfg.SHEEP_SPEED)
    if coh_count > 0:
        coh /= coh_count
        coh = coh - sheep.pos  # steer toward center-of-mass
        if coh.length() > 0:
            coh = coh.normalize() * cfg.SHEEP_SPEED

    # flee dog (dog shouldn't come too close or flock scatters toward pen)
    flee_dog = pygame.Vector2(0, 0)
    if dog is not None and dog.alive:
        diff = sheep.pos - dog.pos
        d = diff.length()
        if 0 < d < cfg.BOIDS_HERDING_DISTANCE:
            flee_dog = diff.normalize() * cfg.SHEEP_SPEED
            # falloff: weaker pressure at edge of herding distance
            strength = 1.0 - (d / cfg.BOIDS_HERDING_DISTANCE)
            flee_dog *= strength

    # flee owner when in herd mode (weaker than dog, same idea)
    flee_owner = pygame.Vector2(0, 0)
    if owner is not None and getattr(owner, "herd_mode", False) and owner.alive:
        diff = sheep.pos - owner.pos
        d = diff.length()
        if 0 < d < cfg.OWNER_HERD_RADIUS:
            flee_owner = diff.normalize() * cfg.SHEEP_SPEED
            strength = 1.0 - (d / cfg.OWNER_HERD_RADIUS)
            flee_owner *= strength

    # flee wolves (panic)
    flee_wolf = pygame.Vector2(0, 0)
    panic_now = False
    for wolf in wolves:
        if not wolf.alive:
            continue
        diff = sheep.pos - wolf.pos
        d = diff.length()
        if 0 < d < cfg.SHEEP_VISION_RANGE:
            flee_wolf += diff.normalize() / max(d / 50.0, 0.5)
            panic_now = True
    if flee_wolf.length() > 0:
        flee_wolf = flee_wolf.normalize() * cfg.SHEEP_PANIC_SPEED

    # combine with tuned weights
    total = (
        sep * cfg.BOIDS_SEPARATION_WEIGHT
        + ali * cfg.BOIDS_ALIGNMENT_WEIGHT
        + coh * cfg.BOIDS_COHESION_WEIGHT
        + flee_dog * cfg.BOIDS_FLEE_DOG_WEIGHT
        + flee_owner * cfg.OWNER_HERD_STRENGTH
        + flee_wolf * cfg.BOIDS_FLEE_WOLF_WEIGHT
    )

    # store panic for the emotion system
    sheep.panicking = panic_now
    return total


def _limit(vec: pygame.Vector2, max_len: float) -> pygame.Vector2:
    if vec.length() > max_len:
        return vec.normalize() * max_len
    return vec