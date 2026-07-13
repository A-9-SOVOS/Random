"""Health diagnostics on remainder-derived bits (monobit + runs-style)."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence

from .core import normalize_seed
from .extract import DEFAULT_CULL_HEAD, extract_bits, resolve_cull_head, stream_seed

HealthStatus = Literal["pass", "warn", "fail"]
HealthProfile = Literal["cosmetic", "gameplay", "economy"]


@dataclass(frozen=True)
class HealthResult:
    """Outcome of :func:`health_check`."""

    status: HealthStatus
    profile: HealthProfile
    ok: bool
    n_bits: int
    p1: float
    monobit_z: float
    monobit_ok: bool
    runs_z: float
    mean_run_length: float
    runs_ok: bool
    messages: tuple = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["messages"] = list(self.messages)
        return d


def _run_lengths(bits: Sequence[int]) -> List[int]:
    if not bits:
        return []
    lengths: List[int] = []
    cur = bits[0] & 1
    length = 1
    for b in bits[1:]:
        b = b & 1
        if b == cur:
            length += 1
        else:
            lengths.append(length)
            cur = b
            length = 1
    lengths.append(length)
    return lengths


def _monobit_z(bits: Sequence[int]) -> tuple[float, float]:
    n = len(bits)
    if n == 0:
        return 0.0, 0.5
    ones = sum(b & 1 for b in bits)
    p1 = ones / n
    # z under H0 p=0.5
    z = (ones - n / 2.0) / math.sqrt(n / 4.0)
    return z, p1


def _runs_z(bits: Sequence[int]) -> tuple[float, float, int]:
    n = len(bits)
    lengths = _run_lengths(bits)
    nruns = len(lengths)
    mean_run = (sum(lengths) / nruns) if nruns else 0.0
    if n < 2:
        return 0.0, mean_run, nruns
    n0 = sum(1 for b in bits if (b & 1) == 0)
    n1 = n - n0
    if n0 == 0 or n1 == 0:
        return float("inf"), mean_run, nruns
    er = 2.0 * n0 * n1 / n + 1.0
    vr = (2.0 * n0 * n1 * (2.0 * n0 * n1 - n)) / (n * n * (n - 1))
    if vr <= 0:
        return 0.0, mean_run, nruns
    z = (nruns - er) / math.sqrt(vr)
    return z, mean_run, nruns


def diagnose_bits(
    bits: Sequence[int],
    *,
    profile: HealthProfile = "gameplay",
) -> HealthResult:
    """
    Run monobit + classical runs diagnostics on an existing bit sequence.

    Profiles
    --------
    cosmetic:
        Loose thresholds; borderline stats → ``warn``, rarely ``fail``.
    gameplay:
        Default bands for sims / proc-gen.
    economy:
        Stricter bands; borderline → ``fail`` (fail-closed).
    """
    if profile not in ("cosmetic", "gameplay", "economy"):
        raise ValueError("profile must be cosmetic, gameplay, or economy")

    n = len(bits)
    messages: List[str] = []
    if n < 256:
        messages.append(f"short sample ({n} bits); results noisy")

    monobit_z, p1 = _monobit_z(bits)
    runs_z, mean_run, _nruns = _runs_z(bits)

    # Thresholds: |z| above warn / fail
    if profile == "cosmetic":
        mono_warn, mono_fail = 3.0, 5.0
        runs_warn, runs_fail = 3.0, 5.0
        runlen_lo, runlen_hi = 1.7, 2.4
    elif profile == "economy":
        mono_warn, mono_fail = 2.0, 2.8
        runs_warn, runs_fail = 2.0, 2.8
        runlen_lo, runlen_hi = 1.85, 2.15
    else:  # gameplay
        mono_warn, mono_fail = 2.5, 3.5
        runs_warn, runs_fail = 2.5, 3.5
        runlen_lo, runlen_hi = 1.8, 2.25

    monobit_ok = abs(monobit_z) < mono_fail
    runs_ok = abs(runs_z) < runs_fail and runlen_lo <= mean_run <= runlen_hi

    if abs(monobit_z) >= mono_fail:
        messages.append(f"monobit |z|={monobit_z:.2f} exceeds fail band")
    elif abs(monobit_z) >= mono_warn:
        messages.append(f"monobit |z|={monobit_z:.2f} in warn band")

    if abs(runs_z) >= runs_fail:
        messages.append(f"runs |z|={runs_z:.2f} exceeds fail band")
    elif abs(runs_z) >= runs_warn:
        messages.append(f"runs |z|={runs_z:.2f} in warn band")

    if not (runlen_lo <= mean_run <= runlen_hi):
        messages.append(
            f"mean run length {mean_run:.3f} outside [{runlen_lo}, {runlen_hi}]"
        )

    # Aggregate status
    hard_fail = (not monobit_ok) or (not runs_ok)
    soft_warn = any("warn band" in m or "outside" in m for m in messages) or (
        abs(monobit_z) >= mono_warn or abs(runs_z) >= runs_warn
    )

    if hard_fail:
        status: HealthStatus = "fail"
    elif soft_warn:
        # economy: treat warn as fail (fail-closed)
        status = "fail" if profile == "economy" else "warn"
    else:
        status = "pass"

    if profile == "cosmetic" and status == "fail" and n < 512:
        # very short samples: demote hard fail to warn for cosmetics only
        status = "warn"
        messages.append("cosmetic profile: short-sample fail demoted to warn")

    ok = status == "pass" or (profile == "cosmetic" and status == "warn")

    return HealthResult(
        status=status,
        profile=profile,
        ok=ok,
        n_bits=n,
        p1=p1,
        monobit_z=monobit_z,
        monobit_ok=monobit_ok,
        runs_z=runs_z,
        mean_run_length=mean_run,
        runs_ok=runs_ok,
        messages=tuple(messages),
    )


def health_check(
    seed: float = 2.4,
    *,
    n_bits: int = 8192,
    profile: HealthProfile = "gameplay",
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
) -> HealthResult:
    """
    Generate remainder-derived bits from *seed* and run health diagnostics.

    Uses the default cull-head extract path (not legacy sin-mix).
    """
    cull = resolve_cull_head(cull_head, drop, DEFAULT_CULL_HEAD)
    seed = normalize_seed(seed)
    bits: List[int] = []
    # Independent substreams so health is not one long feedback chain artifact only
    stream = 0
    while len(bits) < n_bits:
        s = stream_seed(seed, stream)
        # walk a short chain within stream for volume
        cur = s
        for _ in range(32):
            if len(bits) >= n_bits:
                break
            chunk = extract_bits(cur, min(64, n_bits - len(bits)), cull_head=cull)
            bits.extend(chunk)
            from .extract import extract_float

            v = extract_float(cur, cull_head=cull)
            cur = v * 10.0 if v != 0.0 else 1.6180339887498948
        stream += 1
        if stream > n_bits:  # safety
            break

    return diagnose_bits(bits[:n_bits], profile=profile)


class ContinuousHealth:
    """
    Rolling-window health monitor for live generators (economy profile friendly).

    Feed bits as they are produced; call :meth:`check` periodically.
    """

    def __init__(
        self,
        *,
        window_bits: int = 8192,
        profile: HealthProfile = "economy",
    ):
        if window_bits < 256:
            raise ValueError("window_bits must be >= 256")
        self.window_bits = window_bits
        self.profile = profile
        self._bits: List[int] = []
        self._total_ingested = 0
        self.last_result: Optional[HealthResult] = None

    def ingest(self, bits: Sequence[int]) -> None:
        """Append bits (0/1) into the rolling window."""
        for b in bits:
            self._bits.append(b & 1)
            self._total_ingested += 1
        overflow = len(self._bits) - self.window_bits
        if overflow > 0:
            del self._bits[:overflow]

    def ingest_int(self, value: int, nbits: int) -> None:
        """Ingest the low *nbits* of *value* (MSB-first within that width)."""
        if nbits <= 0:
            return
        bits = [(value >> (nbits - 1 - i)) & 1 for i in range(nbits)]
        self.ingest(bits)

    def ready(self) -> bool:
        return len(self._bits) >= min(256, self.window_bits)

    def check(self) -> HealthResult:
        """Diagnose the current window; stores result on ``last_result``."""
        if not self._bits:
            result = HealthResult(
                status="warn",
                profile=self.profile,
                ok=self.profile == "cosmetic",
                n_bits=0,
                p1=0.5,
                monobit_z=0.0,
                monobit_ok=True,
                runs_z=0.0,
                mean_run_length=2.0,
                runs_ok=True,
                messages=("no bits ingested yet",),
            )
        else:
            result = diagnose_bits(self._bits, profile=self.profile)
        self.last_result = result
        return result

    @property
    def total_ingested(self) -> int:
        return self._total_ingested

