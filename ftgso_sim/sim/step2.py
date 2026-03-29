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

