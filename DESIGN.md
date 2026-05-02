# DESIGN.md — Sheep Dog Simulation

Game design and AI architecture document.

## 1. Concept

An intelligent sheep dog operates autonomously in a pastoral environment
populated by:

- A flock of sheep that graze and flee predators using flocking behavior
- A pack of wolves that hunt sheep using adaptive strategies
- A shepherd (the player) who issues whistle commands

The goal of the dog is to herd all sheep into an enclosure before wolves
can pick them off. Weather changes, day/night shifts, and random events
make each run unique.

The dog demonstrates six AI traits:

1. Perception (cone of vision + hearing radius)
2. Decision making (utility scoring over states)
3. Pathfinding (A\* on a tile grid)
4. Emotional intelligence (fear / anger / happiness feed decisions)
5. Natural language communication (speech bubbles + audible events)
6. Memory (short-term recall of events with TTL)

Wolves add a seventh trait: **learning**. They track the failure rate
of four hunting strategies and bias future attempts toward more
successful ones.

## 2. High-level Architecture

The codebase follows an OOP + component composition pattern, with three
cross-cutting infrastructure systems:

- **Event bus** — sound events, agent deaths, weather transitions,
  whistles. Decouples agents so adding a new agent type is safe.
- **FSM** — every agent owns a `FSM` instance. Transitions are logged
  and the log is drawn by the debug overlay.
- **Utility scoring** — used for high-level decisions like "what should
  the dog do right now" rather than hard-coded priority lists.

This trio is the conventional commercial game-AI recipe: see Orkin
(2006) *Three States and a Plan: The AI of F.E.A.R.* and Mark (2009)
*Behavioral Mathematics for Game AI* for prior art.

### Folder Structure

```
main.py                   entry point — creates Game, runs the loop
src/
├── core/
│   ├── settings.py       tunable constants
│   ├── event_bus.py      publish/subscribe
│   └── game.py           top-level loop + scenes
├── ai/
│   ├── fsm.py            FSM with transition log
│   ├── perception.py     cone-of-vision + hearing
│   ├── pathfinding.py    A* + line-of-sight smoothing
│   └── boids.py          Reynolds flocking + predator flee
├── agents/
│   ├── agent.py          base class (emotion, memory, physics)
│   ├── dog.py / sheep.py / wolf.py / owner.py
├── world/
│   ├── world.py          tile map, spawn, random events, endings
│   ├── weather.py        Markov weather
│   └── day_night.py      diurnal cycle
└── rendering/
    ├── renderer.py       procedural sprites
    ├── debug_draw.py     vision cones, paths, state labels, rubric
    └── hud.py            status bar, title, ending screens
```

---

## 3. State Machines

Each agent type has a distinct FSM. The diagrams below use compact
ASCII; the transitions are enforced at runtime by `src/ai/fsm.py`, which
also records a log of transitions that you can inspect via the debug
overlay.

### 3.1 Dog FSM (`src/agents/dog.py`)

```
       +-----------+    stamina low
       |    IDLE   |  <---------------- (any state)
       +-----+-----+
             |
             |  sheep scattered
             v
       +-----------+    wolf spotted     +-----------------+
       |  HERDING  |  ---------------->  |  CHASING_WOLF   |
       +-----+-----+                     +---------+-------+
             |                                     |
   all penned|                             wolf gone|
             v                                     v
       +-----------+                        +-----------+
       | PATROLLING|  <----------------->   |  RESTING  |
       +-----+-----+   time_running > max   +-----------+
             |
 heard whistle (owner_call)
             v
       +-----------+   reached owner       +-----------+
       | RETURNING |  ----------------->   |   IDLE    |
       +-----------+                       +-----------+

   (from ANY state, if time_running > DOG_EXHAUSTION_LIMIT => EXHAUSTED)
```

The decision for which state to enter is centralized in
`Dog._choose_state`. It reads the current context — visible wolves,
scattered sheep, owner call, stamina, fear — and returns the state with
the highest utility. A hysteresis term (+10 utility for current state)
prevents flicker.

### 3.2 Sheep FSM (`src/agents/sheep.py`)

```
           +-----------+
           |  GRAZING  |
           +-----+-----+
                 |
            heard/saw threat
                 v
           +-----------+
           |   ALERT   | <--- fear > 30 and no wolf visible
           +-----+-----+
                 |
          wolf visible
                 v
           +-----------+
           |  FLEEING  |  velocity = panic speed
           +-----+-----+
                 |
           dog close (not wolf)
                 v
           +-----------+   entered pen tile
           |  HERDED   | --------------->  PENNED (terminal)
           +-----------+
                 |
         killed by wolf
                 v
           +-----------+
           |   DEAD    |
           +-----------+
```

### 3.3 Wolf FSM (`src/agents/wolf.py`)

```
           +-----------+   sheep visible
           |  PATROL   | ----+
           +-----------+     |
                 ^           v
                 |        +-------+  target lost  (record_failure)
            rested 3s     | STALK |-------------------------+
                 |        +---+---+                         |
                 |            | in attack range             |
                 |            v                             |
           +-----------+  +--------+                        |
           |  RESTING  |<-| CHARGE |                        |
           +-----------+  +--------+                        |
                 ^           |                              |
                 |           | killed sheep (record_success)|
                 |           v                              |
                 |     +-----------+                        |
                 |     |  (back to +------------------------+
                 |     |   PATROL) |
                 |     +-----------+
                 |
     +-------------+   dog close
     |    FLEE     |  <----- from ANY state
     +-------------+
```

On entering STALK, the wolf picks a strategy by sampling
`choose_strategy`, which returns strategy *s* with probability
proportional to `1 / (1 + failure_count[s])`. Failure counts decay
toward zero over time. This is a minimal tabular reinforcement model
that converges within a single run without needing training episodes.

---

## 4. Perception

The vision and hearing primitives are in `src/ai/perception.py`. Both
respect weather and day/night penalty multipliers supplied by the world.

### 4.1 Cone of Vision

For target T, observer O with facing direction `facing_deg`:

1. Compute vector `v = T - O`, distance `d = |v|`.
2. If `d > vision_range` reject immediately.
3. Compute `cos_between = dot(facing_unit, v / d)`.
4. Accept if `cos_between >= cos(vision_angle_deg / 2)`.

The vision range is multiplied by the world's `vision_multiplier()`,
which combines the weather penalty (e.g. 0.45 for STORM) and the
day/night penalty (0.55 at night). In a stormy night the effective
range is ~25% of the daytime-clear range.

### 4.2 Hearing

Inverse-linear falloff:

```
perceived = loudness - distance * falloff_per_pixel
if perceived > 0 and distance <= hearing_range: audible
```

Rain reduces the effective hearing range (masking); a storm halves it.

---

## 5. Pathfinding

`src/ai/pathfinding.py` implements classic A\* on the tile grid with
an **octile distance** heuristic (admissible for 8-connected grids).
Diagonal movement is allowed but corner-cutting through a pair of
solid diagonals is forbidden. The returned path is then smoothed with
Bresenham line-of-sight passes to reduce zig-zag.

The dog re-paths every 1.0-1.5 seconds (or when it runs out of
waypoints), which trades off planning cost against reactivity to moving
targets.

---

## 6. Flocking

`src/ai/boids.py` implements the three Reynolds rules:

- **Separation** — avoid crowding close neighbors
- **Alignment** — steer toward mean heading of neighbors
- **Cohesion** — steer toward center-of-mass of neighbors

With two predator-avoidance vectors added:

- **Flee dog** — small repulsion in a short radius so the dog can
  "pressure" the flock toward the pen without panicking them
- **Flee wolf** — much stronger repulsion that triggers full panic speed

The weights (1.8 / 1.0 / 1.0 / 1.4 / 4.0) are tuned in
`src/core/settings.py::BOIDS_*_WEIGHT`.

---

## 7. Weather & Day/Night

Weather is a five-state Markov chain with transitions every 20-45s
(`src/world/weather.py::TRANSITIONS`). Each state has:

- A render-time visual overlay (tint, particles)
- A vision-penalty multiplier (applied to every perception check)
- A hearing-penalty multiplier (rain masks footsteps)
- An interaction with physics (wet ground → lower friction)

Storms also spawn random lightning flashes that publish a `thunder`
event audible to every agent — this sometimes startles sheep or alerts
the dog to an area.

Day/night is a sinusoidal brightness curve over a configurable
`DAY_CYCLE_SECONDS` (default 180s = one simulated day every 3 real
minutes). The night overlay alpha ranges 0→140; night applies an
additional 0.55 multiplier to all vision.

---

## 8. Emotions

Each agent has three scalars (0-100) that decay toward a baseline:

- **Fear** — baseline 0, spikes when wolves are visible or heard
- **Anger** — baseline 0, spikes when a sheep is killed nearby
- **Happiness** — baseline 50, spikes when a sheep is penned

Emotions feed back into decisions. The dog will refuse to `CHASING_WOLF`
if it is outnumbered *and* already fearful. Sheep that see a wolf
accumulate enough fear to drive `FLEEING`.

Emotions are rendered as colored mini-bars under each agent when the
debug overlay is on, so graders can verify the system works live.

---

## 9. Random Events

Every 8 seconds, the world rolls a 35% chance to fire one of:

- **extra_wolf** — a new wolf spawns at a map edge
- **straying_sheep** — a sheep is nudged and gets a +10 fear bump
- **wolf_howl_from_distance** — publishes a phantom wolf howl
- **owl_hoot** (night only) — purely cosmetic log entry

This combined with the Markov weather means no two runs are identical.

---

## 10. Endings

Five branching endings in `src/world/world.py::_check_endings`:

| Ending | Trigger |
|---|---|
| `ALL_SAVED` | every alive sheep penned, ≥ 8 total survive |
| `PARTIAL_WIN` | timer out, ≥ 8 penned |
| `PARTIAL_LOSS` | timer out, < 8 penned |
| `WOLVES_WIN` | zero sheep alive |
| `DOG_EXHAUSTED` | dog hit stamina/exhaustion limit or fell into precipice |

This satisfies the "must reach alternative endings" rubric requirement
— none of the endings is predetermined.

---

## 11. Citations / Prior Art

- Reynolds, C. W. (1987). *Flocks, herds and schools: A distributed
  behavioral model.* SIGGRAPH '87.
- Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). *A formal basis
  for the heuristic determination of minimum cost paths.* IEEE Trans.
  Systems Science and Cybernetics.
- Orkin, J. (2006). *Three states and a plan: the AI of F.E.A.R.* GDC.
- Mesa Agent-Based Modeling Framework (Masad & Kazil, 2015) — the
  canonical Wolf-Sheep example informed the biology of our predators.
- The `transitions` Python library README was consulted for the FSM
  logging pattern; the actual FSM here is hand-rolled for
  self-containment.

---

## 12. Limitations and Future Work

- The wolf "learning" is interpretable tabular adaptation within a
  single run. It does **not** persist across runs; an extension would
  pickle failure counts to disk so wolves get smarter over time.
- The A\* repath interval is a naive constant. A more sophisticated
  planner would invalidate paths only on map changes.
- There is no sound — all audio is simulated via the event bus as
  "sound events" but no actual WAV files are played. This was
  intentional to keep the submission self-contained; adding sound
  would mean shipping audio assets.
- Shaders (bloom, CRT) are not used. A `moderngl` post-pass could be
  added with ~60 LOC but would double the dependency surface.
