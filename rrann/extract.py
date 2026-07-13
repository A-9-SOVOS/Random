"""Bit/float extraction from residual harvest digits."""

from __future__ import annotations

import math
import os
import struct
from typing import Iterable, List, Optional

from .core import DEFAULT_DIGIT_COUNT, harvest, normalize_seed

# First residual digits after the diverge cut carry run-structure bias.
# Default cull drops that head; remainder is the game/sim signal.
DEFAULT_CULL_HEAD = 2
DEFAULT_DROP = DEFAULT_CULL_HEAD  # compat alias


def resolve_cull_head(
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
    default: int = DEFAULT_CULL_HEAD,
) -> int:
    """Resolve *cull_head* / legacy *drop* to a single non-negative int."""
    if cull_head is not None and drop is not None and cull_head != drop:
        raise ValueError("cull_head and drop disagree; pass only one")
    if cull_head is not None:
        n = cull_head
    elif drop is not None:
        n = drop
    else:
        n = default
    if n < 0:
        raise ValueError("cull_head must be >= 0")
    return int(n)


def bits_from_digits(digits: str, nbits: int) -> List[int]:
    """
    Map a decimal digit string ``d0 d1 …`` to *nbits* MSB-first bits via

        floor( int(digits) / 10**len(digits) * 2**nbits )
    """
    if nbits <= 0:
        return []
    if not digits:
        return [0] * nbits

    num = int(digits)
    den = 10 ** len(digits)
    word = (num << nbits) // den
    return [(word >> (nbits - 1 - i)) & 1 for i in range(nbits)]


def pack_bits(bits: Iterable[int]) -> bytes:
    """Pack MSB-first bits into bytes (last byte zero-padded)."""
    bit_list = [b & 1 for b in bits]
    out = bytearray()
    acc = 0
    n = 0
    for b in bit_list:
        acc = (acc << 1) | b
        n += 1
        if n == 8:
            out.append(acc)
            acc = 0
            n = 0
    if n:
        out.append(acc << (8 - n))
    return bytes(out)


def von_neumann(bits: Iterable[int]) -> List[int]:
    """Classic von Neumann debias: 01→0, 10→1, discard 00/11."""
    bit_list = list(bits)
    out: List[int] = []
    for i in range(0, len(bit_list) - 1, 2):
        a, b = bit_list[i] & 1, bit_list[i + 1] & 1
        if a != b:
            out.append(a)
    return out


def xor_adjacent(bits: Iterable[int]) -> List[int]:
    """Whitening: out[i] = bits[i] XOR bits[i+1]."""
    bit_list = list(bits)
    return [(bit_list[i] ^ bit_list[i + 1]) & 1 for i in range(len(bit_list) - 1)]


def extract_bits(
    seed,
    nbits: int,
    *,
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
    digit_count: int = DEFAULT_DIGIT_COUNT,
    whitening: Optional[str] = None,
) -> List[int]:
    """
    Harvest residual digits from *seed*, cull the leading residual head,
    and emit *nbits* MSB-first bits.

    Pipeline (default)::

        seed → residual digits → cull head → bits

    Parameters
    ----------
    cull_head:
        Number of leading residual digits to discard (default
        :data:`DEFAULT_CULL_HEAD` = 2). First digits after the float/Decimal
        diverge cut empirically fail run-length geometry; the remainder is
        the intended signal.
    drop:
        Deprecated alias for *cull_head* (same meaning).
    whitening:
        ``None`` | ``"xor"`` | ``"von_neumann"`` after bit packing.
    """
    cull = resolve_cull_head(cull_head, drop)
    result = harvest(seed, count=digit_count)
    body = result.remainder(cull)
    if not body:
        body = result.digits

    need = nbits
    if whitening == "von_neumann":
        need = max(nbits * 5, nbits + 64)
    elif whitening == "xor":
        need = nbits + 1

    bits = bits_from_digits(body, need)

    if whitening == "xor":
        bits = xor_adjacent(bits)[:nbits]
    elif whitening == "von_neumann":
        bits = von_neumann(bits)[:nbits]
    else:
        bits = bits[:nbits]

    return bits


def extract_float(
    seed,
    *,
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
    digit_count: int = DEFAULT_DIGIT_COUNT,
) -> float:
    """
    Float in ``[0, 1)`` from culled residual digits only (no sin mix).

    Preferred over legacy :func:`rrann.generate` for the cleaned signal path.
    """
    cull = resolve_cull_head(cull_head, drop)
    result = harvest(seed, count=digit_count)
    body = result.remainder(cull) or result.digits
    body = (body + "0" * 16)[:16]
    return min(max(float("0." + body), 0.0), 0.9999999999999999)


def _seed_mix(seed: float, counter: int) -> float:
    """Deterministic child seed from parent + counter (independent streams)."""
    x = normalize_seed(seed) + (counter + 1) * math.pi * 1_000_003.0
    x = abs(math.sin(x * 12.9898) * 43758.5453) % 1.0
    return 0.5 + x * 9.5


def stream_seed(master: float, stream_id) -> float:
    """
    Derive an independent stream seed from *master* and *stream_id*.

    Same master+stream_id always yields the same float seed. Parallel workers
    should each use a distinct *stream_id* rather than sharing one chain.
    """
    master = normalize_seed(master)
    if isinstance(stream_id, (bytes, bytearray)):
        tag = int.from_bytes(bytes(stream_id)[:8].ljust(8, b"\0"), "big")
    elif isinstance(stream_id, str):
        tag = sum((i + 1) * ord(c) for i, c in enumerate(stream_id[:64]))
        tag ^= len(stream_id) * 0x9E3779B9
    else:
        tag = int(stream_id) & 0xFFFFFFFFFFFFFFFF
    # Mix into (0.5, 10) band for stable x**x
    x = master + (tag % 1_000_003) * math.pi + ((tag >> 20) % 997) * 0.6180339887498949
    x = abs(math.sin(x * 12.9898) * 43758.5453) % 1.0
    return 0.5 + x * 9.5


def random_bits(
    nbits: int,
    *,
    seed: Optional[float] = None,
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
    whitening: Optional[str] = None,
) -> bytes:
    """
    Produce *nbits* of residual-derived bits as ``bytes``.

    If *seed* is ``None``, uses ``os.urandom`` once for the initial seed
    (OS entropy for the seed only; expansion is the residual map).
    """
    if nbits <= 0:
        return b""

    cull = resolve_cull_head(cull_head, drop)

    if seed is None:
        raw = os.urandom(8)
        seed = struct.unpack("!Q", raw)[0] / 2**64 * 9.0 + 1.0

    bits: List[int] = []
    counter = 0
    current = normalize_seed(seed)

    while len(bits) < nbits:
        chunk = extract_bits(
            current,
            min(64, nbits - len(bits) + (32 if whitening == "von_neumann" else 0)),
            cull_head=cull,
            whitening=whitening,
        )
        if not chunk and whitening == "von_neumann":
            counter += 1
            current = _seed_mix(seed, counter)
            continue
        bits.extend(chunk)
        counter += 1
        current = _seed_mix(seed, counter)

    return pack_bits(bits[:nbits])


def random_float(
    *,
    seed: Optional[float] = None,
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
) -> float:
    """One culled-remainder float in ``[0, 1)``."""
    if seed is None:
        raw = os.urandom(8)
        seed = struct.unpack("!Q", raw)[0] / 2**64 * 9.0 + 1.0
    return extract_float(seed, cull_head=cull_head, drop=drop)
