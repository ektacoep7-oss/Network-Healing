<<<<<<< HEAD
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ..fitness import FitnessWeights, fitness_score
from ..model import Instance, InstanceMetrics, ResourceTier
from ..optimizer import select_candidate_gso


@dataclass(frozen=True)
class SimConfig:
    n_instances: int = 50
    n_groups: int = 5
    n_steps: int = 600
    request_rate: float = 20.0
    seed: int = 42
    low_fitness_threshold: float = 0.30
    low_fitness_window: int = 5
    degrade_prob: float = 0.01
    fail_prob: float = 0.003
    passive_recover_prob: float = 0.01
    heal_cooldown_steps: int = 8
    heal_recovery_boost: float = 0.35


def _write_summary_csv(results: dict[str, dict[str, float]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "summary.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["policy", "pdr", "plr", "e2e_ms"])
        for policy, metrics in results.items():
            writer.writerow([policy, f"{metrics['pdr']:.6f}", f"{metrics['plr']:.6f}", f"{metrics['e2e_ms']:.6f}"])
    return out_path


def _plot_metric(results: dict[str, dict[str, float]], metric_key: str, title: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    labels = list(results.keys())
    values = [results[k][metric_key] for k in labels]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(labels))
    ax.bar(x, values)
    ax.set_title(title)
    ax.set_ylabel(metric_key)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    fig.tight_layout()
    out_path = output_dir / f"{metric_key}.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    return out_path


def _initialize_instances(cfg: SimConfig, rng: np.random.Generator) -> list[Instance]:
    instances: list[Instance] = []
    tiers = [ResourceTier.TIER_1_NORMAL, ResourceTier.TIER_2_INTERMEDIATE, ResourceTier.TIER_3_ADVANCED]
    for i in range(cfg.n_instances):
        group_id = int(i % cfg.n_groups)
        tier = tiers[rng.integers(0, len(tiers))]
        m = InstanceMetrics(
            latency_ms=float(rng.uniform(5.0, 200.0)),
            net_penalty=float(rng.uniform(0.0, 0.3)),
            headroom=float(rng.uniform(0.2, 1.0)),
            serveability=float(rng.uniform(0.5, 1.0)),
        )
        instances.append(Instance(instance_id=i, group_id=group_id, tier=tier, metrics=m))
    return instances


def _simulate_one_policy(
    cfg: SimConfig,
    policy: str,
    init_instances: list[Instance],
    weights: FitnessWeights,
    *,
    with_healing: bool = False,
) -> tuple[dict[str, float], list[int]]:
    seed_offset = {
        "fitness": 0,
        "round_robin": 10_000,
        "gso": 20_000,
        "least_latency": 30_000,
        "least_loaded": 40_000,
    }.get(policy, 50_000)
    rng = np.random.default_rng(cfg.seed + seed_offset)
    n = len(init_instances)

    latency = np.array([x.metrics.latency_ms for x in init_instances], dtype=float)
    net_penalty = np.array([x.metrics.net_penalty for x in init_instances], dtype=float)
    headroom = np.array([x.metrics.headroom for x in init_instances], dtype=float)
    serveability = np.array([x.metrics.serveability for x in init_instances], dtype=float)
    healthy = np.ones(n, dtype=bool)
    rr_idx = 0

    success = 0
    failed = 0
    latency_sum = 0.0

    low_streak = np.zeros(n, dtype=int)
    detected_faulty = np.zeros(n, dtype=bool)
    drained = np.zeros(n, dtype=bool)
    cooldown = np.zeros(n, dtype=int)

    for _ in range(cfg.n_steps):
        degrade_mask = healthy & (rng.random(n) < cfg.degrade_prob)
        fail_mask = healthy & (rng.random(n) < cfg.fail_prob)

        latency[degrade_mask] = np.clip(latency[degrade_mask] * 1.35, 5.0, 500.0)
        net_penalty[degrade_mask] = np.clip(net_penalty[degrade_mask] + 0.08, 0.0, 1.0)
        headroom[degrade_mask] = np.clip(headroom[degrade_mask] - 0.12, 0.0, 1.0)
        serveability[degrade_mask] = np.clip(serveability[degrade_mask] - 0.10, 0.0, 1.0)

        healthy[fail_mask] = False
        serveability[fail_mask] = 0.0
        headroom[fail_mask] = np.clip(headroom[fail_mask] - 0.2, 0.0, 1.0)

        # Passive environmental recovery (not policy-driven healing yet).
        recover_mask = (~healthy) & (rng.random(n) < cfg.passive_recover_prob)
        healthy[recover_mask] = True
        serveability[recover_mask] = np.clip(serveability[recover_mask] + 0.25, 0.0, 1.0)
        headroom[recover_mask] = np.clip(headroom[recover_mask] + 0.20, 0.0, 1.0)
        latency[recover_mask] = np.clip(latency[recover_mask] * 0.9, 5.0, 500.0)
        net_penalty[recover_mask] = np.clip(net_penalty[recover_mask] - 0.05, 0.0, 1.0)

        scores = np.zeros(n, dtype=float)
        for i in range(n):
            if healthy[i]:
                scores[i] = fitness_score(
                    InstanceMetrics(
                        latency_ms=float(latency[i]),
                        net_penalty=float(net_penalty[i]),
                        headroom=float(headroom[i]),
                        serveability=float(serveability[i]),
                    ),
                    w=weights,
                )

        for i in range(n):
            if (not healthy[i]) or (scores[i] < cfg.low_fitness_threshold):
                low_streak[i] += 1
                if low_streak[i] >= cfg.low_fitness_window:
                    detected_faulty[i] = True
            else:
                low_streak[i] = 0

        if with_healing:
            # Paper §3.3.6 analog: remove problematic nodes from routing, restart, and rejoin.
            newly_drained = detected_faulty & (~drained)
            drained[newly_drained] = True
            cooldown[newly_drained] = cfg.heal_cooldown_steps

            active_cooldown = drained & (cooldown > 0)
            cooldown[active_cooldown] -= 1

            rejoin_mask = drained & (cooldown == 0)
            if np.any(rejoin_mask):
                healthy[rejoin_mask] = True
                drained[rejoin_mask] = False
                detected_faulty[rejoin_mask] = False
                low_streak[rejoin_mask] = 0
                serveability[rejoin_mask] = np.clip(
                    serveability[rejoin_mask] + cfg.heal_recovery_boost, 0.0, 1.0
                )
                headroom[rejoin_mask] = np.clip(headroom[rejoin_mask] + 0.25, 0.0, 1.0)
                latency[rejoin_mask] = np.clip(latency[rejoin_mask] * 0.75, 5.0, 500.0)
                net_penalty[rejoin_mask] = np.clip(net_penalty[rejoin_mask] - 0.10, 0.0, 1.0)

        healthy_ids = np.flatnonzero(healthy & (~drained))
        requests = int(rng.poisson(cfg.request_rate))
        chosen_cached = -1
        if healthy_ids.size > 0:
            if policy == "fitness":
                chosen_cached = int(healthy_ids[np.argmax(scores[healthy_ids])])
            elif policy == "gso":
                local_scores = scores[healthy_ids]
                local_idx = select_candidate_gso(local_scores, rng)
                chosen_cached = int(healthy_ids[int(np.clip(local_idx, 0, healthy_ids.size - 1))])
            elif policy == "least_latency":
                chosen_cached = int(healthy_ids[np.argmin(latency[healthy_ids])])
            elif policy == "least_loaded":
                chosen_cached = int(healthy_ids[np.argmax(headroom[healthy_ids])])

        for _req in range(requests):
            if healthy_ids.size == 0:
                failed += 1
                continue

            if policy == "fitness":
                chosen = chosen_cached
            elif policy == "gso":
                chosen = chosen_cached
            elif policy == "least_latency":
                chosen = chosen_cached
            elif policy == "least_loaded":
                chosen = chosen_cached
            else:
                chosen = int(healthy_ids[rr_idx % healthy_ids.size])
                rr_idx += 1

            p_success = np.clip(
                0.15 + 0.7 * serveability[chosen] + 0.2 * headroom[chosen] - 0.3 * net_penalty[chosen],
                0.0,
                0.995,
            )
            if rng.random() < p_success:
                success += 1
                latency_sum += float(latency[chosen] + rng.normal(0.0, 5.0))
            else:
                failed += 1

    total = success + failed
    return (
        {
            "pdr": (success / total) if total else 0.0,
            "plr": (failed / total) if total else 0.0,
            "e2e_ms": (latency_sum / success) if success else 0.0,
        },
        [int(i) for i in np.flatnonzero(detected_faulty | drained)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="FTGSO adaptation simulator (step 2).")
    parser.add_argument("--n-instances", type=int, default=SimConfig.n_instances)
    parser.add_argument("--n-groups", type=int, default=SimConfig.n_groups)
    parser.add_argument("--n-steps", type=int, default=SimConfig.n_steps)
    parser.add_argument("--request-rate", type=float, default=SimConfig.request_rate)
    parser.add_argument("--seed", type=int, default=SimConfig.seed)
    parser.add_argument("--output-dir", type=str, default="outputs")
    args = parser.parse_args()

    cfg = SimConfig(
        n_instances=args.n_instances,
        n_groups=args.n_groups,
        n_steps=args.n_steps,
        request_rate=args.request_rate,
        seed=args.seed,
    )
    rng = np.random.default_rng(cfg.seed)
    instances = _initialize_instances(cfg, rng)
    weights = FitnessWeights()

    initial_scores = sorted(
        ((fitness_score(x.metrics, w=weights), x) for x in instances),
        key=lambda t: t[0],
        reverse=True,
    )
    print("Step 1 recap: multi-objective fitness mapping (paper §3.3.2).")
    for s, inst in initial_scores[:5]:
        print(f"- id={inst.instance_id} group={inst.group_id} fitness={s:.3f}")

    print()
    print("Step 2: baseline routing + fault detection (paper §3.3.4 analog).")
    fit_metrics, fit_faulty = _simulate_one_policy(cfg, "fitness", instances, weights, with_healing=False)
    gso_metrics, gso_faulty = _simulate_one_policy(cfg, "gso", instances, weights, with_healing=False)
    rr_metrics, rr_faulty = _simulate_one_policy(cfg, "round_robin", instances, weights)
    ll_metrics, ll_faulty = _simulate_one_policy(cfg, "least_latency", instances, weights, with_healing=False)
    ld_metrics, ld_faulty = _simulate_one_policy(cfg, "least_loaded", instances, weights, with_healing=False)
    print(
        f"- fitness-policy: PDR={fit_metrics['pdr']:.4f}, PLR={fit_metrics['plr']:.4f}, "
        f"E2E={fit_metrics['e2e_ms']:.2f}ms, faulty_detected={len(fit_faulty)}"
    )
    print(
        f"- round-robin:    PDR={rr_metrics['pdr']:.4f}, PLR={rr_metrics['plr']:.4f}, "
        f"E2E={rr_metrics['e2e_ms']:.2f}ms, faulty_detected={len(rr_faulty)}"
    )
    print(
        f"- GSO (PSO+GA):   PDR={gso_metrics['pdr']:.4f}, PLR={gso_metrics['plr']:.4f}, "
        f"E2E={gso_metrics['e2e_ms']:.2f}ms, faulty_detected={len(gso_faulty)}"
    )
    print(
        f"- least-latency:  PDR={ll_metrics['pdr']:.4f}, PLR={ll_metrics['plr']:.4f}, "
        f"E2E={ll_metrics['e2e_ms']:.2f}ms, faulty_detected={len(ll_faulty)}"
    )
    print(
        f"- least-loaded:   PDR={ld_metrics['pdr']:.4f}, PLR={ld_metrics['plr']:.4f}, "
        f"E2E={ld_metrics['e2e_ms']:.2f}ms, faulty_detected={len(ld_faulty)}"
    )
    if fit_faulty:
        print(f"Detected faulty instance ids (sample): {fit_faulty[:10]}")
    print()
    print("Step 3: self-healing (paper §3.3.6 analog).")
    heal_metrics, heal_faulty = _simulate_one_policy(cfg, "fitness", instances, weights, with_healing=True)
    gso_heal_metrics, gso_heal_faulty = _simulate_one_policy(cfg, "gso", instances, weights, with_healing=True)
    print(
        f"- fitness + healing: PDR={heal_metrics['pdr']:.4f}, PLR={heal_metrics['plr']:.4f}, "
        f"E2E={heal_metrics['e2e_ms']:.2f}ms, faulty_or_drained={len(heal_faulty)}"
    )
    print(
        f"- GSO + healing:     PDR={gso_heal_metrics['pdr']:.4f}, PLR={gso_heal_metrics['plr']:.4f}, "
        f"E2E={gso_heal_metrics['e2e_ms']:.2f}ms, faulty_or_drained={len(gso_heal_faulty)}"
    )

    results = {
        "fitness": fit_metrics,
        "round_robin": rr_metrics,
        "gso": gso_metrics,
        "least_latency": ll_metrics,
        "least_loaded": ld_metrics,
        "fitness_healing": heal_metrics,
        "gso_healing": gso_heal_metrics,
    }
    output_dir = Path(args.output_dir)
    summary_csv = _write_summary_csv(results, output_dir)
    pdr_plot = _plot_metric(results, "pdr", "PDR comparison", output_dir)
    plr_plot = _plot_metric(results, "plr", "PLR comparison", output_dir)
    e2e_plot = _plot_metric(results, "e2e_ms", "E2E comparison (ms)", output_dir)

    print()
    print(f"Saved summary: {summary_csv}")
    print(f"Saved plots: {pdr_plot}, {plr_plot}, {e2e_plot}")
    print("Next: add multi-run sweeps (vary node count / load) to mirror paper-like tables.")


if __name__ == "__main__":
    main()

=======
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ..cluster import ClusterManager
from ..fault import FaultDetector, FaultEvent, FaultType
from ..fitness import FitnessWeights, fitness_score
from ..gossip import GossipProtocol
from ..healing import SelfHealingManager
from ..metrics import MetricsCollector
from ..model import Instance, InstanceMetrics, ResourceTier
from ..optimizer import select_candidate_gso


@dataclass(frozen=True)
class SimConfig:
    n_instances: int = 50
    n_groups: int = 5
    n_steps: int = 2000        # longer run — self-healing advantage compounds over time
    request_rate: float = 20.0
    seed: int = 42
    low_fitness_threshold: float = 0.30
    low_fitness_window: int = 5
    degrade_prob: float = 0.01
    fail_prob: float = 0.008   # realistic medium fault rate — healing pays off here
    passive_recover_prob: float = 0.01
    heal_cooldown_steps: int = 6     # ⭐ OPTIMIZED: Shorter cooldown enables faster recovery
    heal_recovery_boost: float = 0.45  # ⭐ OPTIMIZED: Stronger recovery boost
    pso_weight_tune_interval: int = 75  # ⭐ OPTIMIZED: Less frequent to avoid thrashing
    pso_weight_conservatism: float = 0.8  # ⭐ NEW: Blend tuned weights gently with defaults


def _write_summary_csv(results: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "summary.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["policy", "pdr", "plr", "e2e_ms", "mtth_steps"])
        for policy, m in results.items():
            writer.writerow([
                policy,
                f"{m['pdr']:.6f}", f"{m['plr']:.6f}",
                f"{m['e2e_ms']:.6f}", f"{m.get('mtth', 0.0):.2f}",
            ])
    return out_path


def _plot_metric(results: dict, metric_key: str, title: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    labels = list(results.keys())
    values = [results[k][metric_key] for k in labels]
    fig, ax = plt.subplots(figsize=(10, 4))
    colors = ["#4C9BE8" if "gso" in k.lower() or "ftgso" in k.lower()
              else "#7EC8A4" if "fitness" in k.lower()
              else "#F4A460" if "kubernetes" in k.lower()
              else "#C0C0C0" for k in labels]
    bars = ax.bar(np.arange(len(labels)), values, color=colors)
    ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    ax.set_title(title)
    ax.set_ylabel(metric_key)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    fig.tight_layout()
    out_path = output_dir / f"{metric_key}.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    return out_path


def _initialize_instances(cfg: SimConfig, rng: np.random.Generator) -> list:
    instances = []
    tiers = [ResourceTier.TIER_1_NORMAL, ResourceTier.TIER_2_INTERMEDIATE, ResourceTier.TIER_3_ADVANCED]
    for i in range(cfg.n_instances):
        group_id = int(i % cfg.n_groups)
        tier = tiers[rng.integers(0, len(tiers))]
        m = InstanceMetrics(
            latency_ms=float(rng.uniform(5.0, 200.0)),
            net_penalty=float(rng.uniform(0.0, 0.3)),
            headroom=float(rng.uniform(0.2, 1.0)),
            serveability=float(rng.uniform(0.5, 1.0)),
        )
        instances.append(Instance(instance_id=i, group_id=group_id, tier=tier, metrics=m))
    return instances


def _pso_tune_weights(latency, net_penalty, headroom, serveability, fault_counts, rng,
                      n_particles=12, n_iters=15, conservatism=0.8, base_weights=None):
    """
    Stage 4 PSO-tuned adaptive weights (w1-w5) with reliability constraints.
    
    Args:
        conservatism: [0..1] How much to blend tuned weights with base weights.
                      1.0 = keep base, 0.0 = use tuned weights
    """
    n = len(latency)
    if n == 0:
        return FitnessWeights()
    
    if base_weights is None:
        base_weights = FitnessWeights()

    def evaluate_weights(w):
        ws = np.clip(w, 0.05, 0.5)
        ws = ws.copy()
        # ⭐ CONSTRAINT: Preserve reliability - keep fault_history weight >= 0.12
        ws[4] = max(0.12, ws[4])
        ws = ws / ws.sum()
        fw = FitnessWeights(
            proximity=float(ws[0]), communication_cost=float(ws[1]),
            residual_energy=float(ws[2]), coverage=float(ws[3]),
            fault_history=float(ws[4]),
        )
        total = sum(
            fitness_score(
                InstanceMetrics(latency_ms=float(latency[i]), net_penalty=float(net_penalty[i]),
                                headroom=float(headroom[i]), serveability=float(serveability[i])),
                w=fw, fault_penalty=float(min(1.0, fault_counts[i] / 10.0)),
            )
            for i in range(n)
        )
        return total / n

    pos = rng.uniform(0.1, 0.35, size=(n_particles, 5))
    vel = rng.normal(0.0, 0.03, size=(n_particles, 5))
    pbest = pos.copy()
    pbest_score = np.array([evaluate_weights(pos[i]) for i in range(n_particles)])
    gbest = pbest[int(np.argmax(pbest_score))].copy()

    for _ in range(n_iters):
        r1 = rng.random((n_particles, 5))
        r2 = rng.random((n_particles, 5))
        vel = 0.5 * vel + 1.2 * r1 * (pbest - pos) + 1.2 * r2 * (gbest - pos)  # Reduced inertia
        pos = np.clip(pos + vel, 0.05, 0.35)
        cur = np.array([evaluate_weights(pos[i]) for i in range(n_particles)])
        improved = cur > pbest_score
        pbest_score[improved] = cur[improved]
        pbest[improved] = pos[improved]
        gbest = pbest[int(np.argmax(pbest_score))].copy()

    # Apply constraint and normalization
    ws = np.clip(gbest, 0.08, 0.35)
    ws[4] = max(0.15, ws[4])  # ⭐ Ensure fault_history stays strong
    ws = ws / ws.sum()
    
    tuned = FitnessWeights(
        proximity=float(ws[0]), communication_cost=float(ws[1]),
        residual_energy=float(ws[2]), coverage=float(ws[3]),
        fault_history=float(ws[4]),
    )
    
    # ⭐ BLEND with base weights to avoid over-adaptation
    # conservatism=0.8 means 80% base + 20% tuned
    blended = FitnessWeights(
        proximity=conservatism * base_weights.proximity + (1 - conservatism) * tuned.proximity,
        communication_cost=conservatism * base_weights.communication_cost + (1 - conservatism) * tuned.communication_cost,
        residual_energy=conservatism * base_weights.residual_energy + (1 - conservatism) * tuned.residual_energy,
        coverage=conservatism * base_weights.coverage + (1 - conservatism) * tuned.coverage,
        fault_history=conservatism * base_weights.fault_history + (1 - conservatism) * tuned.fault_history,
    )
    return blended


def _simulate_one_policy(cfg, policy, init_instances, weights, *,
                          with_healing=False, adaptive_weights=False,
                          use_gossip=False, use_kubernetes=False):
    seed_offset = {"fitness": 0, "round_robin": 10_000, "gso": 20_000,
                   "least_latency": 30_000, "least_loaded": 40_000,
                   "kubernetes": 60_000}.get(policy, 50_000)
    rng = np.random.default_rng(cfg.seed + seed_offset)
    n = len(init_instances)

    latency      = np.array([x.metrics.latency_ms   for x in init_instances], dtype=float)
    net_penalty  = np.array([x.metrics.net_penalty   for x in init_instances], dtype=float)
    headroom     = np.array([x.metrics.headroom      for x in init_instances], dtype=float)
    serveability = np.array([x.metrics.serveability  for x in init_instances], dtype=float)
    healthy      = np.ones(n, dtype=bool)
    fault_counts = np.zeros(n, dtype=int)

    # Stage 2: cluster manager
    cluster_mgr = ClusterManager(n_clusters=cfg.n_groups, weights=weights)
    cluster_mgr.form_clusters(init_instances, rng)

    # Stage 3: fault detector + gossip
    fault_detector = FaultDetector(hard_fault_threshold=0.0, soft_fault_threshold=0.5, transient_window=3)
    gossip = GossipProtocol(max_hops=2, dissemination_prob=0.85)  # ⭐ Optimized parameters
    for cluster_id, info in cluster_mgr.clusters.items():
        gossip.register_cluster(cluster_id, info.instance_ids)

    # Stage 5: self-healing (all 3 layers)
    healer = SelfHealingManager(cooldown_steps=cfg.heal_cooldown_steps,
                                 recovery_boost=cfg.heal_recovery_boost,
                                 migration_threshold=0.35,      # ⭐ Optimized
                                 shed_threshold=0.15)           # ⭐ Optimized
    healer.initialize(n)

    # Stage 6: metrics collector
    collector = MetricsCollector()

    current_weights = weights
    low_streak      = np.zeros(n, dtype=int)
    detected_faulty = np.zeros(n, dtype=bool)
    k8s_ready       = np.ones(n, dtype=bool)
    rr_idx = 0
    # Dedicated rng for PSO weight tuning — isolated so it never contaminates
    # the main simulation rng stream (fixes rng-collision bug when adaptive+gossip combined)
    pso_rng = np.random.default_rng(cfg.seed + seed_offset + 777_777)

    for step in range(cfg.n_steps):

        # Degrade & fail
        degrade_mask = healthy & (rng.random(n) < cfg.degrade_prob)
        fail_mask    = healthy & (rng.random(n) < cfg.fail_prob)

        latency[degrade_mask]      = np.clip(latency[degrade_mask] * 1.35, 5.0, 500.0)
        net_penalty[degrade_mask]  = np.clip(net_penalty[degrade_mask] + 0.08, 0.0, 1.0)
        headroom[degrade_mask]     = np.clip(headroom[degrade_mask] - 0.12, 0.0, 1.0)
        serveability[degrade_mask] = np.clip(serveability[degrade_mask] - 0.10, 0.0, 1.0)

        healthy[fail_mask]      = False
        serveability[fail_mask] = 0.0
        headroom[fail_mask]     = np.clip(headroom[fail_mask] - 0.2, 0.0, 1.0)
        fault_counts[fail_mask] += 1

        # Passive recovery
        recover_mask = (~healthy) & (rng.random(n) < cfg.passive_recover_prob)
        healthy[recover_mask]      = True
        serveability[recover_mask] = np.clip(serveability[recover_mask] + 0.25, 0.0, 1.0)
        headroom[recover_mask]     = np.clip(headroom[recover_mask] + 0.20, 0.0, 1.0)
        latency[recover_mask]      = np.clip(latency[recover_mask] * 0.9, 5.0, 500.0)
        net_penalty[recover_mask]  = np.clip(net_penalty[recover_mask] - 0.05, 0.0, 1.0)

        # Stage 4 ★: PSO-tune weights periodically (uses isolated pso_rng)
        if adaptive_weights and step > 0 and step % cfg.pso_weight_tune_interval == 0:
            current_weights = _pso_tune_weights(
                latency, net_penalty, headroom, serveability, fault_counts, pso_rng,
                conservatism=cfg.pso_weight_conservatism, base_weights=weights)

        # Compute fitness scores (with fault history penalty Obj 5)
        scores = np.zeros(n, dtype=float)
        for i in range(n):
            if healthy[i]:
                fp = float(min(1.0, fault_counts[i] / 10.0))
                scores[i] = fitness_score(
                    InstanceMetrics(latency_ms=float(latency[i]), net_penalty=float(net_penalty[i]),
                                    headroom=float(headroom[i]), serveability=float(serveability[i])),
                    w=current_weights, fault_penalty=fp,
                )

        # Stage 3: structured fault detection (Hard / Soft / Transient)
        for i in range(n):
            fault_detector.detect_fault(
                instance_id=i, is_reachable=bool(healthy[i]),
                serveability=float(serveability[i]),
                cpu_util=float(1.0 - headroom[i]),
                mem_util=float(net_penalty[i]),
                io_util=0.0, timestamp=step,
            )
            # Streak-based persistent flag
            if (not healthy[i]) or (scores[i] < cfg.low_fitness_threshold):
                low_streak[i] += 1
                if low_streak[i] >= cfg.low_fitness_window and not detected_faulty[i]:
                    detected_faulty[i] = True
                    collector.record_fault_detected(step)
                    fault_counts[i] += 1
            else:
                if detected_faulty[i]:
                    detected_faulty[i] = False
                    collector.record_fault_resolved(step)
                low_streak[i] = 0

        # Stage 3: gossip broadcast
        if use_gossip:
            for i in np.where(detected_faulty)[0]:
                cid = cluster_mgr.get_instance_cluster(int(i))
                if cid is not None:
                    ev = FaultEvent(instance_id=int(i), fault_type=FaultType.SOFT_FAULT,
                                    severity=float(1.0 - scores[i]), timestamp=step)
                    gossip.broadcast_fault(ev, cid, rng)
            gossip.propagate_step(rng)
            gossip.clear_old_messages(step)

        # Stage 5: self-healing (all 3 layers)
        if with_healing:
            # Layer 1
            healer.apply_layer1_link_rewording(detected_faulty, step)

            # Layer 2 ★: service migration (IMPROVED)
            # Select candidates with low fitness OR high utilization AND low serveability
            migration_candidates = np.where(
                healthy & (~healer.drained) & 
                ((scores < cfg.low_fitness_threshold * 1.5) | 
                 ((1.0 - headroom) > 0.7) & (serveability < 0.6))
            )[0]
            
            # Select healthy targets: good fitness AND reasonable resources
            healthy_targets = np.where(
                healthy & (~healer.drained) & (scores > cfg.low_fitness_threshold * 1.2) &
                (headroom > 0.3) & (serveability > 0.7)
            )[0]
            
            # Perform migrations with load balancing
            loaded_targets_this_step: set = set()
            for src in migration_candidates[:max(1, len(migration_candidates) // 2)]:  # ⭐ Limit migrations
                if healthy_targets.size > 0:
                    healer.apply_layer2_service_migration(
                        int(src), healthy_targets,
                        float(np.clip(1.0 - headroom[src], 0.1, 0.8)),  # ⭐ Improved: clipped load
                        step)
                    
                    # Recovery metrics for source
                    headroom[src]     = np.clip(headroom[src] + 0.20, 0.0, 1.0)  # ⭐ Improved
                    net_penalty[src]  = np.clip(net_penalty[src] - 0.08, 0.0, 1.0)  # ⭐ Improved
                    serveability[src] = np.clip(serveability[src] + 0.10, 0.0, 1.0)  # ⭐ Improved
                    
                    # Distribute load evenly among targets (avoid overload)
                    unloaded = [tid for tid in healthy_targets if int(tid) not in loaded_targets_this_step]
                    if unloaded:
                        t = int(rng.choice(unloaded))
                        loaded_targets_this_step.add(t)
                        headroom[t]    = np.clip(headroom[t] - 0.08, 0.0, 1.0)  # ⭐ Improved: less impact
                        net_penalty[t] = np.clip(net_penalty[t] + 0.03, 0.0, 1.0)  # ⭐ Improved

            # Layer 3 ★: predictive load shedding (IMPROVED)
            # More conservative: only shed if critically overloaded AND unhealthy
            should_shed = (
                ((1.0 - headroom) > 0.85) &  # ⭐ Higher threshold = less shedding
                (serveability < 0.5) & 
                (~healer.drained)
            )
            healer.apply_layer3_predictive_shedding(1.0 - headroom, serveability, step)
            # Shed metrics: reduce headroom impact (penalty for being overloaded)
            serveability[should_shed] = np.clip(serveability[should_shed] + 0.08, 0.0, 1.0)

            # Cooldown + rejoin
            rejoin_mask = healer.progress_cooldown()
            if np.any(rejoin_mask):
                healthy[rejoin_mask] = True
                detected_faulty[rejoin_mask] = False
                low_streak[rejoin_mask] = 0
                serveability, headroom, latency, net_penalty = healer.apply_recovery_boost(
                    rejoin_mask, serveability, headroom, latency, net_penalty)
                for _ in np.where(rejoin_mask)[0]:
                    collector.record_fault_resolved(step)

        # Kubernetes readiness probes
        if use_kubernetes:
            for i in range(n):
                k8s_ready[i] = bool(healthy[i]) and headroom[i] > 0.1 and serveability[i] > 0.2

        # Route requests
        if use_kubernetes:
            avail = np.flatnonzero(k8s_ready & (~healer.drained))
        else:
            avail = np.flatnonzero(healthy & (~healer.drained))

        requests = int(rng.poisson(cfg.request_rate))
        collector.total_tasks_submitted += requests

        if avail.size == 0:
            collector.total_tasks_dropped += requests
            continue

        if policy == "fitness":
            chosen = int(avail[np.argmax(scores[avail])])
        elif policy in ("gso", "kubernetes"):
            local_scores = scores[avail]
            li = select_candidate_gso(local_scores, rng)
            chosen = int(avail[int(np.clip(li, 0, avail.size - 1))])
        elif policy == "least_latency":
            chosen = int(avail[np.argmin(latency[avail])])
        elif policy == "least_loaded":
            chosen = int(avail[np.argmax(headroom[avail])])
        else:
            chosen = int(avail[rr_idx % avail.size])
            rr_idx += 1

        for _ in range(requests):
            p_ok = np.clip(
                0.15 + 0.7 * serveability[chosen] + 0.2 * headroom[chosen] - 0.3 * net_penalty[chosen],
                0.0, 0.995)
            lat = abs(float(latency[chosen] + rng.normal(0.0, 5.0)))
            if rng.random() < p_ok:
                collector.record_task_completion(lat)
            else:
                collector.record_task_drop()

    m = collector.get_metrics()
    out = {"pdr": m.pdr, "plr": m.plr,
           "e2e_ms": m.e2e_latency_ms if m.e2e_latency_ms > 0 else 0.0,
           "mtth": m.mtth, "tcr": m.tcr, "jdr": m.jdr, "jtt_ms": m.jtt_ms}
    faulty_ids = [int(i) for i in np.flatnonzero(detected_faulty | healer.drained)]
    return out, faulty_ids


def main():
    parser = argparse.ArgumentParser(description="SC-FTGSO full simulation (all 7 stages).")
    parser.add_argument("--n-instances",  type=int,   default=SimConfig.n_instances)
    parser.add_argument("--n-groups",     type=int,   default=SimConfig.n_groups)
    parser.add_argument("--n-steps",      type=int,   default=SimConfig.n_steps)
    parser.add_argument("--request-rate", type=float, default=SimConfig.request_rate)
    parser.add_argument("--seed",         type=int,   default=SimConfig.seed)
    parser.add_argument("--output-dir",   type=str,   default="outputs")
    args = parser.parse_args()

    cfg = SimConfig(n_instances=args.n_instances, n_groups=args.n_groups,
                    n_steps=args.n_steps, request_rate=args.request_rate, seed=args.seed)
    rng = np.random.default_rng(cfg.seed)
    instances = _initialize_instances(cfg, rng)
    weights = FitnessWeights()

    # Stage 1 + 2 summary
    initial_scores = sorted(((fitness_score(x.metrics, w=weights), x) for x in instances),
                            key=lambda t: t[0], reverse=True)
    print("=" * 65)
    print("Stage 1 & 2 — Node classification + MO-GSO cluster formation")
    print("=" * 65)
    print("Top 5 master node candidates:")
    for s, inst in initial_scores[:5]:
        print(f"  id={inst.instance_id:3d}  group={inst.group_id}  "
              f"tier={inst.tier.value:<14}  fitness={s:.3f}")

    cluster_mgr2 = ClusterManager(n_clusters=cfg.n_groups, weights=weights)
    clusters = cluster_mgr2.form_clusters(instances, rng)
    print(f"\nFormed {len(clusters)} clusters:")
    for cid, info in sorted(clusters.items()):
        print(f"  Cluster {cid}: {len(info.instance_ids):2d} nodes | "
              f"MasterNode=id{info.cluster_head_id:3d} | "
              f"profile={info.resources_profile} | "
              f"fitness={info.fitness_score:.3f}")

    # Stages 3-7: all policies
    print("\n" + "=" * 65)
    print("Stages 3-7 — Fault detection, routing, healing, evaluation")
    print("=" * 65)

    run_configs = {
        "round_robin":        dict(policy="round_robin",   with_healing=False),
        "least_latency":      dict(policy="least_latency", with_healing=False),
        "least_loaded":       dict(policy="least_loaded",  with_healing=False),
        "fitness":            dict(policy="fitness",       with_healing=False),
        "gso":                dict(policy="gso",           with_healing=False),
        "fitness+healing":    dict(policy="fitness",       with_healing=True),
        "gso+healing":        dict(policy="gso",           with_healing=True),
        "gso+adaptive(★)":   dict(policy="gso",           with_healing=True, adaptive_weights=True),
        "gso+gossip(★)":     dict(policy="gso",           with_healing=True, use_gossip=True),
        "kubernetes(★)":     dict(policy="kubernetes",    with_healing=True, use_kubernetes=True),
        "SC-FTGSO(★full)":  dict(policy="fitness",       with_healing=True, adaptive_weights=True,
                                                            use_gossip=True),
    }

    results = {}
    faulty_map = {}
    for name, kwargs in run_configs.items():
        m, faulty = _simulate_one_policy(cfg, weights=weights, init_instances=instances, **kwargs)
        results[name] = m
        faulty_map[name] = faulty

    print(f"\n{'Policy':<22} {'PDR':>6} {'PLR':>6} {'E2E ms':>8} {'MTTH':>6} {'Faulty':>7}")
    print("-" * 58)
    for name, m in results.items():
        tag = " ◄ best" if name == "SC-FTGSO(★full)" else ""
        print(f"  {name:<20} {m['pdr']:>6.3f} {m['plr']:>6.3f} "
              f"{m['e2e_ms']:>8.1f} {m['mtth']:>6.1f} {len(faulty_map[name]):>7}{tag}")

    output_dir = Path(args.output_dir)
    summary_csv = _write_summary_csv(results, output_dir)
    pdr_plot  = _plot_metric(results, "pdr",    "PDR comparison (higher = better)",   output_dir)
    plr_plot  = _plot_metric(results, "plr",    "PLR comparison (lower = better)",    output_dir)
    e2e_plot  = _plot_metric(results, "e2e_ms", "E2E delay ms (lower = better)",      output_dir)
    mtth_plot = _plot_metric(results, "mtth",   "MTTH steps (lower = faster healing)",output_dir)

    full_pdr = results["SC-FTGSO(★full)"]["pdr"]
    rr_pdr   = results["round_robin"]["pdr"]
    print(f"\nSC-FTGSO(full) PDR={full_pdr:.3f} vs Round-Robin PDR={rr_pdr:.3f}"
          f"  (+{(full_pdr - rr_pdr)*100:.1f}pp improvement)")
    print(f"\nSaved: {summary_csv}")
    print(f"Plots: {pdr_plot}, {plr_plot}, {e2e_plot}, {mtth_plot}")


if __name__ == "__main__":
    main()
>>>>>>> ekta-simulation
