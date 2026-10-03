"""Reference topologies, feed-forward under shortest-path (ECMP) routing."""
from __future__ import annotations

from .model import GBPS, Network


def leaf_spine(n_spine: int = 2, n_leaf: int = 4, es_per_leaf: int = 5, C: float = GBPS,
               t_proc: float = 0.0) -> Network:
    """
    Two-tier leaf-spine (folded Clos): every leaf links to every spine, end
    stations attach to leaves. 
    """
    spines = [f"sp{s}" for s in range(n_spine)]
    links, es = [], []
    for i in range(n_leaf):
        leaf = f"lf{i}"
        links += [(leaf, sp) for sp in spines]
        for j in range(es_per_leaf):
            e = f"es{i}_{j}"
            es.append(e)
            links.append((e, leaf))
    return Network(links, es, C, t_proc)


def leaf_spine_small(C: float = GBPS, t_proc: float = 0.0) -> Network:
    """2 spines x 4 leaves x 5 end stations: 20 end stations, 56 ports."""
    return leaf_spine(2, 4, 5, C, t_proc)


def leaf_spine_large(C: float = GBPS, t_proc: float = 0.0) -> Network:
    """4 spines x 8 leaves x 5 end stations: 40 end stations, 144 ports."""
    return leaf_spine(4, 8, 5, C, t_proc)


def single_switch(n_es: int = 3, C: float = GBPS, t_proc: float = 0.0) -> Network:
    """One switch with n end stations (for hand-computed examples)."""
    es = [f"es{i}" for i in range(n_es)]
    return Network([(e, "sw0") for e in es], es, C, t_proc)
