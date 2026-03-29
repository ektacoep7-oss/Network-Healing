from __future__ import annotations

import numpy as np


def ga_refine_1d(
    objective_values: np.ndarray,
    rng: np.random.Generator,
    seed_index: int,
    *,
    pop_size: int = 20,
    generations: int = 15,
    mutation_prob: float = 0.2,
) -> int:
    """
    Tiny GA on integer index chromosomes, maximizing objective_values[index].
    """
    n = int(objective_values.shape[0])
    if n <= 1:
        return 0

    def fit(idx: int) -> float:
        return float(objective_values[int(np.clip(idx, 0, n - 1))])

    pop = rng.integers(0, n, size=pop_size)
    pop[0] = int(np.clip(seed_index, 0, n - 1))

    for _ in range(generations):
        scores = np.array([fit(int(x)) for x in pop], dtype=float)

        # Tournament-style selection by sampling top half.
        top_k = max(2, pop_size // 2)
        elite_idx = np.argsort(scores)[-top_k:]
        elites = pop[elite_idx]

        new_pop = np.empty_like(pop)
        new_pop[0] = int(elites[np.argmax([fit(int(x)) for x in elites])])  # elitism
        for i in range(1, pop_size):
            p1 = int(elites[rng.integers(0, top_k)])
            p2 = int(elites[rng.integers(0, top_k)])
            child = int(np.rint((p1 + p2) / 2.0))
            if rng.random() < mutation_prob:
                child += int(rng.integers(-2, 3))
            new_pop[i] = int(np.clip(child, 0, n - 1))
        pop = new_pop

    final_scores = np.array([fit(int(x)) for x in pop], dtype=float)
    return int(pop[int(np.argmax(final_scores))])

