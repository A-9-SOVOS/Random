#!/usr/bin/env python3
"""Minimal usage examples for rrann."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import rrann
from rrann import Rng, create_receipt, health_check, roll, verify_receipt


def main() -> None:
    print("rrann", rrann.__version__, "algo", rrann.ALGO_VERSION)
    print("cull_head default", rrann.DEFAULT_CULL_HEAD)

    print("legacy generate(2.4) =", rrann.generate(2.4))
    print("extract_float(2.4)   =", rrann.extract_float(2.4, cull_head=2))

    g = Rng(seed=2.4, cull_head=2, mode="remainder")
    print("five floats:", [round(g.random(), 6) for _ in range(5)])
    print("64-bit int: ", g.next_u64())
    print("fork(0) vs fork(1):", g.fork(0).random(), g.fork(1).random())

    print("roll(loot,0):", roll(2.4, "loot", 0))
    r = create_receipt(2.4, "loot", 0, game_id="demo")
    print("receipt verify:", verify_receipt(r, 2.4, game_id="demo"))

    h = health_check(2.4, n_bits=2048, profile="gameplay")
    print(f"health: {h.status} ok={h.ok}")

    hv = rrann.harvest(2.4)
    print(
        "diverge",
        hv.divergence_index,
        "head",
        hv.head,
        "remainder",
        hv.remainder(cull_head=2)[:8] + "...",
    )


if __name__ == "__main__":
    main()
