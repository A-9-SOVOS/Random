#!/usr/bin/env python3
"""Loot-table demo: fork streams, deterministic rolls, commit–reveal receipt."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rrann import (
    Rng,
    commit_seed,
    create_receipt,
    health_check,
    roll,
    verify_receipt,
)

# Simple weighted table: (name, cumulative upper bound in [0,1))
TABLE = [
    ("common", 0.70),
    ("uncommon", 0.90),
    ("rare", 0.98),
    ("legendary", 1.00),
]


def pick(u: float) -> str:
    for name, hi in TABLE:
        if u < hi:
            return name
    return TABLE[-1][0]


def main() -> None:
    master = 2.4
    game_id = "demo-rpg"
    season = "s1"

    print("=== health (gameplay) ===")
    h = health_check(master, n_bits=4096, profile="gameplay")
    print(f"  status={h.status} ok={h.ok} monobit_z={h.monobit_z:.2f} runs_z={h.runs_z:.2f}")

    print("\n=== commit seed (publish before rolls) ===")
    commit = commit_seed(master, game_id=game_id, season=season)
    print(f"  commit={commit[:16]}…")

    print("\n=== 5 chest rolls (deterministic context+counter) ===")
    for n in range(5):
        u = roll(master, "loot.chest", n)
        item = pick(float(u))
        print(f"  n={n} u={float(u):.6f} → {item}")

    print("\n=== receipt create / verify ===")
    receipt = create_receipt(
        master, "loot.chest", 0, game_id=game_id, season=season
    )
    print(f"  result={receipt.result} algo={receipt.algo_version}")
    ok = verify_receipt(receipt, master, game_id=game_id, season=season)
    print(f"  verify_ok={ok}")
    bad = verify_receipt(receipt, 9.9, game_id=game_id, season=season)
    print(f"  verify_wrong_seed={bad}")

    print("\n=== forked region streams (parallel-safe) ===")
    g = Rng(master)
    for region in (0, 1, 2):
        rg = g.fork(region)
        print(f"  region {region}: first float={rg.random():.6f}")


if __name__ == "__main__":
    main()
