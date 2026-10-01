"""
Cross-check the gate's bounds against panco.

Two modes:

  --mode hop   Per-hop check, pure Python (no LP solver). For every port and class of
               our analysis, panco's SpServer.residual() builds the residual service
               curve of the class from the higher-priority cross traffic (B_H, R_H) and
               the max lower-priority frame; we compare
                   d_panco = T_res + B_k / R_res      with our d_k,
                   TokenBucket(b, r).delay(d)         with our output burst.
               Validates the per-hop formulas; the aggregation is ours.

  --mode e2e   End-to-end check, independent of our aggregation and burst propagation:
               panco's SpNetwork builds one FIFO network per priority class (residual
               servers, class by class) and TfaLP computes the TFA bounds. Requires
               `lp_solve` (on Windows panco calls it through WSL:
               `wsl sudo apt install lp-solve`).

Both use the same model as the gate: servers are RateLatency(C, 0) with no maximum
service curve (no line shaping), non-strict residual (max frame of strictly lower
priority), t_proc = 0. Units are converted to microseconds to keep the LP well scaled.

Usage:
    PANCO_PATH=/path/to/panco python validation/panco_check.py --mode hop
    PANCO_PATH=/path/to/panco python validation/panco_check.py --mode e2e
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if os.environ.get("PANCO_PATH"):
    sys.path.insert(0, os.environ["PANCO_PATH"])

from panco.descriptor.curves import RateLatency, TokenBucket  # noqa: E402
from panco.descriptor.server import Server  # noqa: E402
from panco.staticpriorities.spServer import SpServer  # noqa: E402

from tsn_gate import Flow, IncrementalGate  # noqa: E402
from tsn_gate.topologies import leaf_spine_large, leaf_spine_small, single_switch  # noqa: E402
from tsn_gate.workload import random_flows  # noqa: E402

US = 1e6   # seconds -> microseconds


def scenarios():
    """(name, network, admitted gate) with t_proc = 0."""
    out = []
    net = single_switch(3)
    g = IncrementalGate(net)
    g.admit(Flow(1, "es0", "es1", b=12000, r=12e6, L=12000, prio=1, deadline=1e-4))
    g.admit(Flow(2, "es2", "es1", b=800, r=0.8e6, L=800, prio=0, deadline=5e-5))
    out.append(("hand", net, g))
    for name, make, n in [("ls-small", leaf_spine_small, 60), ("ls-large", leaf_spine_large, 60)]:
        for seed in (0, 1):
            net = make()
            g = IncrementalGate(net)
            for f in random_flows(net, n, seed=seed):
                g.admit(f)
            out.append((f"{name}-s{seed}", net, g))
    return out


def rel(a, b):
    return abs(a - b) / max(abs(a), abs(b), 1e-300)


# ---------------------------------------------------------------------------
def check_hop(name, net, g, rows):
    C = net.C / US                                     # bit/us
    for p, res in g.port_results.items():
        prios = sorted(res.classes)
        n_cls = max(prios) + 1
        max_len = [0.0] * n_cls
        for f, _ in g.members[p]:
            fl = g.flows[f]
            max_len[fl.prio] = max(max_len[fl.prio], fl.L)
        sp = SpServer([RateLatency(C, 0)], [], max_len)
        for k in prios:
            cb = res.classes[k]
            srv = sp.residual([TokenBucket(cb.B_H, cb.R_H / US)], k, False)
            rl = srv.service_curve[0]
            d_panco = rl.latency + cb.B_k / rl.rate        # us
            d_ours = cb.delay * US
            rows.append((name, "hop-delay", str(p), k, d_ours, d_panco, rel(d_ours, d_panco)))
        for f, i in g.members[p]:
            fl = g.flows[f]
            if i + 1 < len(g.paths[f]):
                d = res.classes[fl.prio].delay * US
                b_panco = TokenBucket(g.bursts[f][i], fl.r / US).delay(d).sigma
                b_ours = g.bursts[f][i + 1]
                rows.append((name, "out-burst", f"{f}@{p}", fl.prio, b_ours, b_panco,
                             rel(b_ours, b_panco)))


# ---------------------------------------------------------------------------
def lp_solve_available() -> bool:
    from panco.lpSolvePath import LPSOLVEPATH
    if not LPSOLVEPATH:
        return False
    if LPSOLVEPATH[0] == "wsl":
        r = subprocess.run(["wsl", "which", "lp_solve"], capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() != ""
    return shutil.which(LPSOLVEPATH[0]) is not None


def check_e2e(name, net, g, rows):
    from panco.fifo.tfaLP import TfaLP
    from panco.staticpriorities.spFlow import SpFlow
    from panco.staticpriorities.spNetwork import SpNetwork

    ports = sorted({p for f in g.paths for p in g.paths[f]}, key=net.topo_index.__getitem__)
    idx = {p: j for j, p in enumerate(ports)}
    fids = sorted(g.flows)
    sp_flows = [SpFlow([TokenBucket(g.flows[f].b, g.flows[f].r / US)],
                       [idx[p] for p in g.paths[f]], g.flows[f].L, g.flows[f].prio) for f in fids]
    servers = [Server([RateLatency(net.C / US, 0)], []) for _ in ports]
    per_class = SpNetwork(servers, sp_flows).equiv_network(False)
    for k, cnet in enumerate(per_class):
        members = [f for f in fids if g.flows[f].prio == k]      # same order as panco's list
        if not members:
            continue
        delays = TfaLP(cnet, filename=f"tfa_{name}_{k}.lp").all_delays
        for f, d_panco in zip(members, delays):
            d_ours = g.e2e[f] * US
            rows.append((name, "e2e", str(f), k, d_ours, float(d_panco), rel(d_ours, d_panco)))


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["hop", "e2e"], default="hop")
    ap.add_argument("--out", default=str(ROOT / "results" / "panco_check.csv"))
    args = ap.parse_args()

    if args.mode == "e2e" and not lp_solve_available():
        sys.exit("lp_solve not found: install it (Linux: apt install lp-solve; "
                 "Windows: wsl sudo apt install lp-solve) or use --mode hop")

    rows = []
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory(dir=ROOT / "results") as tmp:
        os.chdir(tmp)                   # panco writes its .lp files in the cwd
        try:
            for name, net, g in scenarios():
                (check_hop if args.mode == "hop" else check_e2e)(name, net, g, rows)
        finally:
            os.chdir(cwd)

    out = Path(args.out).with_name(Path(args.out).stem + f"_{args.mode}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "quantity", "where", "class", "ours", "panco", "rel_diff"])
        w.writerows(rows)

    worst = max(rows, key=lambda r: r[6])
    by_scn = {}
    for r in rows:
        by_scn.setdefault(r[0], []).append(r[6])
    print(f"mode={args.mode}: {len(rows)} comparisons -> {out.relative_to(ROOT)}")
    for s, v in by_scn.items():
        print(f"  {s:10s} n={len(v):4d}  max rel diff = {max(v):.2e}")
    print(f"  worst: {worst[:4]} ours={worst[4]:.6f} panco={worst[5]:.6f}")
    tol = 1e-9 if args.mode == "hop" else 1e-5
    ok = worst[6] <= tol
    print("PASS" if ok else "FAIL", f"(tolerance {tol:g})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
