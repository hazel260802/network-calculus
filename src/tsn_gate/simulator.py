"""
Packet-level discrete-event simulator used as a sanity check of the bounds.
"""
from __future__ import annotations

import heapq
import random
from collections import deque


def simulate(net, flows: dict, paths: dict, horizon: float, seed: int = 0) -> dict:
    """Returns fid observed end-to-end delay."""
    rng = random.Random(seed)
    C, tp = net.C, net.t_proc
    events = []   # (time, seq, kind, payload)
    seq = 0

    def push(t, kind, payload):
        nonlocal seq
        heapq.heappush(events, (t, seq, kind, payload))
        seq += 1

    for f, fl in flows.items():
        t0 = rng.uniform(0, fl.L / fl.r) if fl.r > 0 else 0.0
        n_burst = int(fl.b // fl.L)
        k = 0
        while True:
            t = t0 if k < n_burst else t0 + (k - n_burst + 1) * fl.L / fl.r
            if t > horizon or (fl.r == 0 and k >= n_burst):
                break
            push(t, "arrive", (f, 0, t))          # (flow, hop, creation time)
            k += 1

    queues = {}    # port -> {prio: deque}
    busy = {}      # port -> bool
    worst = {f: 0.0 for f in flows}

    def start(p, now):
        qs = queues.get(p)
        if not qs or busy.get(p):
            return
        for prio in sorted(qs):
            if qs[prio]:
                pkt = qs[prio].popleft()
                busy[p] = True
                push(now + flows[pkt[0]].L / C, "done", (p, pkt))
                return

    while events:
        now, _, kind, payload = heapq.heappop(events)
        if kind == "arrive":
            f, hop, created = payload
            p = paths[f][hop]
            queues.setdefault(p, {}).setdefault(flows[f].prio, deque()).append((f, hop, created))
            start(p, now)
        else:
            p, (f, hop, created) = payload
            busy[p] = False
            if hop + 1 < len(paths[f]):
                push(now + tp, "arrive", (f, hop + 1, created))
            else:
                worst[f] = max(worst[f], now + tp - created)
            start(p, now)
    return worst
