"""
Gossip protocol for distributed anomaly sharing (Stage 3 of flow diagram).
Enables cluster heads to share fault detection information.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
import numpy as np

from .fault import FaultEvent, FaultType


@dataclass(frozen=True)
class AnomalyMessage:
    """Message containing anomaly information to be gossiped."""
    source_cluster_id: int
    instance_id: int
    fault_type: FaultType
    severity: float
    timestamp: int
    hop_count: int = 0  # Number of hops


class GossipProtocol:
    """
    Distributed gossip protocol for sharing fault detection results.
    Stage 3: PSO phase - distributed anomaly share.
    """

    def __init__(self, max_hops: int = 3, dissemination_prob: float = 0.8):
        self.max_hops = max_hops
        self.dissemination_prob = dissemination_prob
        self.message_queue: list[AnomalyMessage] = []
        self.seen_messages: set[tuple[int, int, int]] = set()  # (source, instance_id, timestamp)
        self.cluster_members: dict[int, list[int]] = defaultdict(list)  # cluster_id -> [instance_ids]
        self.instance_to_cluster: dict[int, int] = {}  # instance_id -> cluster_id

    def register_cluster(self, cluster_id: int, instance_ids: list[int]) -> None:
        """Register cluster membership."""
        self.cluster_members[cluster_id] = instance_ids.copy()
        for iid in instance_ids:
            self.instance_to_cluster[iid] = cluster_id

    def create_message(
        self,
        source_cluster_id: int,
        instance_id: int,
        fault_type: FaultType,
        severity: float,
        timestamp: int,
    ) -> AnomalyMessage:
        """Create a new anomaly message."""
        return AnomalyMessage(
            source_cluster_id=source_cluster_id,
            instance_id=instance_id,
            fault_type=fault_type,
            severity=severity,
            timestamp=timestamp,
            hop_count=0,
        )

    def broadcast_fault(
        self,
        fault_event: FaultEvent,
        source_cluster_id: int,
        rng: np.random.Generator,
    ) -> None:
        """Broadcast a detected fault via gossip protocol."""
        msg = self.create_message(
            source_cluster_id=source_cluster_id,
            instance_id=fault_event.instance_id,
            fault_type=fault_event.fault_type,
            severity=fault_event.severity,
            timestamp=fault_event.timestamp,
        )
        
        # Add to queue if not seen before
        msg_key = (source_cluster_id, fault_event.instance_id, fault_event.timestamp)
        if msg_key not in self.seen_messages:
            self.message_queue.append(msg)
            self.seen_messages.add(msg_key)

    def propagate_step(
        self,
        rng: np.random.Generator,
    ) -> list[AnomalyMessage]:
        """
        Perform one gossip propagation step.
        Returns newly propagated messages.
        """
        propagated = []
        
        # Process existing messages
        new_queue = []
        for msg in self.message_queue:
            if msg.hop_count < self.max_hops and rng.random() < self.dissemination_prob:
                # Propagate to neighboring clusters
                propagated.append(msg)
                new_msg = AnomalyMessage(
                    source_cluster_id=msg.source_cluster_id,
                    instance_id=msg.instance_id,
                    fault_type=msg.fault_type,
                    severity=msg.severity,
                    timestamp=msg.timestamp,
                    hop_count=msg.hop_count + 1,
                )
                new_queue.append(new_msg)
            elif msg.hop_count < self.max_hops:
                new_queue.append(msg)
        
        self.message_queue = new_queue
        return propagated

    def get_known_faults(self, cluster_id: int) -> dict[int, AnomalyMessage]:
        """Get all currently known faults for a cluster."""
        known_faults: dict[int, AnomalyMessage] = {}
        for msg in self.message_queue:
            # Include faults from own cluster and propagated ones
            known_faults[msg.instance_id] = msg
        return known_faults

    def clear_old_messages(self, current_timestamp: int, max_age: int = 10) -> None:
        """Remove old messages from queue."""
        self.message_queue = [
            msg for msg in self.message_queue
            if current_timestamp - msg.timestamp <= max_age
        ]
