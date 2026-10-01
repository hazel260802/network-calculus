"""Reference topologies in feed-forward under shortest-path routing."""
from __future__ import annotations

from .model import GBPS, Network


def line(n_switches: int = 5, es_per_switch: int = 4, C: float = GBPS, t_proc: float = 0.0) -> Network:
    """Daisy chain sw with end stations on each switch."""
    sws = [f"sw{i}" for i in range(n_switches)]
    links = list(zip(sws[:-1], sws[1:]))
    es = []
    for i, sw in enumerate(sws):
        for j in range(es_per_switch):
            e = f"es{i}_{j}"
            es.append(e)
            links.append((e, sw))
    return Network(links, es, C, t_proc)


def tree(n_edge: int = 4, es_per_switch: int = 5, C: float = GBPS, t_proc: float = 0.0) -> Network:
    """Two-level tree: one core switch, edge switches, end stations on edge switches."""
    links, es = [], []
    for i in range(n_edge):
        sw = f"sw{i + 1}"
        links.append(("sw0", sw))
        for j in range(es_per_switch):
            e = f"es{i + 1}_{j}"
            es.append(e)
            links.append((e, sw))
    return Network(links, es, C, t_proc)


def single_switch(n_es: int = 3, C: float = GBPS, t_proc: float = 0.0) -> Network:
    """One switch with n end stations (for hand-computed examples)."""
    es = [f"es{i}" for i in range(n_es)]
    return Network([(e, "sw0") for e in es], es, C, t_proc)
