"""Seeded random flow requests (two priority classes)."""
from __future__ import annotations

import random

from .model import BYTE, Flow

# class 0: control traffic (small frames, tight deadlines)
# class 1: stream traffic (AVB-like: large frames, looser deadlines)
PROFILES = {
    0: dict(frame=(64, 256), periods=(250e-6, 500e-6, 1e-3), frames_per_burst=(1, 1),
            deadline=(100e-6, 500e-6)),
    1: dict(frame=(500, 1500), periods=(125e-6, 250e-6, 500e-6, 1e-3), frames_per_burst=(1, 2),
            deadline=(500e-6, 2e-3)),
}


def random_flows(net, n: int, seed: int = 0, p_high: float = 0.3, start_id: int = 0) -> list:
    rng = random.Random(seed)
    es = net.end_stations
    out = []
    for k in range(n):
        src, dst = rng.sample(es, 2)
        prio = 0 if rng.random() < p_high else 1
        pr = PROFILES[prio]
        L = rng.randint(*pr["frame"]) * BYTE
        period = rng.choice(pr["periods"])
        b = L * rng.randint(*pr["frames_per_burst"])
        out.append(Flow(id=start_id + k, src=src, dst=dst, b=b, r=L / period, L=L, prio=prio,
                        deadline=rng.uniform(*pr["deadline"])))
    return out
