# Sheep Dog Simulation

An intelligent-agent simulation built in Python with Pygame-CE. A sheep
dog must herd a flock of sheep into an enclosure while defending them
from a learning wolf pack. The environment features dynamic weather, a
day/night cycle, and random happenings so no two runs play out the same.

This project was built for an Intelligent Agent / AI assignment and maps
one-to-one to the grading rubric; see the checklist at the bottom.

---

## Quick Start

```bash
# 1. create a virtual environment (optional but recommended)
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 2. install the one dependency
pip install -r requirements.txt

# 3. run
python main.py
```

You should see the title screen. Press **SPACE** or **ENTER** to start.

Runs on Python 3.9+. No assets need to be downloaded — all sprites are
drawn procedurally with shapes.

---

## Controls

| Input | Action |
|---|---|
| **Left click** (on the map) | Move the shepherd (you) to that spot |
| **Right click** (on a wolf) | Command dog to chase that specific wolf |
| **Right click** (on a sheep) | Command dog to drive that sheep toward pen |
| **Right click** (empty area) | Command dog to go to that point |
| **Spacebar** | Whistle - dog returns to you, cancels active command |
| **F1** | Toggle debug overlay - vision cones, hearing circles, A* path, state pills |
| **F2** | Toggle rubric checklist overlay |
| **F3** | Toggle the always-on legend in the top-left corner |
| **R** | Reset the simulation with a new random seed |
| **ESC** | Quit |

The dog has two layers of intelligence: it autonomously herds, chases
threatening wolves, and rests when tired - but right-click commands
override that when you want to take direct control.

When you start, a **HOW TO PLAY** overlay explains everything with a
legend of what each sprite is. Press any key to begin. You'll also see:

- A **pulsing yellow arrow** above the pen showing where to herd sheep
- An **objective banner** at the top updating with your current goal
- **Floating notifications** when sheep are saved (+1 SAVED in green)
  or killed (−1 LOST in red)
- A **permanent legend** in the top-left so you never forget what is what

The debug overlay is **on by default** so every intelligence trait is
visible in the first screenshot.

---

## How to Play

The shepherd you control is on the left. The dog (`Rex`) starts next to
you. A flock of white sheep is grazing nearby. Three wolves roam the
edges of the map and will try to pick off stray sheep.

**Your goal**: get at least 5 sheep into the green-tinted pen on the
right before the 4-minute timer runs out, before too many are eaten, or
before the dogs collapse from exhaustion.

You have **two dogs**:
- **Rex (brown)** — the herder. Prioritizes pushing sheep toward the pen.
- **Buddy (dark grey)** — the defender. Prioritizes chasing wolves.

Right-click commands target whichever dog is closer to the click, so
you can direct them independently.

The dog is autonomous — you don't steer it directly. What you *can* do:

- **Whistle** (spacebar) to call the dog back to you. Useful if it's
  chasing a wolf in the wrong direction or burning stamina uselessly.
- **Walk** (left click) to re-position. Sheep don't follow you, but the
  dog's `RETURNING` state uses your position, so this relocates its
  anchor point.
- Let the dog do its job. It will autonomously switch between herding,
  chasing wolves, resting, and returning.

---

## Five Possible Endings

| Ending | Trigger |
|---|---|
| **PERFECT — All Sheep Saved** | All alive sheep penned, and at least 6 survive |
| **Partial Win** | Timer runs out with 6+ sheep penned |
| **Partial Loss** | Timer runs out with fewer than 6 sheep penned |
| **Disaster — Wolves Won** | Every sheep killed before the timer |
| **Dog Collapsed** | Dog ran itself to exhaustion |

---

## Architecture (one-line tour)

```
main.py                   entry point
src/
├── core/
│   ├── settings.py       every tunable constant lives here
│   ├── event_bus.py      pub/sub so agents don't hold direct refs
│   └── game.py           main loop + scene management
├── ai/
│   ├── fsm.py            finite state machine with transition log
│   ├── perception.py     cone of vision + hearing radius
│   ├── pathfinding.py    A* with octile heuristic + LOS smoothing
│   └── boids.py          Reynolds flocking + predator flee vectors
├── agents/
│   ├── agent.py          base: emotion, memory, physics, speech
│   ├── dog.py            7-state FSM, utility-based choice, A* follower
│   ├── sheep.py          6-state FSM, boids steering
│   ├── wolf.py           6-state FSM, strategy LEARNING (4 strategies)
│   └── owner.py          human-controlled shepherd
├── world/
│   ├── world.py          tile map, spawning, random events, endings
│   ├── weather.py        Markov FSM: CLEAR/CLOUDY/RAIN/STORM/FOG
│   └── day_night.py      day/night cycle, vision penalty at night
└── rendering/
    ├── renderer.py       procedural sprite drawing
    ├── debug_draw.py     vision cones, hearing, paths, state labels
    └── hud.py            status bar, title screen, ending screen
```

See `DESIGN.md` for the design details, state diagrams, and citations.

---

## Rubric Checklist

Every requirement from the assignment rubric, mapped to a file so it can
be inspected directly:

| Requirement | Where it lives |
|---|---|
| Intelligent agent pursues a goal | `src/agents/dog.py` |
| State-based behavior | `src/ai/fsm.py` + every agent's `fsm` attr |
| State transitions on events | `src/agents/dog.py::_on_whistle` / `_on_wolf_howl` / `_on_sheep_killed` |
| No predefined sequence | `src/world/world.py::_fire_random_event` + Markov weather |
| Multiple alternative endings | `src/world/world.py::_check_endings` (5 endings) |
| Random happenings | `src/world/world.py::_fire_random_event` |
| NL communication | `src/agents/agent.py::say()` + speech bubbles (`renderer.py::_draw_speech`) |
| Perception — vision | `src/ai/perception.py::can_see` |
| Perception — hearing | `src/ai/perception.py::can_hear` |
| Emotional intelligence | `src/agents/agent.py::Emotion` (fear / anger / happiness) |
| Learning | `src/agents/wolf.py::choose_strategy` + `record_failure / record_success` |
| Searching / pathfinding | `src/ai/pathfinding.py` (A*) |
| Decision making | `src/agents/dog.py::_choose_state` (utility scoring) |
| Real-world physics — friction | `src/agents/agent.py::update` |
| Real-world physics — inverse-distance sound | `src/ai/perception.py::can_hear` |
| Real-world physics — precipice death | `src/agents/agent.py::_resolve_tile_collisions` |
| Cone of vision | `src/ai/perception.py::can_see` (uses facing_deg + dot product) |
| Time-of-day affecting vision | `src/world/day_night.py::vision_multiplier` |
| Natural phenomena (rain / sun / dark / storm) | `src/world/weather.py` |

The total number of implemented intelligence traits is **six** (the
rubric requires three, and a higher grade requires three plus real-world
physics).

---

## Testing (optional)

A small smoke-test suite is in `tests/`. Run with:

```bash
pip install pytest
pytest tests/
```

It exercises the FSM transitions, the A* pathfinder on a hand-built
grid, and the can_see / can_hear perception primitives.

---

## Credits

- Pygame-CE - LGPL, [pygame-community/pygame-ce](https://github.com/pygame-community/pygame-ce)
- Boids algorithm - Craig Reynolds, 1987
- A* - Hart, Nilsson, Raphael, 1968
- Roguebasin shadowcasting references for vision cone ideas
- All sprites are drawn procedurally in `src/rendering/renderer.py` — no
  external assets are shipped with this project.

MIT-style license. Built for academic use.
