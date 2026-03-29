"""
Multi-layer self-healing mechanism (Stage 5 of flow diagram).
Implements 3-layer healing: Link rewording, Service migration, Predictive load shedding.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import numpy as np


class HealingLayer(Enum):
    """Three layers of self-healing."""
    LAYER_1_LINK_REWORDING = "link_rewording"      # Remove from routing
    LAYER_2_SERVICE_MIGRATION = "service_migration"  # Relocate services
    LAYER_3_PREDICTIVE_SHED = "predictive_shed"    # Load shedding


@dataclass(frozen=True)
class HealingAction:
    """Represents a healing action taken by the system."""
    layer: HealingLayer
    instance_id: int
    timestamp: int
    effectiveness: float  # 0..1, how much it helped


class SelfHealingManager:
    """
    Manages three-layer self-healing based on detected faults.
    Stage 5: Three-layer self-healing
    - Layer 1: Link Rewording (remove from routing)
    - Layer 2: Service Migration (relocate from unhealthy instance)
    - Layer 3: Predictive Load Shedding (reduce load proactively)
    """

    def __init__(
        self,
        cooldown_steps: int = 8,
        recovery_boost: float = 0.35,
        migration_threshold: float = 0.4,
        shed_threshold: float = 0.2,
    ):
        self.cooldown_steps = cooldown_steps
        self.recovery_boost = recovery_boost
        self.migration_threshold = migration_threshold
        self.shed_threshold = shed_threshold
        
        # Track healing state
        self.drained: np.ndarray = None  # Instances removed from routing (Layer 1)
        self.cooldown: np.ndarray = None  # Cooldown counter per instance
        self.healing_history: list[HealingAction] = []

    def initialize(self, n_instances: int) -> None:
        """Initialize healing state for n instances."""
        self.drained = np.zeros(n_instances, dtype=bool)
        self.cooldown = np.zeros(n_instances, dtype=int)

    def apply_layer1_link_rewording(
        self,
        detected_faulty: np.ndarray,
        timestamp: int,
    ) -> np.ndarray:
        """
        Layer 1: Link Rewording - remove faulty instances from routing.
        Returns mask of newly drained instances.
        """
        newly_drained = detected_faulty & (~self.drained)
        self.drained[newly_drained] = True
        self.cooldown[newly_drained] = self.cooldown_steps
        
        # Record healing actions
        for idx in np.where(newly_drained)[0]:
            self.healing_history.append(HealingAction(
                layer=HealingLayer.LAYER_1_LINK_REWORDING,
                instance_id=int(idx),
                timestamp=timestamp,
                effectiveness=0.7,
            ))
        
        return newly_drained

    def apply_layer2_service_migration(
        self,
        instance_id: int,
        target_instance_ids: np.ndarray,
        load_to_migrate: float,
        timestamp: int,
    ) -> float:
        """
        Layer 2: Service Migration - move load from unhealthy to healthy instances.
        
        Args:
            instance_id: Source (unhealthy) instance
            target_instance_ids: Candidate destination instances
            load_to_migrate: Amount of load to move [0..1]
            timestamp: Current step
            
        Returns:
            Actual load migrated
        """
        if len(target_instance_ids) == 0:
            return 0.0
        
        # In simulation, we model this as reducing impact on source
        # and increasing load on targets (modeled in caller)
        actual_migrated = min(load_to_migrate, 0.8)  # Max 80% can migrate
        
        self.healing_history.append(HealingAction(
            layer=HealingLayer.LAYER_2_SERVICE_MIGRATION,
            instance_id=instance_id,
            timestamp=timestamp,
            effectiveness=actual_migrated,
        ))
        
        return actual_migrated

    def apply_layer3_predictive_shedding(
        self,
        utilization: np.ndarray,
        serveability: np.ndarray,
        timestamp: int,
    ) -> np.ndarray:
        """
        Layer 3: Predictive Load Shedding - proactively reduce load before saturation.
        
        Args:
            utilization: Current resource utilization [0..1]
            serveability: Service availability [0..1]
            timestamp: Current step
            
        Returns:
            Mask of instances where load should be shed
        """
        # Shed load if approaching utilization limit AND low serveability
        should_shed = (utilization > (1.0 - self.shed_threshold)) & (serveability < self.migration_threshold)
        
        # Record actions
        for idx in np.where(should_shed)[0]:
            self.healing_history.append(HealingAction(
                layer=HealingLayer.LAYER_3_PREDICTIVE_SHED,
                instance_id=int(idx),
                timestamp=timestamp,
                effectiveness=0.5,
            ))
        
        return should_shed

    def progress_cooldown(self) -> np.ndarray:
        """
        Progress cooldown and return instances ready to rejoin.
        """
        active_cooldown = self.drained & (self.cooldown > 0)
        self.cooldown[active_cooldown] -= 1
        
        rejoin_mask = self.drained & (self.cooldown == 0)
        self.drained[rejoin_mask] = False
        
        return rejoin_mask

    def apply_recovery_boost(
        self,
        rejoin_mask: np.ndarray,
        serveability: np.ndarray,
        headroom: np.ndarray,
        latency_ms: np.ndarray,
        net_penalty: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Apply recovery boost metrics when instances rejoin after healing.
        """
        serveability[rejoin_mask] = np.clip(
            serveability[rejoin_mask] + self.recovery_boost, 0.0, 1.0
        )
        headroom[rejoin_mask] = np.clip(headroom[rejoin_mask] + 0.25, 0.0, 1.0)
        latency_ms[rejoin_mask] = np.clip(latency_ms[rejoin_mask] * 0.75, 5.0, 500.0)
        net_penalty[rejoin_mask] = np.clip(net_penalty[rejoin_mask] - 0.10, 0.0, 1.0)
        
        return serveability, headroom, latency_ms, net_penalty

    def get_drained_instances(self) -> np.ndarray:
        """Get set of currently drained instances."""
        return np.where(self.drained)[0]

    def get_healing_history(self, layer: HealingLayer | None = None) -> list[HealingAction]:
        """Get healing history, optionally filtered by layer."""
        if layer is None:
            return self.healing_history.copy()
        return [h for h in self.healing_history if h.layer == layer]

    def get_layer_effectiveness(self, layer: HealingLayer) -> float:
        """Get average effectiveness of a healing layer."""
        actions = [h for h in self.healing_history if h.layer == layer]
        if not actions:
            return 0.0
        return float(np.mean([h.effectiveness for h in actions]))
