from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

# Keep matplotlib in non-interactive mode for terminal runs.
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", ".mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", ".cache")

import matplotlib.pyplot as plt
import numpy as np

from ..fitness import FitnessWeights
from .step2 import SimConfig, _initialize_instances, _simulate_one_policy


def _plot_metric(results: dict[str, dict[str, float]], metric_key: str, title: str, output_dir: Path) -> Path:
    labels = list(results.keys())
    values = [results[k][metric_key] for k in labels]
    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(x, values)
    ax.set_title(title)
    ax.set_ylabel(metric_key)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    fig.tight_layout()

    out_path = output_dir / f"ablation_{metric_key}.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="FTGSO Stage 8 ablation runner.")
    parser.add_argument("--n-instances", type=int, default=80)
    parser.add_argument("--n-groups", type=int, default=5)
    parser.add_argument("--n-steps", type=int, default=500)
    parser.add_argument("--request-rate", type=float, default=20.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default="ablation_outputs")
    args = parser.parse_args()

    cfg = SimConfig(
        n_instances=args.n_instances,
        n_groups=args.n_groups,
        n_steps=args.n_steps,
        request_rate=args.request_rate,
        seed=args.seed,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(cfg.seed)
    instances = _initialize_instances(cfg, rng)
    weights = FitnessWeights()

    # Stage 8 ablation definitions:
    # - score_only: objective score routing (no healing)
    # - gso_only: PSO+GA hybrid routing (no healing)
    # - healing_only: simple round-robin routing with healing enabled
    # - full_ftgso_healing: GSO routing with healing enabled
    results = {
        "score_only": _simulate_one_policy(cfg, "fitness", instances, weights, with_healing=False)[0],
        "gso_only": _simulate_one_policy(cfg, "gso", instances, weights, with_healing=False)[0],
        "healing_only": _simulate_one_policy(cfg, "round_robin", instances, weights, with_healing=True)[0],
        "full_ftgso_healing": _simulate_one_policy(cfg, "gso", instances, weights, with_healing=True)[0],
    }

    out_csv = output_dir / "ablation_summary.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "pdr", "plr", "e2e_ms"])
        for name, m in results.items():
            writer.writerow([name, f"{m['pdr']:.6f}", f"{m['plr']:.6f}", f"{m['e2e_ms']:.6f}"])

    pdr_plot = _plot_metric(results, "pdr", "Ablation: PDR", output_dir)
    plr_plot = _plot_metric(results, "plr", "Ablation: PLR", output_dir)
    e2e_plot = _plot_metric(results, "e2e_ms", "Ablation: E2E (ms)", output_dir)

    print(f"Saved ablation summary: {out_csv}")
    print(f"Saved plots: {pdr_plot}, {plr_plot}, {e2e_plot}")


if __name__ == "__main__":
    main()

