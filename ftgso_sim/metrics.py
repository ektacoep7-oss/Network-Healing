"""
Advanced performance metrics and evaluation (Stage 6 of flow diagram).
Implements: TCR (Task Completion Rate), JDR (Job Drop Rate), 
JTT (Job Turnaround Time), MTTH (Mean Time To Heal).
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class PerformanceMetrics:
    """Stage 6 performance metrics."""
    tcr: float  # Task Completion Rate [0..1]
    jdr: float  # Job Drop Rate [0..1]
    jtt_ms: float  # Job Turnaround Time (ms)
    mtth: float  # Mean Time To Heal (steps)
    pdr: float  # Packet Delivery Rate (legacy)
    plr: float  # Packet Loss Rate (legacy)
    e2e_latency_ms: float  # End-to-end latency (ms)


class MetricsCollector:
    """
    Collects and computes advanced performance metrics.
    Stage 6: Performance monitoring & metrics
    """

    def __init__(self):
        self.total_tasks_submitted: int = 0
        self.total_tasks_completed: int = 0
        self.total_tasks_dropped: int = 0
        self.task_latencies: list[float] = []  # For JTT
        self.healing_events: list[tuple[int, int]] = []  # (start_step, end_step)
        self.current_fault_step: int | None = None

    def record_task_submission(self) -> None:
        """Record a new task submission."""
        self.total_tasks_submitted += 1

    def record_task_completion(self, latency_ms: float) -> None:
        """Record task completion with latency."""
        self.total_tasks_completed += 1
        self.task_latencies.append(latency_ms)

    def record_task_drop(self) -> None:
        """Record task drop."""
        self.total_tasks_dropped += 1

    def record_fault_detected(self, step: int) -> None:
        """Mark start of fault event."""
        self.current_fault_step = step

    def record_fault_resolved(self, step: int) -> None:
        """Mark end of fault event (healing complete)."""
        if self.current_fault_step is not None:
            heal_time = step - self.current_fault_step
            self.healing_events.append((self.current_fault_step, step))
            self.current_fault_step = None

    def compute_tcr(self) -> float:
        """
        Task Completion Rate.
        TCR = completed_tasks / submitted_tasks
        """
        if self.total_tasks_submitted == 0:
            return 0.0
        return float(self.total_tasks_completed) / float(self.total_tasks_submitted)

    def compute_jdr(self) -> float:
        """
        Job Drop Rate.
        JDR = dropped_tasks / submitted_tasks
        """
        if self.total_tasks_submitted == 0:
            return 0.0
        return float(self.total_tasks_dropped) / float(self.total_tasks_submitted)

    def compute_jtt(self) -> float:
        """
        Job Turnaround Time (mean).
        JTT = average latency of completed tasks
        """
        if len(self.task_latencies) == 0:
            return 0.0
        return float(np.mean(self.task_latencies))

    def compute_mtth(self) -> float:
        """
        Mean Time To Heal.
        MTTH = average time to recover from faults
        """
        if len(self.healing_events) == 0:
            return 0.0
        heal_times = [end - start for start, end in self.healing_events]
        return float(np.mean(heal_times))

    def compute_pdr(self) -> float:
        """Packet Delivery Rate (legacy metric)."""
        return self.compute_tcr()

    def compute_plr(self) -> float:
        """Packet Loss Rate (legacy metric)."""
        return self.compute_jdr()

    def compute_e2e_latency(self) -> float:
        """End-to-end latency (legacy metric)."""
        return self.compute_jtt()

    def get_metrics(self) -> PerformanceMetrics:
        """Get all performance metrics."""
        return PerformanceMetrics(
            tcr=self.compute_tcr(),
            jdr=self.compute_jdr(),
            jtt_ms=self.compute_jtt(),
            mtth=self.compute_mtth(),
            pdr=self.compute_pdr(),
            plr=self.compute_plr(),
            e2e_latency_ms=self.compute_e2e_latency(),
        )

    def reset(self) -> None:
        """Reset all counters."""
        self.total_tasks_submitted = 0
        self.total_tasks_completed = 0
        self.total_tasks_dropped = 0
        self.task_latencies.clear()
        self.healing_events.clear()
        self.current_fault_step = None

    def summary_string(self) -> str:
        """Get human-readable metrics summary."""
        metrics = self.get_metrics()
        return (
            f"TCR={metrics.tcr:.4f}, JDR={metrics.jdr:.4f}, "
            f"JTT={metrics.jtt_ms:.2f}ms, MTTH={metrics.mtth:.1f}steps, "
            f"E2E={metrics.e2e_latency_ms:.2f}ms"
        )
