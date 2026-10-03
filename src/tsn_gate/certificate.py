"""
Certificates and an independent checker.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from .analysis import INF

REL_TOL = 1e-9


@dataclass(frozen=True)
class HopWitness:
    port: tuple
    b_in: float
    B_H: float
    R_H: float
    L_lo: float
    B_k: float
    R_k: float
    delay: float


@dataclass(frozen=True)
class FlowWitness:
    flow: object          # Flow
    path: tuple
    hops: tuple           # Hop witness (per hop)
    e2e: float


@dataclass
class Certificate:
    verdict: bool
    flow_id: int
    state_before: str                  # digest of the admitted set before the request
    state_after: str                   # digest before when rejected
    witnesses: dict = field(default_factory=dict)   # all, or only changed flows
    violations: list = field(default_factory=list)  # human-readable reasons when rejected
    complete: bool = True              # false for an incremental (delta) certificate

    def summary(self) -> str:
        v = "ACCEPT" if self.verdict else "REJECT"
        s = f"{v} flow {self.flow_id}: {len(self.witnesses)} witnesses"
        if self.violations:
            s += "; " + "; ".join(self.violations[:3])
        return s


def flow_hash(f) -> int:
    key = repr((f.id, f.src, f.dst, f.b, f.r, f.L, f.prio, f.deadline)).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")


def digest(flows) -> str:
    """Fingerprint of an admitted set: XOR of flow hashes (order-free, O(1) to update)."""
    h = 0
    for f in flows:
        h ^= flow_hash(f)
    return f"{h:016x}"


def make_witness(flow, path, bursts, port_results, e2e) -> FlowWitness:
    hops = []
    for i, p in enumerate(path):
        cb = port_results[p].classes[flow.prio]
        hops.append(HopWitness(p, bursts[i], cb.B_H, cb.R_H, cb.L_lo, cb.B_k, cb.R_k, cb.delay))
    return FlowWitness(flow, tuple(path), tuple(hops), e2e)


# ---------------------------------------------------------------------------
def _ge(a: float, b: float) -> bool:
    """a >= b up to a relative tolerance."""
    return a >= b - REL_TOL * max(1.0, abs(a), abs(b))


def check_certificate(net, witnesses: dict, flows=None) -> tuple:
    """
    Verify a COMPLETE acceptance witness set. When given, the checker
    also requires exactly one witness per admitted flow, carrying that flow's own
    parameters (C0). Without it, a certificate that silently omits a flow would
    still pass: removing a flow only makes the other aggregates over-estimates.
    """
    err = []
    if flows is not None:                                                      # C0
        if set(witnesses) != set(flows):
            err.append(f"witness set != admitted flows (missing "
                       f"{sorted(set(flows) - set(witnesses))[:5]}, extra "
                       f"{sorted(set(witnesses) - set(flows))[:5]})")
        err += [f"flow {f}: witness parameters differ from the flow database"
                for f in witnesses if f in flows and witnesses[f].flow != flows[f]]
    C, tp = net.C, net.t_proc
    at_port = {}
    for fid, w in witnesses.items():
        f = w.flow
        if w.path != net.route(f.src, f.dst):                                  # C1
            err.append(f"flow {fid}: path is not the fixed route")
            continue
        if len(w.hops) != len(w.path):
            err.append(f"flow {fid}: hop count mismatch")
            continue
        if not _ge(w.hops[0].b_in, f.b):                                       # C2
            err.append(f"flow {fid}: initial burst below b")
        for i, h in enumerate(w.hops):
            at_port.setdefault(h.port, []).append((f, h))
            if i + 1 < len(w.hops) and not _ge(w.hops[i + 1].b_in, h.b_in + f.r * h.delay):  # C3
                err.append(f"flow {fid} hop {i}: output burst not propagated")
            ok_rate = h.R_H < C and h.R_H + h.R_k <= C * (1 + REL_TOL)          # C5
            if not ok_rate or h.delay == INF:
                err.append(f"flow {fid} hop {i}: rate condition fails at {h.port}")
            elif not _ge(h.delay, (h.B_H + h.L_lo + h.B_k) / (C - h.R_H) + tp):
                err.append(f"flow {fid} hop {i}: delay below the NP-SP bound")
        if not _ge(w.e2e, math.fsum(h.delay for h in w.hops)):                  # C6
            err.append(f"flow {fid}: e2e below the sum of hop delays")
        if w.e2e > f.deadline:
            err.append(f"flow {fid}: e2e {w.e2e:.3e} > deadline {f.deadline:.3e}")
    for p, lst in at_port.items():                                             # C4
        for f, h in lst:
            k = f.prio
            same = [(g, x) for g, x in lst if g.prio == k]
            hi = [(g, x) for g, x in lst if g.prio < k]
            lo = [g for g, _ in lst if g.prio > k]
            if not (_ge(h.B_k, math.fsum(x.b_in for _, x in same))
                    and _ge(h.R_k, math.fsum(g.r for g, _ in same))
                    and _ge(h.B_H, math.fsum(x.b_in for _, x in hi))
                    and _ge(h.R_H, math.fsum(g.r for g, _ in hi))
                    and _ge(h.L_lo, max((g.L for g in lo), default=0.0))):
                err.append(f"flow {f.id} at {p}: class aggregates under-estimated")
    return (not err, err)
