"""
Backward-compatible module entrypoint.

Prefer::

    import rrann
    from rrann import Rng, roll, health_check, create_receipt
"""

from rrann import *  # noqa: F401,F403
from rrann import __all__ as __all__  # noqa: F401
