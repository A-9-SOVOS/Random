"""Stateful generator API (sequences, randbits, floats, fork)."""

from __future__ import annotations

from typing import Iterator, List, Optional, Union

from .core import harvest, normalize_seed
from .extract import (
    DEFAULT_CULL_HEAD,
    extract_bits,
    extract_float,
    resolve_cull_head,
    stream_seed,
)
from .fairness import ALGO_VERSION


class Generator:
    """
    Stateful residual-harvest generator (game/sim default path).

    Pipeline: ``seed → residual digits → cull head → float/bits``.

    Parameters
    ----------
    seed:
        Initial seed (positive float).
    cull_head:
        Leading residual digits to discard (default 2). Alias: *drop*.
    mode:
        ``"remainder"`` — cleaned residual (default).
        ``"legacy"`` — original float + sin mix (opt-in only).
    whitening:
        Optional bit whitening for :meth:`randbits`.
    """

    algo_version = ALGO_VERSION

    def __init__(
        self,
        seed: float = 2.4,
        *,
        cull_head: Optional[int] = None,
        drop: Optional[int] = None,
        mode: str = "remainder",
        whitening: Optional[str] = None,
    ):
        if mode not in ("remainder", "legacy"):
            raise ValueError("mode must be 'remainder' or 'legacy'")
        if whitening not in (None, "von_neumann", "xor"):
            raise ValueError("whitening must be None, 'von_neumann', or 'xor'")
        self._seed0 = normalize_seed(seed)
        self._state = self._seed0
        self.cull_head = resolve_cull_head(cull_head, drop, DEFAULT_CULL_HEAD)
        self.drop = self.cull_head  # compat
        self.mode = mode
        self.whitening = whitening
        self._counter = 0

    @property
    def state(self) -> float:
        return self._state

    def seed(self, value: float) -> None:
        self._seed0 = normalize_seed(value)
        self._state = self._seed0
        self._counter = 0

    def _legacy_float(self, s: float) -> float:
        from .legacy import generate as legacy_generate

        return legacy_generate(s)

    def random(self) -> float:
        """Next float in ``[0, 1)``; advances state."""
        if self.mode == "legacy":
            value = self._legacy_float(self._state)
        else:
            value = extract_float(self._state, cull_head=self.cull_head)

        self._state = value * 10.0 if value != 0.0 else 1.6180339887498948
        self._counter += 1
        return value

    def next_f64(self) -> float:
        """Alias of :meth:`random`."""
        return self.random()

    def randbits(self, k: int) -> int:
        """Next *k* bits as an ``int`` (MSB-first)."""
        if k <= 0:
            return 0
        bits = extract_bits(
            self._state,
            k if self.whitening != "von_neumann" else max(k * 5, k + 32),
            cull_head=self.cull_head,
            whitening=self.whitening,
        )
        if self.whitening == "von_neumann" and len(bits) < k:
            while len(bits) < k:
                self._state = (
                    extract_float(self._state, cull_head=self.cull_head) * 10.0
                    or 1.6180339887498948
                )
                extra = extract_bits(
                    self._state,
                    max(64, (k - len(bits)) * 5),
                    cull_head=self.cull_head,
                    whitening="von_neumann",
                )
                bits.extend(extra)
            bits = bits[:k]

        step = extract_float(self._state, cull_head=self.cull_head)
        self._state = step * 10.0 if step != 0.0 else 1.6180339887498948
        self._counter += 1

        value = 0
        for b in bits[:k]:
            value = (value << 1) | (b & 1)
        return value

    def next_u64(self) -> int:
        """Next 64-bit unsigned value."""
        return self.randbits(64)

    def randbytes(self, n: int) -> bytes:
        if n <= 0:
            return b""
        return self.randbits(n * 8).to_bytes(n, "big")

    def getrandbits(self, k: int) -> int:
        return self.randbits(k)

    def random_sample(self, n: int) -> List[float]:
        return [self.random() for _ in range(n)]

    def iter_floats(self) -> Iterator[float]:
        while True:
            yield self.random()

    def fork(self, stream_id: Union[int, str, bytes]) -> "Generator":
        """
        Independent child generator: ``mix(master_seed, stream_id)``.

        Does not share mutable state with the parent — safe for parallel
        workers (one fork per worker / chunk / region).
        """
        child_seed = stream_seed(self._seed0, stream_id)
        return Generator(
            child_seed,
            cull_head=self.cull_head,
            mode=self.mode,
            whitening=self.whitening,
        )

    def harvest_once(self):
        """Return a :class:`~rrann.core.HarvestResult` without advancing."""
        return harvest(self._state)

    def __repr__(self) -> str:
        return (
            f"Generator(seed={self._seed0!r}, cull_head={self.cull_head}, "
            f"mode={self.mode!r}, whitening={self.whitening!r}, "
            f"calls={self._counter})"
        )


# Designer-facing alias
Rng = Generator
