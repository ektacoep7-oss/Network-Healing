"""
Fault detection and classification (Stage 3 of flow diagram).
Implements Hard, Soft, and Transient fault detection.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FaultType(Enum):
    """Fault classification types (Stage 3 of diagram)."""
    HARD_FAULT = "hard"              # Node unreachable (persistent)
    SOFT_FAULT = "soft"              # CPU/Memory saturated (degradation)
    TRANSIENT_FAULT = "transient"    # Intermittent spike (temporary)
    HEALTHY = "healthy"              # No fault detected


@dataclass(frozen=True)
class FaultEvent:
    """Represents a detected fault event."""
    instance_id: int
    fault_type: FaultType
    severity: float  # 0.0 (minor) to 1.0 (critical)
    timestamp: int   # Simulation step
    is_persistent: bool = False  # True if detected for multiple steps


class FaultDetector:
    """
    Detects and classifies faults based on instance metrics and history.
    Implements Stage 3 fault type classification logic.
    """

    def __init__(self, hard_fault_threshold: float = 0.0, soft_fault_threshold: float = 0.5, transient_window: int = 3):
        self.hard_fault_threshold = hard_fault_threshold  # Serveability < threshold = hard fault
        self.soft_fault_threshold = soft_fault_threshold  # Utilization > threshold = soft fault
        self.transient_window = transient_window  # Steps to confirm transient fault
        self.fault_history: dict[int, list[FaultEvent]] = {}  # instance_id -> list of events

    def detect_fault(
        self,
        instance_id: int,
        is_reachable: bool,
        serveability: float,
        cpu_util: float,
        mem_util: float,
        io_util: float,
        timestamp: int,
    ) -> FaultEvent | None:
        """
        Detect fault type based on instance metrics.
        
        Args:
            instance_id: Instance identifier
            is_reachable: Whether node is reachable
            serveability: Service availability [0..1]
            cpu_util, mem_util, io_util: Utilization metrics [0..1]
            timestamp: Current simulation step
            
        Returns:
            FaultEvent if fault detected, None otherwise
        """
        if not is_reachable or serveability < self.hard_fault_threshold:
            # Hard fault: node unreachable
            event = FaultEvent(
                instance_id=instance_id,
                fault_type=FaultType.HARD_FAULT,
                severity=1.0 - serveability,
                timestamp=timestamp,
                is_persistent=True,
            )
            self._record_fault(instance_id, event)
            return event

        max_util = max(cpu_util, mem_util, io_util)
        if max_util > self.soft_fault_threshold:
            # Soft fault: resource saturation
            event = FaultEvent(
                instance_id=instance_id,
                fault_type=FaultType.SOFT_FAULT,
                severity=max_util - self.soft_fault_threshold,
                timestamp=timestamp,
                is_persistent=False,
            )
            self._record_fault(instance_id, event)
            return event

        # Check for transient faults (intermittent spikes)
        if self._is_transient_spike(instance_id, timestamp):
            event = FaultEvent(
                instance_id=instance_id,
                fault_type=FaultType.TRANSIENT_FAULT,
                severity=0.5,  # Medium severity
                timestamp=timestamp,
                is_persistent=False,
            )
            self._record_fault(instance_id, event)
            return event

        return None

    def _record_fault(self, instance_id: int, event: FaultEvent) -> None:
        """Track fault event in history."""
        if instance_id not in self.fault_history:
            self.fault_history[instance_id] = []
        self.fault_history[instance_id].append(event)

    def _is_transient_spike(self, instance_id: int, timestamp: int) -> bool:
        """Detect intermittent spike pattern."""
        if instance_id not in self.fault_history:
            return False
        
        recent = [e for e in self.fault_history[instance_id] if timestamp - e.timestamp < self.transient_window]
        # Transient if fault detected but quickly recovered
        return len(recent) == 1 and recent[0].fault_type in (FaultType.SOFT_FAULT, FaultType.TRANSIENT_FAULT)

    def get_fault_history(self, instance_id: int) -> list[FaultEvent]:
        """Get all recorded faults for an instance."""
        return self.fault_history.get(instance_id, [])

    def clear_history(self, instance_id: int | None = None) -> None:
        """Clear fault history."""
        if instance_id is None:
            self.fault_history.clear()
        elif instance_id in self.fault_history:
            del self.fault_history[instance_id]
