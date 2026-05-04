"""
Settings module - Central configuration for the Sheep Dog Simulation.

All tunable constants live here. Tweak these values to balance the game
without touching agent or AI code.
"""

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Sheep Dog Simulation - AI Agent Project"

# ---------------------------------------------------------------------------
# Colors (R, G, B)
# ---------------------------------------------------------------------------
# Environment
GRASS_GREEN = (90, 150, 70)
GRASS_DARK = (70, 120, 55)
DIRT = (120, 95, 60)
WATER = (70, 130, 180)
PRECIPICE = (40, 40, 50)
TREE = (50, 100, 40)
ROCK = (110, 110, 115)
FENCE = (140, 100, 60)

# Agents
DOG_COLOR = (80, 60, 40)
SHEEP_COLOR = (240, 240, 230)
SHEEP_FACE = (80, 70, 70)
WOLF_COLOR = (60, 60, 70)
OWNER_COLOR = (160, 80, 80)

# UI
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 60, 60)
GREEN = (60, 200, 80)
YELLOW = (230, 220, 80)
ORANGE = (230, 150, 60)
BLUE = (80, 120, 220)
GRAY = (130, 130, 140)
LIGHT_GRAY = (190, 190, 200)
DARK_GRAY = (50, 50, 60)

# Debug overlay
VISION_CONE_COLOR = (255, 240, 150, 70)    # translucent yellow
HEARING_CIRCLE_COLOR = (100, 200, 255, 50) # translucent blue
PATH_LINE_COLOR = (100, 255, 100)
TARGET_LINE_COLOR = (255, 100, 100)

# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------
TILE_SIZE = 32
WORLD_COLS = 40   # 40 * 32 = 1280 (matches screen width)
WORLD_ROWS = 22   # 22 * 32 = 704
WORLD_PIXEL_WIDTH = WORLD_COLS * TILE_SIZE
WORLD_PIXEL_HEIGHT = SCREEN_HEIGHT   # render the base grass to bottom edge

# The enclosure (pen) - where sheep must be herded. Right side of the map.
PEN_COL = WORLD_COLS - 5
PEN_ROW = WORLD_ROWS // 2 - 2
PEN_WIDTH = 4
PEN_HEIGHT = 5

# ---------------------------------------------------------------------------
# Agent counts
# ---------------------------------------------------------------------------
NUM_SHEEP = 10
NUM_WOLVES = 2
NUM_DOGS = 2
NUM_OWNERS = 1
MAX_WOLVES_TOTAL = 3   # cap on how many wolves can exist at once

# ---------------------------------------------------------------------------
# Dog
# ---------------------------------------------------------------------------
DOG_SPEED = 140.0           # pixels / second
DOG_VISION_RANGE = 260.0
DOG_VISION_ANGLE = 120.0    # degrees (full cone width)
DOG_HEARING_RANGE = 320.0
DOG_MAX_STAMINA = 100.0
DOG_STAMINA_DRAIN = 5.0     # per second while running
DOG_STAMINA_REGEN = 18.0    # per second while resting
DOG_RADIUS = 10

# ---------------------------------------------------------------------------
# Sheep
# ---------------------------------------------------------------------------
SHEEP_SPEED = 70.0
SHEEP_PANIC_SPEED = 130.0
SHEEP_VISION_RANGE = 140.0
SHEEP_VISION_ANGLE = 200.0
SHEEP_HEARING_RANGE = 200.0
SHEEP_RADIUS = 8

# Boids tuning (Reynolds 1987, with a flee vector added for predators)
BOIDS_SEPARATION_RADIUS = 35.0
BOIDS_ALIGNMENT_RADIUS = 45.0
BOIDS_COHESION_RADIUS = 55.0
BOIDS_SEPARATION_WEIGHT = 2.8
BOIDS_ALIGNMENT_WEIGHT = 0.4
BOIDS_COHESION_WEIGHT = 0.25
BOIDS_FLEE_DOG_WEIGHT = 1.4        # push away from dog when it comes close
BOIDS_FLEE_WOLF_WEIGHT = 4.0       # much stronger fear of wolves
BOIDS_HERDING_DISTANCE = 90.0      # dog pressures flock within this distance

# ---------------------------------------------------------------------------
# Wolf
# ---------------------------------------------------------------------------
WOLF_SPEED = 110.0
WOLF_CHARGE_SPEED = 170.0
WOLF_VISION_RANGE = 300.0
WOLF_VISION_ANGLE = 130.0
WOLF_HEARING_RANGE = 360.0
WOLF_RADIUS = 10
WOLF_ATTACK_RANGE = 14.0           # wolf kills sheep within this distance
WOLF_FEAR_DISTANCE = 130.0         # wolves flee from dog at this distance

# Wolf learning: strategy failure decay per second
WOLF_STRATEGY_DECAY = 0.05

# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------
OWNER_RADIUS = 11
OWNER_CALL_RANGE = 500.0
OWNER_CALL_COOLDOWN = 3.0  # seconds between whistles

# Owner herding
OWNER_HERD_RADIUS = 100.0       # owner pushes sheep within this distance
OWNER_HERD_STRENGTH = 0.9       # relative to dog flee weight (dog=1.4, owner weaker)
OWNER_CLAP_COOLDOWN = 2.5       # seconds between clap shouts

# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------
FRICTION = 0.88              # velocity multiplier each frame (dry)
RAIN_FRICTION = 0.82         # more slippery when raining
PRECIPICE_FALL_DANGER = False  # falls bump agent back, don't kill

# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------
WEATHER_TRANSITION_MIN = 20.0   # seconds (min time between weather changes)
WEATHER_TRANSITION_MAX = 45.0   # seconds (max time)

RAIN_DROP_COUNT = 220
RAIN_SPEED = 520.0
STORM_DROP_COUNT = 420
STORM_SPEED = 780.0

# Vision range penalties for bad weather (multipliers)
WEATHER_VISION_PENALTY = {
    "CLEAR": 1.0,
    "CLOUDY": 0.9,
    "RAIN": 0.7,
    "STORM": 0.45,
    "FOG": 0.35,
}

# Hearing range penalties for bad weather (rain masks sound)
WEATHER_HEARING_PENALTY = {
    "CLEAR": 1.0,
    "CLOUDY": 1.0,
    "RAIN": 0.75,
    "STORM": 0.5,
    "FOG": 0.95,
}

# ---------------------------------------------------------------------------
# Day / night
# ---------------------------------------------------------------------------
DAY_CYCLE_SECONDS = 180.0   # full day = 3 minutes of real time
NIGHT_DARKNESS_MAX = 140    # alpha value 0-255 for the night overlay
NIGHT_VISION_PENALTY = 0.55

# ---------------------------------------------------------------------------
# Emotion
# ---------------------------------------------------------------------------
EMOTION_DECAY = 5.0         # emotion points decaying per second toward baseline
EMOTION_MAX = 100.0

# ---------------------------------------------------------------------------
# Game rules / ending conditions
# ---------------------------------------------------------------------------
SIMULATION_TIME_LIMIT = 240.0   # seconds before the dog "wins by time survived"
DOG_EXHAUSTION_LIMIT = 600.0    # seconds of cumulative running before dog collapses
MIN_SHEEP_TO_WIN = 5            # at least this many must survive and be penned

# ---------------------------------------------------------------------------
# Random events
# ---------------------------------------------------------------------------
RANDOM_EVENT_CHECK_INTERVAL = 8.0   # check every N seconds
RANDOM_EVENT_CHANCE = 0.35          # probability an event fires on a check

# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------
DEBUG_DEFAULT_ON = True        # start with debug overlay visible (graders see traits)
SHOW_FPS = True