"""Original RRann float API (sin-mixed residual) for compatibility."""

from __future__ import annotations

import math

from .core import harvest, normalize_seed


def generate(seed: float, precision_digits: int = 8) -> float:
    """
    Legacy generator: residual digits → ``0.ddd…`` then
    ``(base + sin(seed * 1e6)) % 1``.

    Kept for demos and paper trails. Prefer
    :func:`rrann.extract_float` / :class:`rrann.Generator` for new code.
    """
    result = harvest(seed, count=precision_digits + 4)
    digits = result.digits[: precision_digits + 2].ljust(precision_digits + 2, "0")

    if not digits or all(c == "0" for c in digits):
        digits = "3141592653589793"[: precision_digits + 2]

    try:
        base_value = float("0." + digits)
    except ValueError:
        base_value = 0.5

    seed_value = normalize_seed(seed)
    mixed = (base_value + math.sin(seed_value * 1e6)) % 1.0
    return min(max(mixed, 0.0), 0.9999999999999999)
