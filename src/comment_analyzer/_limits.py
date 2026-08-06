"""Set conservative CPU/memory limits for numeric libraries.

The Hub is deployed on small single-purpose servers (1-2 vCPU, ~1.6 GB RAM)
that are typically oversubscribed with other services. NumPy, SciPy and
scikit-learn dispatch work to every core by default, which oversubscribes the
box and spikes memory during analysis (each BLAS/OpenMP worker allocates its
own buffers).

Setting these environment variables *before* the libraries are imported caps
the thread pools they spin up. The values can be overridden by the caller's
own environment: this module only fills in defaults via ``setdefault``.

Import this module before ``numpy``/``pandas``/``sklearn``/``gensim`` loads.
"""

from __future__ import annotations

import os

_THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "MKL_DOMAIN_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "GOTO_NUM_THREADS",
    "BLIS_NUM_THREADS",
)


def apply_runtime_limits(default_threads: str = "1") -> None:
    """Set default thread caps for numeric libraries (does not override env)."""
    for name in _THREAD_ENV_VARS:
        os.environ.setdefault(name, default_threads)


# Apply immediately on import so that any later ``import numpy``/``sklearn``
# in the same process picks up the limits.
apply_runtime_limits()
