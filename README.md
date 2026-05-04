# 🐑 Sheepdog Simulation

A real-time multi-agent AI simulation built with **Python** and **pygame-ce**.  
Guide your sheepdogs to herd a flock of sheep into the pen, defend them from a learning wolf pack, and race against a 4-minute timer — all while managing your dog's stamina.

Built as a group project for an Intelligent Agents / AI assignment.

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Controls](#-controls)
- [How to Play](#-how-to-play)
- [Game Endings](#-game-endings)
- [Agents](#-agents)
- [AI Systems](#-ai-systems)
- [Project Structure](#-project-structure)
- [Tuning & Configuration](#-tuning--configuration)
- [Rubric Checklist](#-rubric-checklist)
- [Running Tests](#-running-tests)
- [Credits](#-credits)

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd sheepdog_sim

# 2. (Optional but recommended) Create a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install the single dependency
pip install -r requirements.txt

# 4. Run
python main.py
```

**Requirements:** Python 3.9+, pygame-ce 2.5.7  
No external assets needed — all sprites are drawn procedurally with shapes.

Press **SPACE** or **ENTER** on the title screen to begin.

---

## 🎮 Controls

| Input | Action |
|---|---|
| **Left Click** | Move the owner (farmer) to that position |
| **Right Click on wolf** | Command dog to chase that wolf |
| **Right Click on sheep** | Command dog to drive that sheep toward the pen |
| **Right Click on empty area** | Command dog to go to that position |
| **SPACE** | Whistle — sheep flock toward you for 5 s, dog returns to owner |
| **H** | Toggle Herd Mode — owner pushes nearby sheep toward pen |
| **F1** | Toggle debug overlay (vision cones, A* paths, FSM state labels, event log) |
| **F2** | Toggle rubric checklist overlay |
| **F3** | Toggle compact controls legend |
| **R** | Restart with a new random map |
| **ESC** | Quit |

---

## 🐕 How to Play

Your goal is to get **at least 5 out of 10 sheep** into the green pen on the right side of the map before the **4-minute timer** runs out.

### Step-by-step tips

1. **Press SPACE at the start** — sheep are drawn toward you for 5 seconds. Walk to the centre of the map to loosely group them.
2. **Right-click behind the flock** (between the sheep and the pen) to send the dog around. The dog positions itself behind the flock and pushes them forward automatically.
3. **Use H (Herd Mode)** when sheep are near the pen entrance to add extra pressure.
4. **Right-click directly on a wolf** to send the dog to intercept it. The second dog handles nearby wolves on its own.
5. **Watch the stamina bar** above the dog. If it turns red, stop issuing commands and let the dog rest for a few seconds.
6. **For stragglers**, right-click directly on a specific sheep to drive it individually.
7. **Press SPACE again** whenever scattered sheep need recalling (3-second cooldown).

### On-screen indicators

| Indicator | Meaning |
|---|---|
| Green stamina bar | Dog is healthy |
| Yellow stamina bar | Dog is getting tired |
| Red stamina bar | Dog is near collapse — let it rest |
| Green dot above sheep | Sheep is safely penned |
| Blue dot above agent | Agent is frightened |
| Red dot above agent | Agent is angry |
| Coloured ring around dog | FSM state: Green=Idle, Yellow=Herding, Red=Chasing wolf, Blue=Returning, Grey=Resting |
| Pulsing green aura | Owner Herd Mode is active |
| Arrow at screen edge | Points toward the pen |

---

## 🏁 Game Endings

| Ending | Trigger |
|---|---|
| 🌟 **Perfect Run** | All currently alive sheep are penned (≥ 5) |
| ✅ **Success** | Timer runs out with ≥ 5 sheep penned, some still outside |
| ⚠️ **Too Few Saved** | Timer runs out with fewer than 5 sheep penned |
| 🐺 **The Wolves Won** | Wolves kill enough sheep that victory becomes mathematically impossible |
| 💀 **Dog Collapsed** | Dog's stamina hits zero, or a dog falls into a precipice |

---

## 🐾 Agents

### 🐑 Sheep (10 per game)
Sheep are fully autonomous. They graze spread across the field and react to threats.

| State | Behaviour |
|---|---|
| GRAZING | Wanders independently, boids forces suppressed |
| ALERT | Heard a threat; clusters slightly |
| FLEEING | Wolf visible; panics at full speed |
| HERDED | Dog or owner pushing; steers toward pen |
| PENNED | Inside pen — permanent safe state |
| DEAD | Killed by wolf or fell in precipice |

### 🐕 Rex — Primary Dog (herder)
Uses A* pathfinding and the Strömback shepherding algorithm to position behind the flock and push them toward the pen.

**Stamina:** 100 pts max · drains 5 pts/s while running · regenerates 18 pts/s while resting

### 🐕 Buddy — Second Dog (defender)
Focuses on intercepting wolves. Same rules and appearance as Rex. Both dogs are brown.

### 🐺 Wolves (2 at start, up to 3)
Each wolf learns from experience using a **weighted strategy system** across 4 hunting approaches:

| Strategy | Approach |
|---|---|
| `charge_frontal` | Sprint directly at the target sheep |
| `sneak_flank` | Approach from the side of the sheep's movement |
| `ambush_bush` | Approach from behind the sheep |
| `howl_scatter` | Howl to scatter the flock, then charge |

Failed strategies get a higher failure score and are picked less often. Scores decay over time so mistakes are eventually forgotten.

### 🧑‍🌾 Owner (Player)
Left-click to walk. **SPACE** to whistle (recalls dog + pulls all sheep within ~430px toward you for 5 seconds). **H** to toggle Herd Mode (sustained push of nearby sheep).

---

## 🤖 AI Systems

### Finite State Machine (FSM)
Every agent has an FSM tracking current state, time in state, and a 20-entry transition log. The log is visible in the F1 debug overlay.

### Boids Flocking
Reynolds 1987 algorithm drives sheep movement using six steering vectors:

| Vector | Weight | Effect |
|---|---|---|
| Separation | 2.8 | Push away from neighbours within 35px |
| Alignment | 0.4 | Match heading of neighbours within 45px |
| Cohesion | 0.25 | Steer toward centre of neighbours within 55px |
| Flee dog | 1.4 | Run from dog within 90px |
| Flee wolf | 4.0 | Panic flee from wolves |
| Flee owner | 0.9 | Flee from owner in Herd Mode |

During `GRAZING`, boids forces are suppressed to **5%** so sheep spread naturally across the field.

### A* Pathfinding
The dog uses A* on the 40×22 tile grid with an octile distance heuristic and Bresenham line-of-sight path smoothing. Replans every 0.8–1.5 seconds to track moving targets.

### Perception
- **Vision cone** — dot product of facing vector vs direction-to-target, limited by range and angle
- **Hearing** — inverse-linear falloff: `perceived = loudness − distance × 0.1`
- Both are multiplied by day/night and weather penalties at runtime

### Event Bus
Pub/sub system for inter-agent communication. Key events: `owner_whistle`, `sheep_bleat`, `wolf_howl`, `dog_bark`, `sheep_penned`, `sheep_killed`, `dog_exhausted`.

---

## 📁 Project Structure

```
sheepdog_sim/
├── main.py                   Entry point
├── requirements.txt
├── src/
│   ├── core/
│   │   ├── settings.py       All tunable constants
│   │   ├── event_bus.py      Publish/subscribe messaging
│   │   └── game.py           Main loop, input, scene management
│   ├── ai/
│   │   ├── fsm.py            Finite State Machine
│   │   ├── perception.py     Vision cone + hearing
│   │   ├── pathfinding.py    A* + path smoothing
│   │   └── boids.py          Reynolds flocking
│   ├── agents/
│   │   ├── agent.py          Base class (emotion, memory, physics)
│   │   ├── sheep.py          Sheep FSM + boids + whistle response
│   │   ├── dog.py            Dog FSM + A* + Strömback herding
│   │   ├── wolf.py           Wolf FSM + strategy learning
│   │   └── owner.py          Owner + whistle + herd mode
│   ├── world/
│   │   ├── world.py          Map generation, spawning, endings
│   │   ├── weather.py        Weather state machine
│   │   └── day_night.py      Day/night cycle + vision penalty
│   └── rendering/
│       ├── renderer.py       Procedural pixel-art drawing
│       ├── hud.py            HUD, title screen, ending screen
│       ├── debug_draw.py     F1 debug overlay
│       ├── tutorial.py       Notifications, pen arrow, legend
│       └── ui_theme.py       Colours and font helpers
└── tests/
    └── test_smoke.py
```

---

## ⚙️ Tuning & Configuration

All constants are in `src/core/settings.py`. Nothing is hardcoded elsewhere.

```python
# Difficulty
NUM_SHEEP             = 10       # total sheep per game
NUM_WOLVES            = 2        # starting wolves
MIN_SHEEP_TO_WIN      = 5        # minimum to pen for any win
SIMULATION_TIME_LIMIT = 240.0    # seconds (4 minutes)

# Dog stamina
DOG_MAX_STAMINA       = 100.0
DOG_STAMINA_DRAIN     = 5.0      # pts/s while running
DOG_STAMINA_REGEN     = 18.0     # pts/s while resting

# Sheep spreading (lower = more spread out)
BOIDS_COHESION_WEIGHT = 0.25
BOIDS_COHESION_RADIUS = 55.0
```

---

## 📐 Rubric Checklist

| AI Requirement | Location |
|---|---|
| Intelligent agent pursuing a goal | `src/agents/dog.py` |
| Finite State Machine | `src/ai/fsm.py` + all agents |
| State transitions on events | `dog.py::_on_whistle`, `_on_wolf_howl` |
| No predefined sequence | `world.py::_fire_random_event` + Markov weather |
| Multiple alternative endings (5) | `world.py::_check_endings` |
| Random happenings | `world.py::_fire_random_event` |
| Natural language communication | `agent.py::say()` + speech bubbles |
| Perception — vision cone | `ai/perception.py::can_see` |
| Perception — hearing | `ai/perception.py::can_hear` |
| Emotional intelligence | `agent.py::Emotion` (fear / anger / happiness) |
| **Learning** | `wolf.py::choose_strategy` + `record_failure/success` |
| Searching / pathfinding (A*) | `ai/pathfinding.py` |
| Decision making | `dog.py::_choose_state` |
| Physics — friction | `agent.py::update` |
| Physics — inverse-distance sound | `ai/perception.py::can_hear` |
| Physics — precipice danger | `agent.py::_resolve_tile_collisions` |
| Day/night affecting vision | `world/day_night.py::vision_multiplier` |
| Natural phenomena (weather) | `world/weather.py` |

---

## 🧪 Running Tests

```bash
pip install pytest
pytest tests/
```

Tests cover FSM transitions, A* on a hand-built grid, and perception primitives.

---

## 👥 Group Members & Responsibilities

| Part | Responsibility |
|---|---|
| **Part 1** | AI & Decision Making — FSM, Boids, A*, Perception, Event Bus |
| **Part 2** | Agents: Dog & Owner — Strömback herding, stamina, commands, whistle |
| **Part 3** | Agents: Wolf & Sheep — strategy learning, boids, emotion, bleat system |
| **Part 4** | World, Rendering & Core — map generation, day/night, weather, HUD |

---

## 📚 Credits

- **pygame-ce** — LGPL — [pygame-community/pygame-ce](https://github.com/pygame-community/pygame-ce)
- **Boids algorithm** — Craig Reynolds, 1987
- **A* pathfinding** — Hart, Nilsson & Raphael, 1968
- **Strömback shepherding model** — Strömback et al., 2006
- All sprites drawn procedurally in `src/rendering/renderer.py` — no external assets

---

*Built for academic use. MIT-style licence.*
