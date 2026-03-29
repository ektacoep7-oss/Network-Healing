from __future__ import annotations

from dataclasses import dataclass

from .model import InstanceMetrics


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _normalize_minimize(x: float, lo: float, hi: float) -> float:
    """
    Maps x in [lo, hi] to [1..0] (lower is better).
    """
    if hi <= lo:
        return 0.5
    return _clamp01(1.0 - (x - lo) / (hi - lo))


def _normalize_maximize(x: float, lo: float, hi: float) -> float:
    """
    Maps x in [lo, hi] to [0..1] (higher is better).
    """
    if hi <= lo:
        return 0.5
    return _clamp01((x - lo) / (hi - lo))


@dataclass(frozen=True)
class FitnessWeights:
    """
    Mirrors the paper's 4-objective intent (§3.3.2) using service metrics.
    Extended with fault history weight for Stage 4.
    We combine normalized objectives into a single score for now.
    
    Stage 4 fitness formula:
    w1(1-CPU) + w2(1-Mem) + w3(1/Lat) + w4(SW) + w5*FaultHistory
    """

    proximity: float = 0.25  # w3: latency weight (reduced from 0.35)
    communication_cost: float = 0.15  # w2: network penalty
    residual_energy: float = 0.25  # w1: headroom/capacity
    coverage: float = 0.20  # w4: serveability
    fault_history: float = 0.15  # w5: fault penalty (PSO-tuned)


@dataclass(frozen=True)
class FitnessBounds:
    latency_ms: tuple[float, float] = (1.0, 500.0)
    net_penalty: tuple[float, float] = (0.0, 1.0)
    headroom: tuple[float, float] = (0.0, 1.0)
    serveability: tuple[float, float] = (0.0, 1.0)


def fitness_score(
    m: InstanceMetrics,
    *,
    w: FitnessWeights = FitnessWeights(),
    b: FitnessBounds = FitnessBounds(),
    fault_penalty: float = 0.0,
) -> float:
    """
    Single scalar fitness used to (a) pick coordinators (CH analog) and
    (b) rank instances for routing.

    Paper correspondence:
    - Obj1 proximity: minimize latency
    - Obj2 comm cost: minimize net_penalty
    - Obj3 residual energy: maximize headroom
    - Obj4 coverage: maximize serveability
    - Obj5 (Stage 4): fault history penalty

    Args:
        m: Instance metrics
        w: Fitness weights
        b: Bounds for normalization
        fault_penalty: Penalty for recent faults [0..1]
    """
    f1 = _normalize_minimize(m.latency_ms, *b.latency_ms)
    f2 = _normalize_minimize(m.net_penalty, *b.net_penalty)
    f3 = _normalize_maximize(m.headroom, *b.headroom)
    f4 = _normalize_maximize(m.serveability, *b.serveability)

    # Apply fault penalty (reduces score if instance has recent faults)
    f5 = _clamp01(1.0 - fault_penalty)

    score = (
        w.proximity * f1
        + w.communication_cost * f2
        + w.residual_energy * f3
        + w.coverage * f4
        + w.fault_history * f5
    )
    return _clamp01(score)

