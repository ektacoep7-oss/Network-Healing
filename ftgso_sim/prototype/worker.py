from __future__ import annotations

import os
import random
import time
from multiprocessing import Queue


def worker_main(
    worker_id: int,
    in_q: Queue,
    out_q: Queue,
    base_latency_ms: float,
    crash_prob: float,
) -> None:
    rng = random.Random(worker_id * 100_003 + int(time.time()))
    while True:
        msg = in_q.get()
        if msg is None:
            break
        job_id, ts_submit = msg

        # Simulate transient worker crash (process dies unexpectedly).
        if rng.random() < crash_prob:
            os._exit(1)

        jitter = rng.uniform(0.6, 1.5)
        time.sleep((base_latency_ms * jitter) / 1000.0)
        out_q.put((job_id, worker_id, ts_submit, time.time(), True))

