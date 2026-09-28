"""
Network and flow model.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

GBPS = 1e9
BYTE = 8

Port = tuple  # (u, v)


@dataclass(frozen=True)
class Flow:
    """A flow request."""
    id: int
    src: str
    dst: str
    b: float          # burst (bits)
    r: float          # rate (bit/s)
    L: float          # max frame size (bits)
    prio: int         # 0 = highest priority
    deadline: float   # end-to-end deadline (s)

    def validate(self) -> None:
        if not (self.r >= 0 and self.L > 0 and self.b >= self.L):
            raise ValueError(f"flow {self.id}: need r >= 0, L > 0, b >= L")
        if self.prio < 0 or self.deadline <= 0:
            raise ValueError(f"flow {self.id}: need prio >= 0, deadline > 0")


@dataclass
class Network:
    """
    Undirected topology with full-duplex links of equal rate C.
    """
    links: list
    end_stations: list
    C: float = GBPS
    t_proc: float = 0.0
    adj: dict = field(init=False)
    topo_index: dict = field(init=False)
    _routes: dict = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.adj = {}
        for u, v in self.links:
            self.adj.setdefault(u, set()).add(v)
            self.adj.setdefault(v, set()).add(u)
        self.topo_index = self._port_topological_order()

    # ---- routing -------------------------------------------------------
    def route(self, src: str, dst: str) -> tuple:
        """Path as a tuple of ports [(src, s1), (s1, s2), ..., (sk, dst)]."""
        key = (src, dst)
        if key not in self._routes:
            parent = {src: None}
            q = deque([src])
            while q:
                u = q.popleft()
                if u == dst:
                    break
                for v in sorted(self.adj[u]):
                    # end stations do not forward traffic
                    if v not in parent and (v == dst or v not in self.end_stations):
                        parent[v] = u
                        q.append(v)
            if dst not in parent:
                raise ValueError(f"no route {src} -> {dst}")
            nodes = [dst]
            while nodes[-1] != src:
                nodes.append(parent[nodes[-1]])
            nodes.reverse()
            self._routes[key] = tuple(zip(nodes[:-1], nodes[1:]))
        return self._routes[key]

    def ports(self) -> list:
        return sorted({(u, v) for u, v in self.links} | {(v, u) for u, v in self.links})

    # ---- feed-forward check -------------------------------------------
    def _port_topological_order(self) -> dict:
        """
        Topological order of the port dependency graph induced by all routes.

        Since routing is fixed, every flow that can ever be admitted follows one of
        these routes, so one order computed here is valid for every flow set.
        Raises if the graph is cyclic (TFA as implemented needs feed-forward).
        """
        succ = {p: set() for p in self.ports()}
        for s in self.end_stations:
            for d in self.end_stations:
                if s != d:
                    path = self.route(s, d)
                    for a, b in zip(path[:-1], path[1:]):
                        succ[a].add(b)
        indeg = {p: 0 for p in succ}
        for p in succ:
            for q in succ[p]:
                indeg[q] += 1
        ready = sorted(p for p in succ if indeg[p] == 0)
        order = []
        while ready:
            p = ready.pop(0)
            order.append(p)
            for q in sorted(succ[p]):
                indeg[q] -= 1
                if indeg[q] == 0:
                    ready.append(q)
            ready.sort()
        if len(order) != len(succ):
            raise ValueError("port dependency graph is cyclic: network is not feed-forward")
        return {p: i for i, p in enumerate(order)}
