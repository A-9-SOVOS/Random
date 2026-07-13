"""Seed commit and roll receipts for transparent game economies."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional, Union

from .core import normalize_seed
from .extract import (
    DEFAULT_CULL_HEAD,
    extract_bits,
    extract_float,
    resolve_cull_head,
)

# Bump when extract semantics that affect roll results change.
ALGO_VERSION = "rrann-remainder-cull2-v1"
_PKG_VERSION = "0.2.0"

Context = Union[str, bytes, int, float]


def _context_bytes(context: Context) -> bytes:
    if isinstance(context, bytes):
        return context
    if isinstance(context, bytearray):
        return bytes(context)
    if isinstance(context, str):
        return context.encode("utf-8")
    if isinstance(context, bool):
        return b"true" if context else b"false"
    if isinstance(context, int):
        return str(context).encode("ascii")
    if isinstance(context, float):
        return repr(float(context)).encode("ascii")
    return str(context).encode("utf-8")


def commit_seed(
    seed: float,
    *,
    game_id: str = "",
    season: str = "",
    extra: bytes = b"",
) -> str:
    """
    Hash seed material for commit–reveal (anti re-roll transparency).

    Returns a hex SHA-256 digest. Publish *commit* before the roll; reveal
    *seed* (and game_id/season) afterward so players can recompute.
    """
    seed = normalize_seed(seed)
    payload = (
        b"rrann-commit-v1\0"
        + repr(seed).encode("ascii")
        + b"\0"
        + game_id.encode("utf-8")
        + b"\0"
        + season.encode("utf-8")
        + b"\0"
        + extra
    )
    return hashlib.sha256(payload).hexdigest()


def verify_commit(
    commit: str,
    seed: float,
    *,
    game_id: str = "",
    season: str = "",
    extra: bytes = b"",
) -> bool:
    """Return True if *commit* matches :func:`commit_seed` inputs."""
    expected = commit_seed(seed, game_id=game_id, season=season, extra=extra)
    # constant-time compare
    try:
        return hmac.compare_digest(expected, commit.strip().lower())
    except (TypeError, ValueError):
        return False


def roll_seed(master: float, context: Context, n: int = 0) -> float:
    """
    Deterministic sub-seed for ``(master, context, n)``.

    Same triple always maps to the same float seed (independent of call order).
    """
    master = normalize_seed(master)
    raw = (
        b"rrann-roll-v1\0"
        + repr(master).encode("ascii")
        + b"\0"
        + _context_bytes(context)
        + b"\0"
        + str(int(n)).encode("ascii")
    )
    digest = hashlib.sha256(raw).digest()
    # Map 64 bits into (0.5, 10)
    u = int.from_bytes(digest[:8], "big") / 2**64
    return 0.5 + u * 9.5


def roll(
    seed: float,
    context: Context,
    n: int = 0,
    *,
    kind: str = "float",
    bits: int = 32,
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
) -> Union[float, int]:
    """
    Deterministic roll: same ``(seed, context, n, kind, bits, cull)`` → same result.

    Parameters
    ----------
    kind:
        ``"float"`` → value in [0, 1); ``"int"`` → unsigned *bits*-bit integer.
    n:
        Counter / draw index within *context* (loot slot, spin number, …).
    """
    cull = resolve_cull_head(cull_head, drop)
    s = roll_seed(seed, context, n)
    if kind == "float":
        return extract_float(s, cull_head=cull)
    if kind == "int":
        if bits <= 0:
            return 0
        bit_list = extract_bits(s, bits, cull_head=cull)
        value = 0
        for b in bit_list:
            value = (value << 1) | (b & 1)
        return value
    raise ValueError("kind must be 'float' or 'int'")


@dataclass(frozen=True)
class RollReceipt:
    """Auditable record of a single roll."""

    commit: str
    context: str
    n: int
    result: Union[float, int]
    kind: str
    bits: int
    algo_version: str
    cull_head: int
    package_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RollReceipt":
        return cls(
            commit=str(d["commit"]),
            context=str(d["context"]),
            n=int(d["n"]),
            result=d["result"],
            kind=str(d.get("kind", "float")),
            bits=int(d.get("bits", 32)),
            algo_version=str(d.get("algo_version", ALGO_VERSION)),
            cull_head=int(d.get("cull_head", DEFAULT_CULL_HEAD)),
            package_version=str(d.get("package_version", _PKG_VERSION)),
        )


def create_receipt(
    seed: float,
    context: Context,
    n: int = 0,
    *,
    kind: str = "float",
    bits: int = 32,
    game_id: str = "",
    season: str = "",
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
) -> RollReceipt:
    """Create a roll result and bind it to a seed commit."""
    cull = resolve_cull_head(cull_head, drop)
    commit = commit_seed(seed, game_id=game_id, season=season)
    result = roll(
        seed, context, n, kind=kind, bits=bits, cull_head=cull
    )
    ctx_str = (
        context.decode("utf-8", errors="replace")
        if isinstance(context, (bytes, bytearray))
        else str(context)
    )
    return RollReceipt(
        commit=commit,
        context=ctx_str,
        n=int(n),
        result=result,
        kind=kind,
        bits=bits,
        algo_version=ALGO_VERSION,
        cull_head=cull,
        package_version=_PKG_VERSION,
    )


def verify_receipt(
    receipt: Union[RollReceipt, Mapping[str, Any]],
    seed: float,
    *,
    game_id: str = "",
    season: str = "",
) -> bool:
    """
    Recompute roll from *seed* and check commit + result match *receipt*.

    Returns True only if commit verifies and result is identical (floats via
    equality of recomputed extract; ints exact).
    """
    if not isinstance(receipt, RollReceipt):
        receipt = RollReceipt.from_dict(receipt)

    if not verify_commit(
        receipt.commit, seed, game_id=game_id, season=season
    ):
        return False

    if receipt.algo_version != ALGO_VERSION:
        # Still try recompute with current algo; mismatch is a fail for strict verify
        return False

    expected = roll(
        seed,
        receipt.context,
        receipt.n,
        kind=receipt.kind,
        bits=receipt.bits,
        cull_head=receipt.cull_head,
    )
    if receipt.kind == "float":
        return isinstance(expected, float) and expected == float(receipt.result)
    return int(expected) == int(receipt.result)
