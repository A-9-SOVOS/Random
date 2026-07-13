#!/usr/bin/env python3
"""
Optional light mixer: take RRann u64 blocks and run through splitmix64.

This is a *finalizer/mixer*, not extra entropy. Useful when you want faster
downstream scrambling after residual extract.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rrann import Rng


def splitmix64(x: int) -> int:
    """Standard splitmix64 finalizer (public domain algorithm)."""
    x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = x
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9 & 0xFFFFFFFFFFFFFFFF
    z = (z ^ (z >> 27)) * 0x94D049BB133111EB & 0xFFFFFFFFFFFFFFFF
    return (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF


def main() -> None:
    g = Rng(2.4)
    raw = [g.next_u64() for _ in range(4)]
    mixed = [splitmix64(x) for x in raw]
    print("raw   ", [hex(x) for x in raw])
    print("mixed ", [hex(x) for x in mixed])
    print("note: mixer is deterministic post-processing, not a new entropy source")


if __name__ == "__main__":
    main()
