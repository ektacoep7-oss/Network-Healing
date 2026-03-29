from __future__ import annotations

import time
from dataclasses import dataclass
from multiprocessing import Process, Queue

import numpy as np

from ..fitness import FitnessWeights, fitness_score
from ..model import InstanceMetrics
from ..optimizer import select_candidate_gso
from .worker import worker_main


@dataclass
class WorkerHandle:
    worker_id: int
    in_q: Queue
    proc: Process
    latency_ms: float
    net_penalty: float
    headroom: float
    serveability: float


class LocalRouter:
    def __init__(self, n_workers: int, *, use_gso: bool, crash_prob: float, seed: int = 42) -> None:
        self.n_workers = n_workers
        self.use_gso = use_gso
        self.crash_prob = crash_prob
        self.rng = np.random.default_rng(seed)
        self.weights = FitnessWeights()
        self.result_q: Queue = Queue()
        self.workers: dict[int, WorkerHandle] = {}
        self._rr = 0

    def start(self) -> None:
        for wid in range(self.n_workers):
            self._spawn_worker(wid)

    def _spawn_worker(self, wid: int) -> None:
        in_q: Queue = Queue()
        latency_ms = float(self.rng.uniform(8.0, 80.0))
        wh = WorkerHandle(
            worker_id=wid,
            in_q=in_q,
            proc=Process(
                target=worker_main,
                args=(wid, in_q, self.result_q, latency_ms, self.crash_prob),
                daemon=True,
            ),
            latency_ms=latency_ms,
            net_penalty=float(self.rng.uniform(0.0, 0.2)),
            headroom=float(self.rng.uniform(0.4, 1.0)),
            serveability=float(self.rng.uniform(0.6, 1.0)),
        )
        wh.proc.start()
        self.workers[wid] = wh

    def _healthy_ids(self) -> list[int]:
        return [wid for wid, wh in self.workers.items() if wh.proc.is_alive()]

    def pick_worker(self) -> int | None:
        healthy = self._healthy_ids()
        if not healthy:
            return None

        if self.use_gso:
            scores = []
            for wid in healthy:
                wh = self.workers[wid]
                scores.append(
                    fitness_score(
                        InstanceMetrics(
                            latency_ms=wh.latency_ms,
                            net_penalty=wh.net_penalty,
                            headroom=wh.headroom,
                            serveability=wh.serveability,
                        ),
                        w=self.weights,
                    )
                )
            idx = select_candidate_gso(np.array(scores, dtype=float), self.rng)
            return healthy[int(np.clip(idx, 0, len(healthy) - 1))]

        # Greedy score-based fallback.
        best = None
        best_s = -1.0
        for wid in healthy:
            wh = self.workers[wid]
            s = fitness_score(
                InstanceMetrics(
                    latency_ms=wh.latency_ms,
                    net_penalty=wh.net_penalty,
                    headroom=wh.headroom,
                    serveability=wh.serveability,
                ),
                w=self.weights,
            )
            if s > best_s:
                best_s = s
                best = wid
        return best

    def route(self, job_id: int) -> bool:
        wid = self.pick_worker()
        if wid is None:
            return False
        self.workers[wid].in_q.put((job_id, time.time()))
        return True

    def drain_results(self) -> list[tuple[int, int, float]]:
        items: list[tuple[int, int, float]] = []
        while True:
            try:
                job_id, wid, ts_submit, ts_done, ok = self.result_q.get_nowait()
            except Exception:
                break
            if ok:
                e2e_ms = (ts_done - ts_submit) * 1000.0
                items.append((job_id, wid, e2e_ms))

                # Lightweight online metric updates.
                wh = self.workers[wid]
                wh.latency_ms = 0.85 * wh.latency_ms + 0.15 * e2e_ms
                wh.headroom = float(np.clip(wh.headroom - 0.005 + self.rng.uniform(-0.01, 0.02), 0.0, 1.0))
                wh.serveability = float(np.clip(wh.serveability + self.rng.uniform(-0.01, 0.01), 0.0, 1.0))
        return items

    def restart_dead(self) -> int:
        restarted = 0
        for wid, wh in list(self.workers.items()):
            if not wh.proc.is_alive():
                self._spawn_worker(wid)
                restarted += 1
        return restarted

    def shutdown(self) -> None:
        for wh in self.workers.values():
            if wh.proc.is_alive():
                wh.in_q.put(None)
        for wh in self.workers.values():
            if wh.proc.is_alive():
                wh.proc.join(timeout=1.0)

