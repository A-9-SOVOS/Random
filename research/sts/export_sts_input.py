#!/usr/bin/env python3
"""Export RRann-generated bits for NIST STS (streaming, low memory).

Default comprehensive profile:
    n = 1_000_000 bits/stream × 1000 streams = 1e9 bits ≈ 119 MiB binary

Streams are generated independently (different seeds) so they can be
produced in parallel and match STS's model of separate sequences.

Examples:
    # Full comprehensive binary dump (default)
    python export_sts_input.py -o rrann_sts_1e6x1000.bin

    # Smaller smoke test
    python export_sts_input.py -o smoke.bin --bits-per-stream 1000000 --streams 10

    # Single continuous chain (legacy behavior)
    python export_sts_input.py -o chain.bin --bits 80000000 --mode chain
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Repo root (…/research/sts → …/)
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
from RRann import generate  # noqa: E402


def _pack_msb_first(word: int, nbits: int, out: bytearray, bit_buf: list) -> None:
    """Pack up to nbits from word (MSB-first within the word) into out via bit_buf.

    bit_buf is a one-element list holding the current incomplete byte state as
    (current_byte, bits_filled).
    """
    cur, filled = bit_buf[0]
    for i in range(nbits - 1, -1, -1):
        cur = (cur << 1) | ((word >> i) & 1)
        filled += 1
        if filled == 8:
            out.append(cur & 0xFF)
            cur = 0
            filled = 0
    bit_buf[0] = (cur, filled)


def generate_bits_to_bytes(seed: float, num_bits: int) -> bytes:
    """Generate num_bits from an independent RRann seed chain; return packed bytes."""
    if num_bits <= 0:
        return b""

    out = bytearray()
    bit_buf = [(0, 0)]  # (partial_byte, bits_in_partial)
    current = float(seed)
    bits_left = num_bits

    while bits_left > 0:
        value = generate(current)
        if not math.isfinite(value):
            value = 0.0

        word = int(value * (2**32)) & 0xFFFFFFFF
        take = min(32, bits_left)
        # Take the top `take` bits of the 32-bit word (MSB-first)
        if take < 32:
            word >>= 32 - take
        _pack_msb_first(word, take, out, bit_buf)
        bits_left -= take

        current = value * 10.0 if value != 0.0 else 1.6180339887498948

    cur, filled = bit_buf[0]
    if filled:
        out.append((cur << (8 - filled)) & 0xFF)

    return bytes(out)


def stream_seed(index: int, base_seed: float) -> float:
    """Derive a distinct positive float seed for stream index."""
    # Spread seeds across a wide positive range; avoid integers-only clustering.
    return abs(base_seed) + index * math.pi * 1_000_003.0 + (index % 997) * 0.6180339887498949


def _worker(args: tuple) -> tuple[int, bytes]:
    index, base_seed, bits = args
    seed = stream_seed(index, base_seed)
    return index, generate_bits_to_bytes(seed, bits)


def export_independent_streams(
    path: str | Path,
    bits_per_stream: int,
    streams: int,
    base_seed: float,
    workers: int,
    progress_every: int = 10,
) -> None:
    path = Path(path)
    total_bits = bits_per_stream * streams
    expected_bytes = (total_bits + 7) // 8

    print(
        f"Exporting {streams} streams × {bits_per_stream:,} bits "
        f"= {total_bits:,} bits ({expected_bytes:,} bytes) → {path}",
        flush=True,
    )
    print(f"Workers: {workers}  base_seed={base_seed}", flush=True)

    t0 = time.perf_counter()
    # Write streams in order so STS reads contiguous n-bit blocks sequentially.
    slots: dict[int, bytes] = {}
    next_write = 0
    written_bytes = 0
    done = 0

    tasks = [(i, base_seed, bits_per_stream) for i in range(streams)]

    with open(path, "wb") as out, ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, t): t[0] for t in tasks}
        for fut in as_completed(futures):
            index, blob = fut.result()
            slots[index] = blob
            done += 1

            while next_write in slots:
                chunk = slots.pop(next_write)
                out.write(chunk)
                written_bytes += len(chunk)
                next_write += 1

            if done % progress_every == 0 or done == streams:
                elapsed = time.perf_counter() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (streams - done) / rate if rate > 0 else float("inf")
                print(
                    f"  streams {done}/{streams}  "
                    f"written={written_bytes:,} B  "
                    f"{rate:.2f} streams/s  ETA {eta/60:.1f} min",
                    flush=True,
                )

        out.flush()
        os.fsync(out.fileno())

    elapsed = time.perf_counter() - t0
    final_size = path.stat().st_size
    print(
        f"Done in {elapsed/60:.2f} min. File size {final_size:,} bytes "
        f"(expected {expected_bytes:,}).",
        flush=True,
    )
    if final_size != expected_bytes:
        raise SystemExit(
            f"ERROR: size mismatch (got {final_size}, expected {expected_bytes})"
        )


def export_chain(path: str | Path, num_bits: int, seed: float) -> None:
    """Legacy single-chain export, still streaming (constant memory)."""
    path = Path(path)
    expected_bytes = (num_bits + 7) // 8
    print(
        f"Chain export: {num_bits:,} bits ({expected_bytes:,} bytes) → {path}",
        flush=True,
    )
    t0 = time.perf_counter()
    # Generate in 1 MiB-bit chunks worth of bytes... actually generate fixed bit chunks
    chunk_bits = 1_000_000
    written = 0
    current_seed = float(seed)

    with open(path, "wb") as out:
        remaining = num_bits
        while remaining > 0:
            take = min(chunk_bits, remaining)
            # Resume chain: need generate_bits that returns new seed
            blob, current_seed = _chain_chunk(current_seed, take)
            out.write(blob)
            remaining -= take
            written += len(blob)
            elapsed = time.perf_counter() - t0
            done_bits = num_bits - remaining
            rate = done_bits / elapsed if elapsed else 0
            eta = remaining / rate if rate else float("inf")
            print(
                f"  {done_bits:,}/{num_bits:,} bits  "
                f"{rate/1e6:.2f} Mbit/s  ETA {eta/60:.1f} min",
                flush=True,
            )
        out.flush()
        os.fsync(out.fileno())

    print(f"Done. {path.stat().st_size:,} bytes in {(time.perf_counter()-t0)/60:.2f} min")


def _chain_chunk(seed: float, num_bits: int) -> tuple[bytes, float]:
    out = bytearray()
    bit_buf = [(0, 0)]
    current = float(seed)
    bits_left = num_bits
    while bits_left > 0:
        value = generate(current)
        if not math.isfinite(value):
            value = 0.0
        word = int(value * (2**32)) & 0xFFFFFFFF
        take = min(32, bits_left)
        shifted = word >> (32 - take) if take < 32 else word
        _pack_msb_first(shifted, take, out, bit_buf)
        bits_left -= take
        current = value * 10.0 if value != 0.0 else 1.6180339887498948
    cur, filled = bit_buf[0]
    if filled:
        out.append((cur << (8 - filled)) & 0xFF)
    return bytes(out), current


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export RRann bits for NIST STS (streaming).")
    p.add_argument("-o", "--output", required=True, help="Output file path")
    p.add_argument(
        "--mode",
        choices=("streams", "chain"),
        default="streams",
        help="streams=independent parallel bitstreams (default); chain=single seed chain",
    )
    p.add_argument(
        "--bits-per-stream",
        type=int,
        default=1_000_000,
        help="Bits per STS bitstream (default 1000000)",
    )
    p.add_argument(
        "--streams",
        type=int,
        default=1000,
        help="Number of independent bitstreams (default 1000)",
    )
    p.add_argument(
        "--bits",
        type=int,
        default=None,
        help="Total bits for chain mode (or override total = bits-per-stream * streams)",
    )
    p.add_argument("--seed", type=float, default=2.4, help="Base seed (default 2.4)")
    p.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 2) - 1),
        help="Parallel workers for streams mode",
    )
    p.add_argument(
        "--format",
        choices=("binary",),
        default="binary",
        help="Only binary is supported (ASCII would waste 8× disk)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "chain":
        nbits = args.bits if args.bits is not None else args.bits_per_stream * args.streams
        export_chain(args.output, nbits, args.seed)
    else:
        if args.bits is not None:
            # Allow --bits as total; derive streams if divisible
            if args.bits % args.bits_per_stream != 0:
                raise SystemExit(
                    f"--bits ({args.bits}) must be divisible by "
                    f"--bits-per-stream ({args.bits_per_stream})"
                )
            streams = args.bits // args.bits_per_stream
        else:
            streams = args.streams
        export_independent_streams(
            args.output,
            args.bits_per_stream,
            streams,
            args.seed,
            max(1, args.workers),
        )


if __name__ == "__main__":
    main()
