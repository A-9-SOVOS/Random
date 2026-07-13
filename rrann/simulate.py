"""Loot-table Monte Carlo and rate helpers (design transparency, not crypto)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .fairness import roll
from .extract import resolve_cull_head

# Cumulative table: list of (name, cumulative_upper_bound in (0,1])
LootTable = Sequence[Tuple[str, float]]
WeightTable = Sequence[Tuple[str, float]]  # name, relative weight


def normalize_weights(weights: WeightTable) -> LootTable:
    """Convert relative weights to a cumulative [0,1) table."""
    total = sum(max(0.0, float(w)) for _, w in weights)
    if total <= 0:
        raise ValueError("weights must sum to a positive total")
    cum = 0.0
    out: List[Tuple[str, float]] = []
    for name, w in weights:
        cum += max(0.0, float(w)) / total
        out.append((str(name), min(1.0, cum)))
    # force last to 1.0
    if out:
        last_name, _ = out[-1]
        out[-1] = (last_name, 1.0)
    return out


def pick_from_table(u: float, table: LootTable) -> str:
    """Pick row for uniform *u* in [0, 1) given cumulative upper bounds."""
    if not 0.0 <= u < 1.0:
        # allow 1.0 edge from float noise
        u = min(max(u, 0.0), 0.9999999999999999)
    for name, hi in table:
        if u < hi:
            return name
    return table[-1][0]


@dataclass(frozen=True)
class RateReport:
    trials: int
    counts: Dict[str, int]
    rates: Dict[str, float]
    expected_rates: Dict[str, float]
    abs_errors: Dict[str, float]
    max_abs_error: float

    def to_dict(self) -> dict:
        return {
            "trials": self.trials,
            "counts": dict(self.counts),
            "rates": dict(self.rates),
            "expected_rates": dict(self.expected_rates),
            "abs_errors": dict(self.abs_errors),
            "max_abs_error": self.max_abs_error,
        }


def expected_rates_from_cumulative(table: LootTable) -> Dict[str, float]:
    """Infer theoretical rates from cumulative bounds (adjacent differences)."""
    rates: Dict[str, float] = {}
    prev = 0.0
    for name, hi in table:
        rates[name] = float(hi) - prev
        prev = float(hi)
    return rates


def simulate_loot(
    seed: float,
    table: Union[LootTable, WeightTable],
    *,
    trials: int = 10_000,
    context: str = "loot.sim",
    cumulative: bool = True,
    cull_head: Optional[int] = None,
    drop: Optional[int] = None,
) -> RateReport:
    """
    Monte Carlo loot draws via :func:`rrann.fairness.roll`.

    If *cumulative* is False, *table* is treated as relative weights.
    """
    if trials <= 0:
        raise ValueError("trials must be positive")
    cull = resolve_cull_head(cull_head, drop)
    if cumulative:
        cum_table = list(table)  # type: ignore[arg-type]
    else:
        cum_table = normalize_weights(table)  # type: ignore[arg-type]

    expected = expected_rates_from_cumulative(cum_table)
    counts: Dict[str, int] = {name: 0 for name, _ in cum_table}

    for n in range(trials):
        u = float(roll(seed, context, n, kind="float", cull_head=cull))
        name = pick_from_table(u, cum_table)
        counts[name] = counts.get(name, 0) + 1

    rates = {k: v / trials for k, v in counts.items()}
    abs_errors = {
        k: abs(rates.get(k, 0.0) - expected.get(k, 0.0)) for k in expected
    }
    max_err = max(abs_errors.values()) if abs_errors else 0.0
    return RateReport(
        trials=trials,
        counts=counts,
        rates=rates,
        expected_rates=expected,
        abs_errors=abs_errors,
        max_abs_error=max_err,
    )


def expected_value(
    rates: Mapping[str, float],
    values: Mapping[str, float],
) -> float:
    """EV = sum rate_i * value_i (missing keys treated as 0)."""
    return sum(float(rates.get(k, 0.0)) * float(v) for k, v in values.items())


def pity_effective_rate(
    base_rate: float,
    *,
    pity_at: int,
    soft_start: Optional[int] = None,
    soft_step: float = 0.0,
) -> float:
    """
    Rough long-run rate under hard pity at *pity_at* pulls.

    Soft pity (optional): from *soft_start*, add *soft_step* each pull until hard pity.
    This is a design aid, not a closed-form guarantee for every schedule.
    """
    if not 0.0 < base_rate < 1.0:
        raise ValueError("base_rate must be in (0,1)")
    if pity_at < 1:
        raise ValueError("pity_at must be >= 1")
    # Simulate one long session of geometric-with-pity using theoretical p only
    # (independent of RRann — documents the *table design*, not the RNG).
    # Effective rate ≈ 1 / E[draws to success] with p_n schedule.
    import random

    rng = random.Random(0)
    trials = 50_000
    total_pulls = 0
    successes = 0
    for _ in range(trials):
        pulls = 0
        while True:
            pulls += 1
            p = base_rate
            if soft_start is not None and pulls >= soft_start:
                p = min(1.0, base_rate + soft_step * (pulls - soft_start + 1))
            if pulls >= pity_at:
                p = 1.0
            if rng.random() < p:
                total_pulls += pulls
                successes += 1
                break
    return successes / total_pulls if total_pulls else 0.0
