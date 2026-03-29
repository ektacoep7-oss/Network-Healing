from __future__ import annotations

import numpy as np


def pso_optimize_1d(
    objective_values: np.ndarray,
    rng: np.random.Generator,
    *,
    n_particles: int = 16,
    n_iters: int = 20,
    w_inertia: float = 0.6,
    c1: float = 1.4,
    c2: float = 1.4,
) -> float:
    """
    Simple 1D PSO over index-space [0, n-1], maximizing objective_values[index].
    Returns a continuous position; caller rounds/clamps to an index.
    """
    n = int(objective_values.shape[0])
    if n <= 1:
        return 0.0

    pos = rng.uniform(0.0, n - 1, size=n_particles)
    vel = rng.normal(0.0, 0.5, size=n_particles)

    def score(x: float) -> float:
        idx = int(np.clip(np.rint(x), 0, n - 1))
        return float(objective_values[idx])

    pbest_pos = pos.copy()
    pbest_score = np.array([score(x) for x in pos], dtype=float)
    gbest_i = int(np.argmax(pbest_score))
    gbest_pos = float(pbest_pos[gbest_i])

    for _ in range(n_iters):
        r1 = rng.random(n_particles)
        r2 = rng.random(n_particles)
        vel = w_inertia * vel + c1 * r1 * (pbest_pos - pos) + c2 * r2 * (gbest_pos - pos)
        pos = np.clip(pos + vel, 0.0, n - 1)

        cur_score = np.array([score(x) for x in pos], dtype=float)
        improved = cur_score > pbest_score
        pbest_score[improved] = cur_score[improved]
        pbest_pos[improved] = pos[improved]

        gbest_i = int(np.argmax(pbest_score))
        gbest_pos = float(pbest_pos[gbest_i])

    return gbest_pos

