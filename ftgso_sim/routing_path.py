"""
Enhanced routing path representation and GA operators (Stage 4).
Implements chromosome as routing path instead of just indices.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from typing import List


@dataclass(frozen=True)
class RoutingPath:
    """Represents a routing path/chromosome (Stage 4)."""
    primary_instance_id: int  # Primary target
    backup_instances: tuple[int, ...] = ()  # Backup route
    path_fitness: float = 0.0  # Cached fitness of this path


class RoutingPathGA:
    """
    GA operators for routing paths.
    Stage 4: GA phase - fault-free routing & load redistribution.
    """

    def __init__(self, pop_size: int = 20, generations: int = 15, mutation_prob: float = 0.2):
        self.pop_size = pop_size
        self.generations = generations
        self.mutation_prob = mutation_prob

    def create_initial_population(
        self,
        objective_values: np.ndarray,
        n_backups: int = 2,
        rng: np.random.Generator = None,
    ) -> list[RoutingPath]:
        """
        Create initial population of routing paths.
        Each path has a primary and backup instances.
        """
        if rng is None:
            rng = np.random.default_rng()
        
        n = len(objective_values)
        if n == 0:
            return []
        
        population = []
        for _ in range(self.pop_size):
            # Primary instance
            primary_idx = int(rng.integers(0, n))
            
            # Backup instances (different from primary)
            available = np.arange(n)
            available = available[available != primary_idx]
            
            if len(available) > 0:
                n_backup = min(n_backups, len(available))
                backup_indices = rng.choice(available, size=n_backup, replace=False)
                backups = tuple(int(idx) for idx in backup_indices)
            else:
                backups = ()
            
            path = RoutingPath(
                primary_instance_id=primary_idx,
                backup_instances=backups,
                path_fitness=float(objective_values[primary_idx]),
            )
            population.append(path)
        
        return population

    def evaluate_population(
        self,
        population: list[RoutingPath],
        objective_values: np.ndarray,
    ) -> np.ndarray:
        """Evaluate fitness of all paths in population."""
        scores = np.zeros(len(population), dtype=float)
        for i, path in enumerate(population):
            # Fitness is primarily based on primary instance
            primary_fitness = float(objective_values[path.primary_instance_id])
            
            # Bonus for having backups
            backup_bonus = 0.0
            if path.backup_instances:
                # Average fitness of backups
                backup_fitness = np.mean([
                    objective_values[bid] for bid in path.backup_instances
                ])
                backup_bonus = 0.1 * backup_fitness  # Small weight
            
            scores[i] = primary_fitness + backup_bonus
        
        return scores

    def crossover(
        self,
        parent1: RoutingPath,
        parent2: RoutingPath,
        objective_values: np.ndarray,
        rng: np.random.Generator,
    ) -> RoutingPath:
        """
        Crossover operation: blend primary and backup from two parents.
        """
        # Primary: randomly select from parents
        primary = parent1.primary_instance_id if rng.random() < 0.5 else parent2.primary_instance_id
        
        # Backups: combine from both parents
        backup_candidates = list(parent1.backup_instances) + list(parent2.backup_instances)
        backup_candidates = list(set(backup_candidates))  # Remove duplicates
        backup_candidates = [b for b in backup_candidates if b != primary]  # Exclude primary
        
        if backup_candidates:
            n_backups = min(2, len(backup_candidates))
            backups_selected = rng.choice(backup_candidates, size=n_backups, replace=False)
            backups = tuple(int(b) for b in backups_selected)
        else:
            backups = ()
        
        return RoutingPath(
            primary_instance_id=int(primary),
            backup_instances=backups,
            path_fitness=float(objective_values[int(primary)]),
        )

    def mutate(
        self,
        path: RoutingPath,
        objective_values: np.ndarray,
        rng: np.random.Generator,
    ) -> RoutingPath:
        """
        Mutation: randomly change primary or backups.
        """
        n = len(objective_values)
        
        if rng.random() < self.mutation_prob:
            # Mutate primary
            new_primary = int(rng.integers(0, n))
            backups = path.backup_instances
        else:
            # Mutate backups
            new_primary = path.primary_instance_id
            available = np.arange(n)
            available = available[available != new_primary]
            
            if len(available) > 0:
                n_backup = min(2, len(available))
                new_backups = rng.choice(available, size=n_backup, replace=False)
                backups = tuple(int(b) for b in new_backups)
            else:
                backups = ()
        
        return RoutingPath(
            primary_instance_id=int(new_primary),
            backup_instances=backups,
            path_fitness=float(objective_values[int(new_primary)]),
        )

    def evolve_population(
        self,
        population: list[RoutingPath],
        objective_values: np.ndarray,
        rng: np.random.Generator,
    ) -> list[RoutingPath]:
        """
        Run GA for specified generations and return best population.
        """
        pop = population.copy()
        
        for _ in range(self.generations):
            # Evaluate
            scores = self.evaluate_population(pop, objective_values)
            
            # Selection: tournament-style, keep top half
            top_k = max(2, self.pop_size // 2)
            elite_indices = np.argsort(scores)[-top_k:]
            elites = [pop[int(i)] for i in elite_indices]
            
            # Create new population
            new_pop = []
            
            # Elitism: keep best
            best_idx = int(np.argmax(scores))
            new_pop.append(pop[best_idx])
            
            # Generate offspring
            while len(new_pop) < self.pop_size:
                # Tournament selection
                p1 = elites[rng.integers(0, len(elites))]
                p2 = elites[rng.integers(0, len(elites))]
                
                # Crossover
                child = self.crossover(p1, p2, objective_values, rng)
                
                # Mutation
                if rng.random() < self.mutation_prob:
                    child = self.mutate(child, objective_values, rng)
                
                new_pop.append(child)
            
            pop = new_pop
        
        return pop

    def select_best_path(
        self,
        population: list[RoutingPath],
        objective_values: np.ndarray,
    ) -> RoutingPath:
        """Select best path from population."""
        if not population:
            return RoutingPath(primary_instance_id=0, backup_instances=(), path_fitness=0.0)
        
        scores = self.evaluate_population(population, objective_values)
        best_idx = int(np.argmax(scores))
        return population[best_idx]
