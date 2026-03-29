from __future__ import annotations

import numpy as np

from .ga import ga_refine_1d
from .pso import pso_optimize_1d


def select_candidate_gso(
    objective_values: np.ndarray,
    rng: np.random.Generator,
) -> int:
    """
    Hybrid GSO (paper §3.2.2 analog):
    1) PSO quickly explores index-space.
    2) GA refines around PSO candidate to avoid local traps.
    Returns selected candidate index.
    """
    if objective_values.size == 0:
        return 0
    if objective_values.size == 1:
        return 0

    pso_pos = pso_optimize_1d(objective_values, rng)
    seed_idx = int(np.clip(np.rint(pso_pos), 0, objective_values.size - 1))
    return ga_refine_1d(objective_values, rng, seed_idx)

