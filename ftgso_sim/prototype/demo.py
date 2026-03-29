from __future__ import annotations

import argparse
import time

from .healer import heal_once
from .router import LocalRouter


def main() -> None:
    parser = argparse.ArgumentParser(description="Local runnable FTGSO prototype demo.")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--requests", type=int, default=300)
    parser.add_argument("--dispatch-interval-ms", type=float, default=3.0)
    parser.add_argument("--crash-prob", type=float, default=0.02)
    parser.add_argument("--mode", choices=["fitness", "gso"], default="gso")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    router = LocalRouter(
        n_workers=args.workers,
        use_gso=(args.mode == "gso"),
        crash_prob=args.crash_prob,
        seed=args.seed,
    )
    router.start()

    sent = 0
    failed_route = 0
    completed = 0
    e2e_sum = 0.0
    restarted_total = 0

    try:
        while sent < args.requests:
            ok = router.route(sent)
            if ok:
                sent += 1
            else:
                failed_route += 1

            for _job_id, _wid, e2e_ms in router.drain_results():
                completed += 1
                e2e_sum += e2e_ms

            restarted_total += heal_once(router)
            time.sleep(args.dispatch_interval_ms / 1000.0)

        # Drain remaining results briefly.
        deadline = time.time() + 3.0
        while time.time() < deadline and completed < sent:
            for _job_id, _wid, e2e_ms in router.drain_results():
                completed += 1
                e2e_sum += e2e_ms
            restarted_total += heal_once(router)
            time.sleep(0.01)
    finally:
        router.shutdown()

    total_attempted = sent + failed_route
    plr = (total_attempted - completed) / total_attempted if total_attempted else 0.0
    pdr = completed / total_attempted if total_attempted else 0.0
    e2e = e2e_sum / completed if completed else 0.0

    print("Local prototype run complete.")
    print(
        f"mode={args.mode} workers={args.workers} requests={args.requests} "
        f"crash_prob={args.crash_prob:.3f}"
    )
    print(f"PDR={pdr:.4f}, PLR={plr:.4f}, E2E={e2e:.2f}ms, restarts={restarted_total}")


if __name__ == "__main__":
    main()

