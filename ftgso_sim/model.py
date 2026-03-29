from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResourceTier(Enum):
    """Resource tier classification (Stage 1 of flow diagram)."""
    TIER_1_NORMAL = "normal"          # Low CPU / RAM / R/W
    TIER_2_INTERMEDIATE = "intermediate"  # Mid-range resources
    TIER_3_ADVANCED = "advanced"      # High CPU / RAM / NIC


@dataclass(frozen=True)
class InstanceMetrics:
    """
    Metrics for a single service instance (WSN SN analog).

    These are the computer-system analogs of the paper's multi-objectives (§3.3.2):
    - proximity     -> latency_ms
    - comm. cost    -> net_penalty
    - residual energy -> headroom (higher is better)
    - coverage      -> serveability (higher is better)
    """

    latency_ms: float
    net_penalty: float
    headroom: float
    serveability: float


@dataclass(frozen=True)
class EnhancedInstanceMetrics:
    """
    Enhanced metrics matching the flow diagram Stage 1 (resource fingerprint vector).
    Provides more granular resource visibility.
    """
    cpu_cores: int           # Number of CPU cores
    memory_gb: float         # Available memory in GB
    disk_io_mbps: float      # Disk I/O in MB/s
    network_latency_ms: float  # Network latency in ms
    bandwidth_mbps: float    # Network bandwidth in MB/s
    
    # Derived normalized metrics [0..1] for optimization
    cpu_utilization: float   # 0=idle, 1=saturated
    memory_utilization: float  # 0=idle, 1=saturated
    io_utilization: float    # 0=idle, 1=saturated


@dataclass(frozen=True)
class Instance:
    instance_id: int
    group_id: int
    tier: ResourceTier
    metrics: InstanceMetrics
    enhanced_metrics: EnhancedInstanceMetrics | None = None
    is_healthy: bool = True
    is_cluster_head: bool = False  # Master node (Stage 2)
