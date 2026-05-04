"""
Sheep Dog Simulation - entry point.

Run with:
    python main.py

Requires: pygame (or pygame-ce).  See requirements.txt.
"""

import sys
import traceback

from src.core.game import Game


def main():
    try:
        game = Game()
        game.run()
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
