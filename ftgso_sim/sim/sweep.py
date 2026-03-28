<<<<<<< HEAD
from __future__ import annotations

import argparse
import os
from dataclasses import replace
from pathlib import Path

# Important: set matplotlib cache/config dirs before importing pyplot.
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", ".mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", ".cache")

import csv

import numpy as np
import matplotlib.pyplot as plt

from ..fitness import FitnessWeights
from .step2 import SimConfig, _initialize_instances, _simulate_one_policy


def _write_agg_csv(agg: dict[str, dict[str, dict[str, float]]], output_dir: Path) -> Path:
    """
    agg[metric_key][policy] = {"mean": x, "std": y}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "summary_agg.csv"
    metrics = ["pdr", "plr", "e2e_ms"]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "policy", "mean", "std"])
        for metric in metrics:
            for policy, s in agg[metric].items():
                writer.writerow([metric, policy, f"{s['mean']:.6f}", f"{s['std']:.6f}"])
    return out_path


def _write_by_scenario_csv(
    scenario_agg: dict[tuple[int, str], dict[str, dict[str, dict[str, float]]]],
    output_dir: Path,
) -> Path:
    """
    scenario_agg[(n_instances, request_rate_str)][metric][policy] = {"mean": x, "std": y}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "summary_by_scenario.csv"
    metrics = ["pdr", "plr", "e2e_ms"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["n_instances", "request_rate", "metric", "policy", "mean", "std"])
        for (n_instances, req_rate), per_metric in sorted(scenario_agg.items(), key=lambda x: (x[0][0], float(x[0][1]))):
            for metric in metrics:
                for policy, s in per_metric[metric].items():
                    writer.writerow(
                        [str(n_instances), req_rate, metric, policy, f"{s['mean']:.6f}", f"{s['std']:.6f}"]
                    )
    return out_path


def _plot_means(agg: dict[str, dict[str, dict[str, float]]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = ["pdr", "plr", "e2e_ms"]

    for metric in metrics:
        policies = list(agg[metric].keys())
        values = [agg[metric][p]["mean"] for p in policies]
        x = np.arange(len(policies))

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(x, values)
        ax.set_title(f"Mean {metric} across sweep")
        ax.set_ylabel(metric)
        ax.set_xticks(x)
        ax.set_xticklabels(policies, rotation=20, ha="right")
        fig.tight_layout()
        fig.savefig(output_dir / f"mean_{metric}.png", dpi=160)
        plt.close(fig)


def _plot_by_scenario(
    scenario_agg: dict[tuple[int, str], dict[str, dict[str, dict[str, float]]]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for (n_instances, req_rate), per_metric in scenario_agg.items():
        tag = f"n{n_instances}_r{req_rate.replace('.', 'p')}"
        for metric in ["pdr", "plr", "e2e_ms"]:
            policies = list(per_metric[metric].keys())
            values = [per_metric[metric][p]["mean"] for p in policies]
            errs = [per_metric[metric][p]["std"] for p in policies]
            x = np.arange(len(policies))

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.bar(x, values, yerr=errs, capsize=4)
            ax.set_title(f"{metric} for n={n_instances}, rate={req_rate}")
            ax.set_ylabel(metric)
            ax.set_xticks(x)
            ax.set_xticklabels(policies, rotation=20, ha="right")
            fig.tight_layout()
            fig.savefig(output_dir / f"{tag}_{metric}.png", dpi=160)
            plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="FTGSO adaptation multi-run sweep (Stage 5).")
    parser.add_argument("--n-instances", type=int, nargs="+", default=[50, 100])
    parser.add_argument("--request-rates", type=float, nargs="+", default=[10.0, 20.0])
    parser.add_argument("--n-seeds", type=int, default=5)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--n-steps", type=int, default=300)
    parser.add_argument("--degrade-prob", type=float, default=SimConfig.degrade_prob)
    parser.add_argument("--fail-prob", type=float, default=SimConfig.fail_prob)
    parser.add_argument("--output-dir", type=str, default="sweep_outputs")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    per_run_csv = output_dir / "runs.csv"
    output_dir.mkdir(parents=True, exist_ok=True)

    policies = [
        "round_robin",
        "least_latency",
        "least_loaded",
        "fitness",
        "gso",
        "fitness_healing",
        "gso_healing",
    ]
    metrics_keys = ["pdr", "plr", "e2e_ms"]

    runs_rows: list[list[str]] = []

    for n_instances in args.n_instances:
        for request_rate in args.request_rates:
            for sidx in range(args.n_seeds):
                seed = args.seed_start + sidx
                cfg = replace(
                    SimConfig(),
                    n_instances=n_instances,
                    request_rate=request_rate,
                    n_steps=args.n_steps,
                    seed=seed,
                    degrade_prob=args.degrade_prob,
                    fail_prob=args.fail_prob,
                )
                rng = np.random.default_rng(cfg.seed)
                instances = _initialize_instances(cfg, rng)
                weights = FitnessWeights()

                # Baselines / policies (same as step2).
                results = {
                    "fitness": _simulate_one_policy(cfg, "fitness", instances, weights, with_healing=False)[0],
                    "round_robin": _simulate_one_policy(cfg, "round_robin", instances, weights, with_healing=False)[0],
                    "least_latency": _simulate_one_policy(
                        cfg, "least_latency", instances, weights, with_healing=False
                    )[0],
                    "least_loaded": _simulate_one_policy(
                        cfg, "least_loaded", instances, weights, with_healing=False
                    )[0],
                    "gso": _simulate_one_policy(cfg, "gso", instances, weights, with_healing=False)[0],
                    "fitness_healing": _simulate_one_policy(cfg, "fitness", instances, weights, with_healing=True)[0],
                    "gso_healing": _simulate_one_policy(cfg, "gso", instances, weights, with_healing=True)[0],
                }

                for policy in policies:
                    m = results[policy]
                    runs_rows.append(
                        [
                            str(n_instances),
                            f"{request_rate:.3f}",
                            str(seed),
                            policy,
                            f"{m['pdr']:.6f}",
                            f"{m['plr']:.6f}",
                            f"{m['e2e_ms']:.6f}",
                        ]
                    )

    with per_run_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["n_instances", "request_rate", "seed", "policy", "pdr", "plr", "e2e_ms"])
        writer.writerows(runs_rows)

    # Overall aggregate across all combinations (retained from Stage 5).
    agg_values: dict[str, dict[str, list[float]]] = {m: {p: [] for p in policies} for m in metrics_keys}
    for row in runs_rows:
        policy = row[3]
        agg_values["pdr"][policy].append(float(row[4]))
        agg_values["plr"][policy].append(float(row[5]))
        agg_values["e2e_ms"][policy].append(float(row[6]))

    agg: dict[str, dict[str, dict[str, float]]] = {m: {} for m in metrics_keys}
    for metric in metrics_keys:
        for policy in policies:
            vals = np.array(agg_values[metric][policy], dtype=float)
            agg[metric][policy] = {"mean": float(np.mean(vals)), "std": float(np.std(vals))}

    # New Stage 6 aggregate: by (n_instances, request_rate) scenario.
    scenario_values: dict[tuple[int, str], dict[str, dict[str, list[float]]]] = {}
    for row in runs_rows:
        n_instances = int(row[0])
        req_rate = row[1]
        policy = row[3]
        key = (n_instances, req_rate)
        if key not in scenario_values:
            scenario_values[key] = {m: {p: [] for p in policies} for m in metrics_keys}
        scenario_values[key]["pdr"][policy].append(float(row[4]))
        scenario_values[key]["plr"][policy].append(float(row[5]))
        scenario_values[key]["e2e_ms"][policy].append(float(row[6]))

    scenario_agg: dict[tuple[int, str], dict[str, dict[str, dict[str, float]]]] = {}
    for key, per_metric in scenario_values.items():
        scenario_agg[key] = {m: {} for m in metrics_keys}
        for metric in metrics_keys:
            for policy in policies:
                vals = np.array(per_metric[metric][policy], dtype=float)
                scenario_agg[key][metric][policy] = {
                    "mean": float(np.mean(vals)),
                    "std": float(np.std(vals)),
                }

    summary_csv = _write_agg_csv(agg, output_dir)
    summary_by_scenario_csv = _write_by_scenario_csv(scenario_agg, output_dir)
    _plot_means(agg, output_dir)
    _plot_by_scenario(scenario_agg, output_dir)

    print(f"Saved per-run results: {per_run_csv}")
    print(f"Saved aggregated summary: {summary_csv}")
    print(f"Saved per-scenario summary: {summary_by_scenario_csv}")
    print(f"Saved plots in: {output_dir}")


if __name__ == "__main__":
    main()

=======
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", ".mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", ".cache")

import numpy as np
import matplotlib.pyplot as plt

from ..fitness import FitnessWeights
from .step2 import SimConfig, _initialize_instances, _simulate_one_policy

POLICIES = {
    "round_robin":      dict(policy="round_robin",   with_healing=False),
    "gso":              dict(policy="gso",           with_healing=False),
    "fitness+healing":  dict(policy="fitness",       with_healing=True),
    "gso+healing":      dict(policy="gso",           with_healing=True),
    "SC-FTGSO(full)":   dict(policy="gso",           with_healing=True,
                              adaptive_weights=True, use_gossip=True),
}


def main():
    parser = argparse.ArgumentParser(description="SC-FTGSO parameter sweep.")
    parser.add_argument("--output-dir", type=str, default="sweep_outputs")
    parser.add_argument("--n-repeats",  type=int, default=5)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    node_counts   = [20, 50, 100]
    request_rates = [10.0, 20.0]
    seeds         = list(range(args.n_repeats))
    weights       = FitnessWeights()

    all_rows = []
    # agg[metric][policy] = list of values across all runs
    agg: dict = {m: {p: [] for p in POLICIES} for m in ["pdr", "plr", "e2e_ms", "mtth"]}

    for n_inst in node_counts:
        for req_rate in request_rates:
            for seed in seeds:
                cfg = SimConfig(n_instances=n_inst, n_steps=400,
                                request_rate=req_rate, seed=seed)
                rng = np.random.default_rng(seed)
                instances = _initialize_instances(cfg, rng)

                for pol_name, kwargs in POLICIES.items():
                    m, _ = _simulate_one_policy(cfg, weights=weights,
                                                 init_instances=instances, **kwargs)
                    row = dict(n_instances=n_inst, request_rate=req_rate,
                               seed=seed, policy=pol_name,
                               pdr=m["pdr"], plr=m["plr"],
                               e2e_ms=m["e2e_ms"], mtth=m["mtth"])
                    all_rows.append(row)
                    for metric in ["pdr", "plr", "e2e_ms", "mtth"]:
                        agg[metric][pol_name].append(m[metric])

    # Save raw runs CSV
    runs_path = output_dir / "runs.csv"
    with runs_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["n_instances","request_rate","seed",
                                                "policy","pdr","plr","e2e_ms","mtth"])
        writer.writeheader()
        writer.writerows(all_rows)

    # Save aggregated CSV
    agg_path = output_dir / "summary_agg.csv"
    with agg_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "policy", "mean", "std"])
        for metric, pol_vals in agg.items():
            for pol_name, vals in pol_vals.items():
                writer.writerow([metric, pol_name,
                                  f"{np.mean(vals):.6f}", f"{np.std(vals):.6f}"])

    # Plot mean metrics
    for metric, pol_vals in agg.items():
        labels = list(pol_vals.keys())
        means  = [np.mean(pol_vals[p]) for p in labels]
        stds   = [np.std(pol_vals[p])  for p in labels]
        fig, ax = plt.subplots(figsize=(9, 4))
        x = np.arange(len(labels))
        ax.bar(x, means, yerr=stds, capsize=4)
        ax.set_title(f"Mean {metric} across sweep (n_nodes × request_rate × seeds)")
        ax.set_ylabel(metric)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=25, ha="right")
        fig.tight_layout()
        fig.savefig(output_dir / f"mean_{metric}.png", dpi=160)
        plt.close(fig)

    print(f"Saved runs:        {runs_path}")
    print(f"Saved aggregated:  {agg_path}")
    print(f"Plots saved to:    {output_dir}/")


if __name__ == "__main__":
    main()
>>>>>>> ekta-simulation
