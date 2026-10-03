"""
Admission gates: admit(state, flow) to (verdict, certificate).

FullGate         recomputes the whole TFA for every request.
IncrementalGate  recomputes only the ports whose inputs change, in topological
                 order, and stops propagating as soon as a burst is unchanged.

Invariant of both gates: every admitted flow meets its deadline under the model.
Both call the same pure function `analyze_port`, so on the same state they produce
bit-identical bounds.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from .analysis import analyze_port, e2e_bound, full_analysis, output_burst
from .certificate import Certificate, digest, flow_hash, make_witness
from .model import Flow, Network


@dataclass
class State:
    """Immutable-by-convention admitted state (used by the functional API)."""
    net: Network
    flows: dict = field(default_factory=dict)   # fid -> Flow

    def with_flow(self, flow: Flow) -> "State":
        return State(self.net, {**self.flows, flow.id: flow})


def _violations(flows, paths, port_results, e2e, fids) -> list:
    """ Message flows are unstable or miss their deadline."""
    out = []
    for f in sorted(fids):
        fl = flows[f]
        for p in paths[f]:
            cb = port_results[p].classes[fl.prio]
            if not cb.stable:
                out.append((f, f"unstable: flow {f} at port {p} class {fl.prio} "
                               f"(R_H+R_k={cb.R_H + cb.R_k:.4g} > C)"))
                break
        else:
            if e2e[f] > fl.deadline:
                out.append((f, f"deadline: flow {f} bound {e2e[f]*1e6:.2f}us "
                               f"> {fl.deadline*1e6:.2f}us"))
    return out


def admit(state: State, flow: Flow):
    """ Functional API from the assignment. """
    flow.validate()
    if flow.id in state.flows:
        raise ValueError(f"duplicate flow id {flow.id}")
    net = state.net
    flows = {**state.flows, flow.id: flow}
    paths = {f: net.route(fl.src, fl.dst) for f, fl in flows.items()}
    A = full_analysis(net, flows, paths)
    viol = _violations(flows, paths, A.port_results, A.e2e, flows)
    before = digest(state.flows.values())
    keep = {f for f, _ in viol} if viol else flows
    wit = {f: make_witness(flows[f], paths[f], A.bursts[f], A.port_results, A.e2e[f])
           for f in keep}
    if viol:
        return False, Certificate(False, flow.id, before, before, wit, [m for _, m in viol])
    return True, Certificate(True, flow.id, before, digest(flows.values()), wit)


class FullGate:
    """Stateful wrapper around commits with accepted flows."""

    def __init__(self, net: Network):
        self.state = State(net)
        self.witnesses = {}

    def admit(self, flow: Flow):
        ok, cert = admit(self.state, flow)
        if ok:
            self.state = self.state.with_flow(flow)
            self.witnesses = cert.witnesses
        return ok, cert

    @property
    def flows(self):
        return self.state.flows


class IncrementalGate:
    """Keeps the TFA results cached and only recomputes what a new flow can change."""

    def __init__(self, net: Network):
        self.net = net
        self.flows = {}          # fid -> Flow
        self.paths = {}          # fid -> path
        self.members = {}        # port -> list of (fid, hop index)
        self.port_results = {}   # port -> PortResult
        self.bursts = {}         # fid -> list of input bursts per hop
        self.e2e = {}            # fid -> bound
        self.witnesses = {}      # fid -> FlowWitness (complete after each commit)
        self.digest = 0          # XOR of flow hashes
        self.last_ports_recomputed = 0

    def admit(self, flow: Flow):
        flow.validate()
        if flow.id in self.flows:
            raise ValueError(f"duplicate flow id {flow.id}")
        net, fid = self.net, flow.id
        path = net.route(flow.src, flow.dst)

        # Tentative overlays: the cache is not touched before the verdict.
        flows = _Overlay(self.flows, {fid: flow})
        paths = _Overlay(self.paths, {fid: path})
        members = _Overlay(self.members, {p: self.members.get(p, []) + [(fid, i)]
                                          for i, p in enumerate(path)})
        new_bursts = {fid: [flow.b] + [None] * (len(path) - 1)}
        new_pr = {}
        changed = {fid}   # flows whose witness changes (a hop ClassBound or burst differs)

        def burst(f, i):
            return new_bursts[f][i] if f in new_bursts else self.bursts[f][i]

        heap = [(net.topo_index[p], p) for p in path]
        heapq.heapify(heap)
        queued = set(path)
        while heap:                        # ports are popped in topological order
            _, p = heapq.heappop(heap)
            mem = members[p]
            res = analyze_port(net.C, net.t_proc,
                               [(flows[f].prio, burst(f, i), flows[f].r, flows[f].L)
                                for f, i in mem])
            new_pr[p] = res
            old = self.port_results.get(p)
            for f, i in mem:
                k = flows[f].prio
                if old is None or old.classes.get(k) != res.classes[k]:
                    changed.add(f)
                if i + 1 < len(paths[f]):
                    nb = output_burst(burst(f, i), flows[f].r, res.classes[k].delay)
                    if nb != burst(f, i + 1):
                        if f not in new_bursts:
                            new_bursts[f] = list(self.bursts[f])
                        new_bursts[f][i + 1] = nb
                        changed.add(f)
                        q = paths[f][i + 1]
                        if q not in queued:
                            queued.add(q)
                            heapq.heappush(heap, (net.topo_index[q], q))
        self.last_ports_recomputed = len(new_pr)

        prs = _Overlay(self.port_results, new_pr)
        new_e2e = {f: e2e_bound(flows[f], paths[f], prs) for f in changed}
        viol = _violations(flows, paths, prs, new_e2e, changed)
        keep = {f for f, _ in viol} if viol else changed
        wit = {f: make_witness(flows[f], paths[f], new_bursts.get(f) or self.bursts[f],
                               prs, new_e2e[f]) for f in keep}
        before = f"{self.digest:016x}"
        if viol:
            return False, Certificate(False, fid, before, before, wit,
                                      [m for _, m in viol], complete=False)

        # Commit.
        self.flows[fid] = flow
        self.paths[fid] = path
        for i, p in enumerate(path):
            self.members.setdefault(p, []).append((fid, i))
        self.port_results.update(new_pr)
        self.bursts.update(new_bursts)
        self.e2e.update(new_e2e)
        self.witnesses.update(wit)
        self.digest ^= flow_hash(flow)
        return True, Certificate(True, fid, before, f"{self.digest:016x}", wit,
                                 complete=False)


class _Overlay:
    """Read-only dict view."""
    __slots__ = ("base", "top")

    def __init__(self, base, top):
        self.base, self.top = base, top

    def __getitem__(self, k):
        return self.top[k] if k in self.top else self.base[k]
