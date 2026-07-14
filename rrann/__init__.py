"""Licensed under the Arc-9 Open Royalty Agreement v1.4. See LICENSE in the repository root.

RRann — dual-precision residual harvest RNG.

Pipeline (default)::

    seed → residual digits of seed**seed (float vs Decimal)
         → cull residual head (default 2 digits)
         → bits / float

Quick start::

    import rrann
    from rrann import Rng, roll, create_receipt, verify_receipt, health_check

    g = Rng(seed=2.4)
    print(g.random(), g.next_u64())
    a, b = g.fork(0), g.fork(1)          # independent streams

    print(roll(2.4, "loot.chest", 0))    # deterministic context roll
    r = create_receipt(2.4, "loot.chest", 0)
    assert verify_receipt(r, 2.4)

    print(health_check(2.4, profile="gameplay"))

Not a CSPRNG. Not FIPS-certified. Not a regulated casino RNG.
For adversarial secrecy, seed from the OS and/or use a standard DRBG.
"""

from .core import HarvestResult, harvest, normalize_seed
from .extract import (
    DEFAULT_CULL_HEAD,
    DEFAULT_DROP,
    bits_from_digits,
    extract_bits,
    extract_float,
    pack_bits,
    random_bits,
    random_float,
    resolve_cull_head,
    stream_seed,
    von_neumann,
    xor_adjacent,
)
from .fairness import (
    ALGO_VERSION,
    RollReceipt,
    commit_seed,
    create_receipt,
    roll,
    roll_seed,
    verify_commit,
    verify_receipt,
)
from .generator import Generator, Rng
from .health import ContinuousHealth, HealthResult, diagnose_bits, health_check
from .legacy import generate
from .simulate import (
    RateReport,
    expected_value,
    normalize_weights,
    pity_effective_rate,
    simulate_loot,
)

__version__ = "0.2.0"

__all__ = [
    "ALGO_VERSION",
    "ContinuousHealth",
    "DEFAULT_CULL_HEAD",
    "DEFAULT_DROP",
    "Generator",
    "HarvestResult",
    "HealthResult",
    "RateReport",
    "Rng",
    "RollReceipt",
    "__version__",
    "bits_from_digits",
    "commit_seed",
    "create_receipt",
    "diagnose_bits",
    "expected_value",
    "extract_bits",
    "extract_float",
    "generate",
    "harvest",
    "health_check",
    "normalize_seed",
    "normalize_weights",
    "pack_bits",
    "pity_effective_rate",
    "random_bits",
    "random_float",
    "resolve_cull_head",
    "roll",
    "roll_seed",
    "simulate_loot",
    "stream_seed",
    "verify_commit",
    "verify_receipt",
    "von_neumann",
    "xor_adjacent",
]
