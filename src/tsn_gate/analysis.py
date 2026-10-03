"""
Deterministic network calculus for NP-SP ports (Total Flow Analysis style).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

INF = math.inf


@dataclass(frozen=True)
class ClassBound:
    prio: int
    B_H: float
    R_H: float
    L_lo: float
    B_k: float
    R_k: float
    delay: float     

    @property
    def stable(self) -> bool:
        return self.delay < INF


@dataclass(frozen=True)
class PortResult:
    classes: dict     # prio to ClassBound


def analyze_port(C: float, t_proc: float, entries) -> PortResult:
    """Pure function with the entries are iterable for flows crossing the port."""
    by_prio = {}
    for prio, b, r, L in entries:
        by_prio.setdefault(prio, []).append((b, r, L))
    prios = sorted(by_prio)
    classes = {}
    for k in prios:
        hi = [x for p in prios if p < k for x in by_prio[p]]
        lo = [x for p in prios if p > k for x in by_prio[p]]
        B_H = math.fsum(b for b, _, _ in hi)
        R_H = math.fsum(r for _, r, _ in hi)
        L_lo = max((L for _, _, L in lo), default=0.0)
        B_k = math.fsum(b for b, _, _ in by_prio[k])
        R_k = math.fsum(r for _, r, _ in by_prio[k])
        if R_H < C and R_H + R_k <= C:
            delay = (B_H + L_lo + B_k) / (C - R_H) + t_proc
        else:
            delay = INF
        classes[k] = ClassBound(k, B_H, R_H, L_lo, B_k, R_k, delay)
    return PortResult(classes)


@dataclass
class Analysis:
    """Result of a TFA pass over a flow set."""
    port_results: dict   # port result
    bursts: dict         # input burst of each hop
    e2e: dict            # end-to-end delay bound


def full_analysis(net, flows: dict, paths: dict) -> Analysis:
    """Recomputes everything."""
    members = {}
    for fid, path in paths.items():
        for i, p in enumerate(path):
            members.setdefault(p, []).append((fid, i))
    bursts = {fid: [flows[fid].b] + [None] * (len(paths[fid]) - 1) for fid in flows}
    port_results = {}
    for p in sorted(members, key=net.topo_index.__getitem__):
        res = analyze_port(net.C, net.t_proc,
                           [(flows[f].prio, bursts[f][i], flows[f].r, flows[f].L)
                            for f, i in members[p]])
        port_results[p] = res
        for f, i in members[p]:
            if i + 1 < len(paths[f]):
                bursts[f][i + 1] = output_burst(bursts[f][i], flows[f].r,
                                                res.classes[flows[f].prio].delay)
    e2e = {f: e2e_bound(flows[f], paths[f], port_results) for f in flows}
    return Analysis(port_results, bursts, e2e)


def output_burst(b: float, r: float, d: float) -> float:
    """Output arrival curve of a server with delay bound."""
    return b + r * d if d < INF else INF


def e2e_bound(flow, path, port_results) -> float:
    return math.fsum(port_results[p].classes[flow.prio].delay for p in path)
