#!/usr/bin/env python3
"""Crit / hit chance using deterministic rolls."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rrann import roll


def attack(seed: float, turn: int, *, hit_chance: float = 0.85, crit_chance: float = 0.15):
    hit_u = float(roll(seed, "combat.hit", turn))
    if hit_u >= hit_chance:
        return "miss", 0
    crit_u = float(roll(seed, "combat.crit", turn))
    base = 10
    if crit_u < crit_chance:
        return "crit", base * 2
    return "hit", base


def main() -> None:
    seed = 2.4
    for turn in range(8):
        kind, dmg = attack(seed, turn)
        print(f"turn {turn}: {kind:4s} dmg={dmg}")


if __name__ == "__main__":
    main()
