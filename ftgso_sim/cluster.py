"""
Cluster management and cluster head (master node) election.
Implements Stage 2 of flow diagram: MO-GSO cluster formation & master node selection.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .model import Instance, InstanceMetrics, ResourceTier
from .fitness import FitnessWeights, fitness_score


@dataclass(frozen=True)
class ClusterInfo:
    """Information about a cluster and its head."""
    cluster_id: int
    instance_ids: list[int]
    cluster_head_id: int
    fitness_score: float
    resources_profile: str  # e.g., "high-CPU", "balanced"


class ClusterManager:
    """
    Manages cluster formation and master node (cluster head) election.
    Stage 2: MO-GSO cluster formation & master node selection.
    """

    def __init__(self, n_clusters: int, weights: FitnessWeights | None = None):
        self.n_clusters = n_clusters
        self.weights = weights or FitnessWeights()
        self.clusters: dict[int, ClusterInfo] = {}
        self.instance_to_cluster: dict[int, int] = {}

    def form_clusters(
        self,
        instances: list[Instance],
        rng: np.random.Generator,
    ) -> dict[int, ClusterInfo]:
        """
        Form clusters and elect cluster heads using multi-objective optimization.
        
        Stage 2: MO-GSO cluster formation - consider:
        - Proximity (latency)
        - Communication cost
        - Residual energy (headroom)
        - Coverage (serveability)
        """
        self.clusters.clear()
        self.instance_to_cluster.clear()
        
        # Group instances by existing group_id
        groups: dict[int, list[Instance]] = {}
        for inst in instances:
            if inst.group_id not in groups:
                groups[inst.group_id] = []
            groups[inst.group_id].append(inst)
        
        cluster_id = 0
        for group_id, group_instances in groups.items():
            if not group_instances:
                continue
            
            # Elect cluster head based on fitness
            best_idx = self._elect_cluster_head(group_instances)
            cluster_head = group_instances[best_idx]
            
            instance_ids = [inst.instance_id for inst in group_instances]
            
            cluster_info = ClusterInfo(
                cluster_id=cluster_id,
                instance_ids=instance_ids,
                cluster_head_id=cluster_head.instance_id,
                fitness_score=fitness_score(cluster_head.metrics, w=self.weights),
                resources_profile=self._classify_resources(cluster_head),
            )
            
            self.clusters[cluster_id] = cluster_info
            for iid in instance_ids:
                self.instance_to_cluster[iid] = cluster_id
            
            cluster_id += 1
        
        return self.clusters

    def _elect_cluster_head(self, instances: list[Instance]) -> int:
        """
        Elect cluster head using multi-objective fitness.
        Returns index of best instance.
        """
        if not instances:
            return 0
        if len(instances) == 1:
            return 0
        
        scores = [fitness_score(inst.metrics, w=self.weights) for inst in instances]
        return int(np.argmax(scores))

    def _classify_resources(self, instance: Instance) -> str:
        """Classify instance resources as profile string."""
        if instance.tier == ResourceTier.TIER_1_NORMAL:
            return "low-resources"
        elif instance.tier == ResourceTier.TIER_2_INTERMEDIATE:
            return "balanced"
        else:
            return "high-resources"

    def get_cluster(self, cluster_id: int) -> ClusterInfo | None:
        """Get cluster info by ID."""
        return self.clusters.get(cluster_id)

    def get_instance_cluster(self, instance_id: int) -> int | None:
        """Get cluster ID for an instance."""
        return self.instance_to_cluster.get(instance_id)

    def get_cluster_members(self, cluster_id: int) -> list[int]:
        """Get all member instance IDs of a cluster."""
        cluster = self.clusters.get(cluster_id)
        return cluster.instance_ids if cluster else []

    def get_cluster_head_id(self, cluster_id: int) -> int | None:
        """Get cluster head (master node) ID."""
        cluster = self.clusters.get(cluster_id)
        return cluster.cluster_head_id if cluster else None

    def reelect_cluster_head(
        self,
        cluster_id: int,
        instances: list[Instance],
    ) -> bool:
        """
        Re-elect cluster head if current one becomes unhealthy.
        Returns True if head changed.
        """
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return False
        
        # Find all healthy members
        healthy_instances = [inst for inst in instances if inst.is_healthy and inst.instance_id in cluster.instance_ids]
        
        if not healthy_instances:
            return False
        
        # Elect new head
        best_idx = self._elect_cluster_head(healthy_instances)
        new_head_id = healthy_instances[best_idx].instance_id
        
        if new_head_id != cluster.cluster_head_id:
            # Update cluster info
            updated = ClusterInfo(
                cluster_id=cluster.cluster_id,
                instance_ids=cluster.instance_ids,
                cluster_head_id=new_head_id,
                fitness_score=fitness_score(healthy_instances[best_idx].metrics, w=self.weights),
                resources_profile=cluster.resources_profile,
            )
            self.clusters[cluster_id] = updated
            return True
        
        return False

    def get_all_cluster_heads(self) -> list[int]:
        """Get IDs of all cluster heads."""
        return [info.cluster_head_id for info in self.clusters.values()]
