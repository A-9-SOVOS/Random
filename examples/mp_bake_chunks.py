#!/usr/bin/env python3
"""
Offline bake: many chunks in parallel via independent forks.

Pattern: seed_i = mix(master, stream_id)  — never share one chain across processes.
"""

from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _bake_one(args: tuple) -> tuple[int, float]:
    master, chunk_id = args
    # Import inside worker for spawn-safe Windows/macOS
    sys.path.insert(0, str(_ROOT))
    from rrann import Rng

    g = Rng(master).fork(chunk_id)
    # checksum of a few samples
    acc = sum(g.random() for _ in range(32))
    return chunk_id, acc


def main() -> None:
    master = 2.4
    chunk_ids = list(range(16))
    results = {}
    with ProcessPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(_bake_one, (master, cid)) for cid in chunk_ids]
        for fut in as_completed(futs):
            cid, acc = fut.result()
            results[cid] = acc
    # sequential check on one id
    from rrann import Rng

    g = Rng(master).fork(3)
    seq = sum(g.random() for _ in range(32))
    assert abs(results[3] - seq) < 1e-12
    print("baked chunks:", len(results))
    print("chunk 3 checksum match sequential:", results[3])


if __name__ == "__main__":
    main()
