#!/usr/bin/env python3
"""Order-of-magnitude bench: residual extract cost (Decimal-bound)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from rrann import extract_bits, extract_float, generate, roll


def bench(name: str, fn, n: int = 200) -> None:
    # warmup
    for i in range(5):
        fn(i)
    t0 = time.perf_counter()
    for i in range(n):
        fn(i)
    dt = time.perf_counter() - t0
    us = (dt / n) * 1e6
    print(f"{name:28s}  n={n:4d}  {us:8.1f} µs/call  ({n/dt:.0f} calls/s)")


def main() -> None:
    seed = 2.4
    print("RRann bench (CPython + Decimal; lower is better)")
    print("Machine-dependent — use for order-of-magnitude only.\n")
    bench("extract_float", lambda i: extract_float(seed + i * 1e-6))
    bench("extract_bits(32)", lambda i: extract_bits(seed + i * 1e-6, 32))
    bench("legacy generate", lambda i: generate(seed + i * 1e-6))
    bench("roll(context,n)", lambda i: roll(seed, "bench", i))


if __name__ == "__main__":
    main()
