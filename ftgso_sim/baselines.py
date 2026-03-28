"""
Additional baseline policies and comparison strategies (Stage 7).
Includes Kubernetes-inspired approach and SC-FTGSO comparison.
"""
from __future__ import annotations

from enum import Enum
import numpy as np


class BaselinePolicy(Enum):
    """Baseline comparison policies (Stage 7)."""
    ROUND_ROBIN = "round_robin"
    PSO_ONLY = "pso_only"
    GA_ONLY = "ga_only"
    KUBERNETES = "kubernetes"
    SC_FTGSO = "sc_ftgso"  # Full SC-FTGSO (our approach)


class KubernetesInspiredRouter:
    """
    Kubernetes-inspired routing policy for baseline comparison.
    Uses readiness probes and resource requests/limits.
    """

    def __init__(self):
        self.readiness_states: dict[int, bool] = {}
        self.resource_requests: dict[int, dict[str, float]] = {}
        self.resource_limits: dict[int, dict[str, float]] = {}

    def register_instance(
        self,
        instance_id: int,
        cpu_request: float,
        memory_request: float,
        cpu_limit: float,
        memory_limit: float,
    ) -> None:
        """Register instance with resource requests/limits."""
        self.readiness_states[instance_id] = True
        self.resource_requests[instance_id] = {"cpu": cpu_request, "memory": memory_request}
        self.resource_limits[instance_id] = {"cpu": cpu_limit, "memory": memory_limit}

    def liveness_probe(
        self,
        instance_id: int,
        is_responding: bool,
        cpu_usage: float,
        memory_usage: float,
    ) -> bool:
        """
        Kubernetes-style liveness probe.
        Marks pod as ready/not-ready based on responsiveness and resources.
        """
        if not is_responding:
            self.readiness_states[instance_id] = False
            return False

        # Check if using > 90% of limits
        cpu_limit = self.resource_limits.get(instance_id, {}).get("cpu", 1.0)
        mem_limit = self.resource_limits.get(instance_id, {}).get("memory", 1.0)

        if cpu_usage > 0.9 * cpu_limit or memory_usage > 0.9 * mem_limit:
            self.readiness_states[instance_id] = False
            return False

        self.readiness_states[instance_id] = True
        return True

    def select_ready_instance(
        self,
        instance_ids: np.ndarray,
        rng: np.random.Generator,
    ) -> int | None:
        """
        Select a ready instance (Kubernetes scheduling).
        Uses round-robin among ready pods.
        """
        ready_ids = [
            iid for iid in instance_ids
            if self.readiness_states.get(int(iid), False)
        ]

        if not ready_ids:
            return None

        return int(ready_ids[rng.integers(0, len(ready_ids))])


class SCFTGSOComparison:
    """
    SC-FTGSO - Service Cluster Fault Tolerant Genetical Swarm Optimization.
    Full implementation as shown in Stage 7 comparison.
    
    This is the complete strategy combining all stages.
    """

    def __init__(
        self,
        use_pso: bool = True,
        use_ga: bool = True,
        use_clustering: bool = True,
        use_healing: bool = True,
        use_gossip: bool = True,
    ):
        self.use_pso = use_pso
        self.use_ga = use_ga
        self.use_clustering = use_clustering
        self.use_healing = use_healing
        self.use_gossip = use_gossip
        self.policy_name = "SC-FTGSO"

    def get_enabled_features(self) -> str:
        """Get string description of enabled features."""
        features = []
        if self.use_pso:
            features.append("PSO")
        if self.use_ga:
            features.append("GA")
        if self.use_clustering:
            features.append("Clustering")
        if self.use_healing:
            features.append("Healing")
        if self.use_gossip:
            features.append("Gossip")
        return "+".join(features)


class PolicyFactory:
    """Factory for creating different baseline policies."""

    @staticmethod
    def create_round_robin() -> dict[str, any]:
        """Round-robin policy configuration."""
        return {
            "name": "Round-Robin",
            "use_pso": False,
            "use_ga": False,
            "use_clustering": False,
            "use_healing": False,
            "use_gossip": False,
        }

    @staticmethod
    def create_pso_only() -> dict[str, any]:
        """PSO-only policy configuration."""
        return {
            "name": "PSO-Only",
            "use_pso": True,
            "use_ga": False,
            "use_clustering": False,
            "use_healing": False,
            "use_gossip": False,
        }

    @staticmethod
    def create_ga_only() -> dict[str, any]:
        """GA-only policy configuration."""
        return {
            "name": "GA-Only",
            "use_pso": False,
            "use_ga": True,
            "use_clustering": False,
            "use_healing": False,
            "use_gossip": False,
        }

    @staticmethod
    def create_kubernetes() -> dict[str, any]:
        """Kubernetes-inspired policy configuration."""
        return {
            "name": "Kubernetes",
            "use_pso": False,
            "use_ga": False,
            "use_clustering": False,
            "use_healing": True,
            "use_gossip": False,
            "scheduler": "kubernetes",
        }

    @staticmethod
    def create_sc_ftgso() -> dict[str, any]:
        """Full SC-FTGSO policy configuration."""
        return {
            "name": "SC-FTGSO",
            "use_pso": True,
            "use_ga": True,
            "use_clustering": True,
            "use_healing": True,
            "use_gossip": True,
        }

    @staticmethod
    def create_all_policies() -> dict[str, dict]:
        """Create all baseline policies."""
        return {
            "round_robin": PolicyFactory.create_round_robin(),
            "pso_only": PolicyFactory.create_pso_only(),
            "ga_only": PolicyFactory.create_ga_only(),
            "kubernetes": PolicyFactory.create_kubernetes(),
            "sc_ftgso": PolicyFactory.create_sc_ftgso(),
        }
