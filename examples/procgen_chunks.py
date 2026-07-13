#!/usr/bin/env python3
"""Proc-gen style: independent chunk streams via Rng.fork(chunk_id)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rrann import Rng


def generate_chunk(master: float, chunk_id: int, size: int = 4) -> list[list[float]]:
    """Return a small heightmap-like grid; independent of other chunks."""
    g = Rng(master).fork(chunk_id)
    grid = []
    for _ in range(size):
        row = [round(g.random(), 4) for _ in range(size)]
        grid.append(row)
    return grid


def main() -> None:
    master = 2.4
    # Parallel-safe: each chunk is fork(id); order of generation does not matter
    c0 = generate_chunk(master, 0)
    c1 = generate_chunk(master, 1)
    c0b = generate_chunk(master, 0)
    assert c0 == c0b
    assert c0 != c1
    print("chunk 0 row0:", c0[0])
    print("chunk 1 row0:", c1[0])
    print("chunk 0 regenerated identical:", c0 == c0b)


if __name__ == "__main__":
    main()
