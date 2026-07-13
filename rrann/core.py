"""Dual-precision residual harvest (error harvester core)."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from decimal import Decimal, getcontext, localcontext
from typing import Optional

getcontext().prec = 120

# Digits harvested past the float/Decimal divergence point.
DEFAULT_DIGIT_COUNT = 12


def normalize_seed(seed) -> float:
    """Coerce *seed* to a positive finite float suitable for ``x**x``."""
    try:
        seed_value = float(seed)
    except (TypeError, ValueError):
        return 0.123456789

    if math.isnan(seed_value) or math.isinf(seed_value) or seed_value <= 0.0:
        seed_value = abs(seed_value) if math.isfinite(seed_value) else 0.123456789
        if seed_value <= 0.0:
            seed_value = 0.123456789

    return seed_value


def _decimal_digits(value: Decimal, count: int = 200) -> str:
    if value.is_nan() or value.is_infinite():
        return "0" * count

    value = value.normalize()
    _sign, digits, exponent = value.as_tuple()
    digits_str = "".join(str(d) for d in digits) or "0"

    if exponent >= 0:
        combined = digits_str + "0" * exponent
    else:
        idx = len(digits_str) + exponent
        if idx > 0:
            combined = digits_str
        else:
            combined = "0" * (-idx) + digits_str

    if len(combined) < count:
        combined = combined.ljust(count, "0")

    return combined[:count]


def _fallback_digits(seed_value: float, count: int) -> str:
    digest = hashlib.sha256(f"{seed_value:.18g}".encode("utf-8")).hexdigest()
    fallback_int = int(digest, 16)
    return str(fallback_int).ljust(count, "0")[:count]


@dataclass(frozen=True)
class HarvestResult:
    """One residual harvest from a seed."""

    seed: float
    digits: str
    divergence_index: Optional[int]
    used_fallback: bool
    float_power: Optional[float]

    @property
    def head(self) -> str:
        """Leading residual digits (structurally hot for runs tests)."""
        return self.digits[:2]

    def remainder(self, cull_head: int = 2, drop: int | None = None) -> str:
        """Digits after culling the residual head (default 2 leading digits)."""
        n = drop if drop is not None else cull_head
        if n <= 0:
            return self.digits
        if n >= len(self.digits):
            return ""
        return self.digits[n:]


def harvest(seed, count: int = DEFAULT_DIGIT_COUNT) -> HarvestResult:
    """
    Compute ``seed**seed`` in IEEE float and high-precision Decimal; return
    *count* digits of the Decimal result starting at the first disagreement.

    If the paths never diverge (or the power overflows), falls back to a
    SHA-256-derived digit string so the API stays total.
    """
    seed_value = normalize_seed(seed)
    used_fallback = False
    divergence_index: Optional[int] = None
    float_power: Optional[float] = None

    try:
        float_result = seed_value**seed_value
    except OverflowError:
        float_result = float("inf")

    float_power = float_result if math.isfinite(float_result) else None

    if not math.isfinite(float_result):
        digits = _fallback_digits(seed_value, count)
        used_fallback = True
    else:
        d_seed = Decimal.from_float(seed_value)
        with localcontext() as ctx:
            ctx.prec = 160
            try:
                d_result = d_seed**d_seed
            except Exception:
                digits = _fallback_digits(seed_value, count)
                used_fallback = True
                return HarvestResult(
                    seed=seed_value,
                    digits=digits,
                    divergence_index=None,
                    used_fallback=True,
                    float_power=float_power,
                )

        float_digits = _decimal_digits(Decimal.from_float(float_result), count=count + 32)
        high_digits = _decimal_digits(d_result, count=count + 32)

        for i in range(min(len(float_digits), len(high_digits))):
            if float_digits[i] != high_digits[i]:
                divergence_index = i
                break

        if divergence_index is None:
            digits = _fallback_digits(seed_value, count)
            used_fallback = True
        else:
            error_digits = high_digits[divergence_index : divergence_index + count]
            if (
                not error_digits
                or len(error_digits) < count
                or all(ch == "0" for ch in error_digits)
            ):
                digits = _fallback_digits(seed_value, count)
                used_fallback = True
            else:
                digits = error_digits

    return HarvestResult(
        seed=seed_value,
        digits=digits,
        divergence_index=divergence_index,
        used_fallback=used_fallback,
        float_power=float_power,
    )
