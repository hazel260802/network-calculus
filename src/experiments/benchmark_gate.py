#!/usr/bin/env python3
"""
Benchmark the admission gate (speed, admission rate, bound safety).

E1  requests.csv    One row per admission request: 1,000 seeded requests per run,
                    line and tree topologies, full and incremental gates, SEEDS seeds.
                    The first N rows of a run are the experiment for N requests, so one
                    run covers every N in 10..1,000.
E2  simulation.csv  For every flow admitted in E1 (incremental gate), its network-calculus
                    bound and the worst delay observed in the packet-level simulator.

Figures are produced separately by plot_figures.py.
"""

import csv
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT)

from tsn_gate import FullGate, IncrementalGate  # noqa: E402
from tsn_gate.simulator import simulate  # noqa: E402
from tsn_gate.topologies import line, tree  # noqa: E402
from tsn_gate.workload import random_flows  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

N_REQUESTS = 1000
SEEDS = range(10)
TOPOLOGIES = {"line": line, "tree": tree}
GATES = {"full": FullGate, "incremental": IncrementalGate}
T_PROC = 1e-6        # switch processing delay (s), same as the simulator test
SIM_HORIZON = 10e-3  # simulated time (s)


def run_requests(rows):
    for topo, make_net in TOPOLOGIES.items():
        for seed in SEEDS:
            net = make_net(t_proc=T_PROC)
            flows = random_flows(net, N_REQUESTS, seed=seed)
            for gate_name, Gate in GATES.items():
                g = Gate(net)
                n_admitted = 0
                t_run = time.perf_counter()
                for i, f in enumerate(flows):
                    t0 = time.perf_counter_ns()
                    ok, _ = g.admit(f)
                    dt_us = (time.perf_counter_ns() - t0) / 1e3
                    n_admitted += ok
                    ports = g.last_ports_recomputed if gate_name == "incremental" else len(net.ports())
                    rows.append([topo, gate_name, seed, i + 1, f.prio, int(ok), n_admitted,
                                 f"{dt_us:.2f}", ports])
                print(f"[E1] {topo:5s} seed={seed} {gate_name:11s} admitted={n_admitted:4d}/{N_REQUESTS}"
                      f"  {time.perf_counter() - t_run:.2f}s")


def run_simulation(rows):
    for topo, make_net in TOPOLOGIES.items():
        for seed in SEEDS:
            net = make_net(t_proc=T_PROC)
            g = IncrementalGate(net)
            for f in random_flows(net, N_REQUESTS, seed=seed):
                g.admit(f)
            worst = simulate(net, g.flows, g.paths, horizon=SIM_HORIZON, seed=seed)
            n_viol = 0
            for fid, fl in g.flows.items():
                bound, obs = g.e2e[fid], worst[fid]
                n_viol += obs > bound * (1 + 1e-9)
                rows.append([topo, seed, fid, fl.prio, len(g.paths[fid]),
                             f"{bound * 1e6:.4f}", f"{obs * 1e6:.4f}", f"{fl.deadline * 1e6:.4f}"])
            print(f"[E2] {topo:5s} seed={seed} flows={len(g.flows):4d}  bound violations={n_viol}")


def write_csv(name, header, rows):
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"[OK] {path} ({len(rows)} rows)")


if __name__ == "__main__":
    req = []
    run_requests(req)
    write_csv("requests.csv",
              ["topology", "gate", "seed", "request", "prio", "accepted", "n_admitted",
               "admit_us", "ports_recomputed"], req)

    sim = []
    run_simulation(sim)
    write_csv("simulation.csv",
              ["topology", "seed", "flow", "prio", "hops", "bound_us", "observed_us",
               "deadline_us"], sim)
