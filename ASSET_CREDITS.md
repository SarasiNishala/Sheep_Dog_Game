# Asset Credits

This project **ships no external art or audio assets**. Every visual
element is drawn procedurally inside `src/rendering/renderer.py` using
Pygame's native shape-drawing functions. Every "sound" is represented
as an event-bus message (see `src/core/event_bus.py`) rather than a
WAV file, so no royalty-bearing audio is included.

The only third-party dependency used at runtime:

- **Pygame Community Edition** (`pygame-ce`)
  - License: LGPL v2.1
  - Source: https://github.com/pygame-community/pygame-ce
  - Pinned in `requirements.txt`

## Algorithms & Academic References

- **Boids flocking** — Craig Reynolds, 1987
  - "Flocks, herds and schools: A distributed behavioral model",
    SIGGRAPH '87 Conference Proceedings
- **A* search** — Hart, Nilsson, Raphael, 1968
  - IEEE Transactions on Systems Science and Cybernetics, vol. 4(2)
- **Game AI state machines & utility** — Orkin (2006) *Three States
  and a Plan: The AI of F.E.A.R.*, GDC proceedings

## Sprite design inspiration (procedurally reproduced, not copied)

Silhouettes were inspired by the generic top-down shepherding genre
(no specific game cloned). All pixel data is produced live at runtime
by shape-drawing calls — nothing copied from any source.
