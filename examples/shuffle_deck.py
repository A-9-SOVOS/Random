#!/usr/bin/env python3
"""Deterministic Fisher–Yates shuffle driven by rrann.roll."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, TypeVar

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rrann import roll

T = TypeVar("T")


def shuffle(seed: float, items: List[T], *, context: str = "deck.shuffle") -> List[T]:
    deck = list(items)
    n = len(deck)
    for i in range(n - 1, 0, -1):
        # unbiased-ish index in 0..i via 32-bit roll
        r = int(roll(seed, context, i, kind="int", bits=32))
        j = r % (i + 1)
        deck[i], deck[j] = deck[j], deck[i]
    return deck


def main() -> None:
    ranks = [f"{r}{s}" for s in "SHDC" for r in "A23456789TJQK"]
    seed = 2.4
    a = shuffle(seed, ranks)
    b = shuffle(seed, ranks)
    assert a == b
    print("top 10:", " ".join(a[:10]))
    print("same seed again:", " ".join(b[:10]))
    print("other seed top:", " ".join(shuffle(3.1, ranks)[:10]))


if __name__ == "__main__":
    main()
