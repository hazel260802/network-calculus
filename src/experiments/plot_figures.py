#!/usr/bin/env python3
"""Generate the evaluation figures of the certified admission gate.

All data loaded from CSV reports in results/ (written by benchmark_gate.py and
validation/panco_check.py).
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import csv
import os
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
RESULTS_DIR = os.path.join(REPO_ROOT, "results")
OUT_DIR = os.path.join(REPO_ROOT, "figures")
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
})

TOPOLOGIES = ["line", "tree"]
TOPO_LABEL = {"line": "Line (5 switches)", "tree": "Tree (1 core + 4 edge)"}
GATES = ["full", "incremental"]
GATE_LABEL = {"full": "Full TFA", "incremental": "Incremental"}
GATE_COLOR = {"full": "#1f77b4", "incremental": "#ff7f0e"}
PRIO_LABEL = {0: "Class 0 (control)", 1: "Class 1 (stream)"}
PRIO_COLOR = {0: "#d62728", 1: "#2ca02c"}
CHECKPOINTS = [10, 20, 50, 100, 200, 500, 1000]


def load_csv(filename):
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    for fmt in ("png", "pdf"):
        out = os.path.join(OUT_DIR, f"{name}.{fmt}")
        fig.savefig(out)
        print(f"[OK] {out}")
    plt.close(fig)


# ── Load data ─────────────────────────────────────────────────────────

req_rows = load_csv("requests.csv")
print(f"[load] requests.csv: {len(req_rows)} rows")

sim_rows = load_csv("simulation.csv")
print(f"[load] simulation.csv: {len(sim_rows)} rows")

# runs[(topology, gate, seed)] = per-request arrays, in request order
runs = {}
for r in req_rows:
    key = (r["topology"], r["gate"], int(r["seed"]))
    d = runs.setdefault(key, {"us": [], "acc": [], "n_adm": [], "prio": [], "ports": []})
    d["us"].append(float(r["admit_us"]))
    d["acc"].append(int(r["accepted"]))
    d["n_adm"].append(int(r["n_admitted"]))
    d["prio"].append(int(r["prio"]))
    d["ports"].append(int(r["ports_recomputed"]))
for d in runs.values():
    for k in d:
        d[k] = np.array(d[k])
seeds = sorted({s for _, _, s in runs})
print(f"[load] {len(runs)} runs, seeds={seeds}")


def seed_stack(topo, gate, field):
    return np.stack([runs[(topo, gate, s)][field] for s in seeds])


# ── Figure 1: Per-request admission latency (box plots) ───────────────

print("\n[latency] per-request admission time (µs):")
for topo in TOPOLOGIES:
    for gate in GATES:
        us = seed_stack(topo, gate, "us").ravel()
        print(f"  {topo:5s} {gate:11s}  median={np.median(us):7.1f}  p95={np.percentile(us, 95):7.1f}"
              f"  max={us.max():8.1f}  N={us.size}")

fig, axes = plt.subplots(1, 2, figsize=(7, 3.5), sharey=True)
for ax, topo in zip(axes, TOPOLOGIES):
    vals = [seed_stack(topo, g, "us").ravel() for g in GATES]
    bp = ax.boxplot(vals, tick_labels=[GATE_LABEL[g] for g in GATES], patch_artist=True,
                    widths=0.6, showfliers=False,
                    medianprops=dict(color="black", linewidth=1.5))
    for patch, g in zip(bp["boxes"], GATES):
        patch.set_facecolor(GATE_COLOR[g])
        patch.set_alpha(0.8)
    ax.set_yscale("log")
    ax.set_title(TOPO_LABEL[topo])
    ax.grid(True, alpha=0.3, axis="y", linestyle="--")
axes[0].set_ylabel("Admission time per request (µs, log)")
fig.tight_layout()
save(fig, "admission_latency")


# ── Figure 2: Scalability with the number of requests and admitted flows ──

print("\n[scalability] cumulative time at N requests (s, mean over seeds):")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.6))
for topo, ls, mk in (("line", "-", "o"), ("tree", "--", "s")):
    for gate in GATES:
        cum = np.cumsum(seed_stack(topo, gate, "us"), axis=1) / 1e6
        at = cum[:, np.array(CHECKPOINTS) - 1]
        mean, std = at.mean(axis=0), at.std(axis=0)
        ax1.plot(CHECKPOINTS, mean, ls, marker=mk, color=GATE_COLOR[gate], linewidth=1.6,
                 markersize=4, label=f"{GATE_LABEL[gate]}, {topo}")
        ax1.fill_between(CHECKPOINTS, mean - std, mean + std, color=GATE_COLOR[gate], alpha=0.15)
        print(f"  {topo:5s} {gate:11s} " + "  ".join(f"N={n}:{m:.3f}" for n, m in zip(CHECKPOINTS, mean)))

        # per-request time against the size of the admitted state (binned)
        n_adm = seed_stack(topo, gate, "n_adm").ravel()
        us = seed_stack(topo, gate, "us").ravel()
        edges = np.arange(0, n_adm.max() + 10, 10)
        idx = np.digitize(n_adm, edges)
        xs = [edges[i - 1] + 5 for i in np.unique(idx)]
        ys = [np.median(us[idx == i]) for i in np.unique(idx)]
        ax2.plot(xs, ys, ls, marker=mk, color=GATE_COLOR[gate], linewidth=1.6, markersize=4)

    speed = (seed_stack(topo, "full", "us").sum(axis=1) /
             seed_stack(topo, "incremental", "us").sum(axis=1))
    print(f"  {topo:5s} incremental speed-up over 1,000 requests: {speed.mean():.2f}x ± {speed.std():.2f}")

ax1.set_xscale("log")
ax1.set_xlabel("Requests processed $N$")
ax1.set_ylabel("Cumulative wall-clock time (s)")
ax1.set_title("(a) Total time")
ax1.grid(True, alpha=0.3, linestyle="--")
ax1.set_ylim(bottom=0)
ax2.set_xlabel("Flows already admitted")
ax2.set_ylabel("Median time per request (µs)")
ax2.set_title("(b) Cost vs. state size")
ax2.grid(True, alpha=0.3, linestyle="--")
ax2.set_ylim(bottom=0)
handles, labels = ax1.get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.1), ncol=4,
           frameon=False, fontsize=8)
fig.tight_layout()
save(fig, "scalability")

inc_ports = np.concatenate([seed_stack(t, "incremental", "ports").ravel() for t in TOPOLOGIES])
print(f"  incremental gate recomputes {np.median(inc_ports):.0f} ports per request (median),"
      f" max {inc_ports.max()}")


# ── Figure 3: Admission rate ──────────────────────────────────────────

print("\n[admission] accepted fraction of the first N requests (mean over seeds):")
fig, axes = plt.subplots(1, 2, figsize=(7, 3.4), sharey=True)
for ax, topo in zip(axes, TOPOLOGIES):
    acc = seed_stack(topo, "incremental", "acc")
    prio = seed_stack(topo, "incremental", "prio")
    cp = np.array(CHECKPOINTS)
    for p in (0, 1):
        m = prio == p
        rate = np.cumsum(acc * m, axis=1) / np.maximum(np.cumsum(m, axis=1), 1)
        at = rate[:, cp - 1]
        ax.errorbar(cp, at.mean(axis=0), yerr=at.std(axis=0), fmt="o-", color=PRIO_COLOR[p],
                    linewidth=1.4, markersize=4, capsize=2, label=PRIO_LABEL[p])
    total = (np.cumsum(acc, axis=1) / np.arange(1, acc.shape[1] + 1))[:, cp - 1]
    ax.plot(cp, total.mean(axis=0), "k--", linewidth=1.0, label="All flows")
    print(f"  {topo:5s} " + "  ".join(f"N={n}:{v:.2f}" for n, v in zip(cp, total.mean(axis=0)))
          + f"   admitted at N=1000: {acc.sum(axis=1).mean():.0f} ± {acc.sum(axis=1).std():.0f}")
    ax.set_xscale("log")
    ax.set_xlabel("Requests $N$")
    ax.set_title(TOPO_LABEL[topo])
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_ylim(0, 1.05)
axes[0].set_ylabel("Admission rate")
axes[0].legend(loc="lower left", fontsize=8, framealpha=0.9)
fig.tight_layout()
save(fig, "admission_rate")


# ── Figure 4: Bound tightness against the packet-level simulator ──────

bound = np.array([float(r["bound_us"]) for r in sim_rows])
obs = np.array([float(r["observed_us"]) for r in sim_rows])
sprio = np.array([int(r["prio"]) for r in sim_rows])
ratio = obs / bound
n_viol = int(np.sum(obs > bound * (1 + 1e-9)))
print(f"\n[simulation] {len(sim_rows)} admitted flows, bound violations: {n_viol}")
for p in (0, 1):
    rp = ratio[sprio == p]
    print(f"  {PRIO_LABEL[p]:18s} observed/bound  median={np.median(rp):.3f}  max={rp.max():.3f}  N={rp.size}")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.6))
for p in (0, 1):
    m = sprio == p
    ax1.scatter(bound[m], obs[m], s=6, alpha=0.5, color=PRIO_COLOR[p], label=PRIO_LABEL[p])
    rs = np.sort(ratio[m])
    ax2.plot(rs, np.arange(1, rs.size + 1) / rs.size, color=PRIO_COLOR[p], linewidth=1.6,
             label=PRIO_LABEL[p])
lim = [min(bound.min(), obs[obs > 0].min()) * 0.8, bound.max() * 1.2]
ax1.plot(lim, lim, "k--", linewidth=0.8, label="Observed = bound")
ax1.set_xscale("log")
ax1.set_yscale("log")
ax1.set_xlim(lim)
ax1.set_ylim(lim)
ax1.set_xlabel("Network-calculus bound (µs)")
ax1.set_ylabel("Worst observed delay (µs)")
ax1.set_title("(a) Per flow")
ax1.legend(fontsize=8, loc="upper left", framealpha=0.9)
ax1.grid(True, alpha=0.3, linestyle="--")
ax2.axvline(1.0, color="black", linewidth=0.8, linestyle="--")
ax2.set_xlim(0, 1.05)
ax2.set_xlabel("Observed / bound")
ax2.set_ylabel("Fraction of flows (CDF)")
ax2.set_title("(b) Tightness")
ax2.grid(True, alpha=0.3, linestyle="--")
fig.tight_layout()
save(fig, "bound_tightness")


# ── Figure 5: Agreement with panco ────────────────────────────────────

panels = []
for mode, quantities, title in (
    ("hop", ["hop-delay", "out-burst"], "(a) Per hop"),
    ("e2e", ["e2e"], "(b) End to end (TfaLP)"),
):
    name = f"panco_check_{mode}.csv"
    if not os.path.exists(os.path.join(RESULTS_DIR, name)):
        print(f"\n[panco] {name} not found — run validation/panco_check.py --mode {mode}")
        continue
    rows = load_csv(name)
    print(f"\n[load] {name}: {len(rows)} rows")
    panels.append((rows, quantities, title))

if panels:
    QCOLOR = {"hop-delay": "#1f77b4", "out-burst": "#ff7f0e", "e2e": "#2ca02c"}
    QLABEL = {"hop-delay": "Hop delay (µs)", "out-burst": "Output burst", "e2e": "End-to-end delay (µs)"}
    fig, axes = plt.subplots(1, len(panels), figsize=(4 * len(panels), 3.8), squeeze=False)
    for ax, (rows, quantities, title) in zip(axes[0], panels):
        for q in quantities:
            sel = [r for r in rows if r["quantity"] == q]
            ours = np.array([float(r["ours"]) for r in sel])
            pan = np.array([float(r["panco"]) for r in sel])
            rel = np.array([float(r["rel_diff"]) for r in sel])
            print(f"  {q:10s} N={len(sel):4d}  max rel diff={rel.max():.2e}")
            ax.scatter(pan, ours, s=10, alpha=0.6, color=QCOLOR[q],
                       label=f"{QLABEL[q]}, max rel. diff {rel.max():.1e}")
        allv = [float(r[k]) for r in rows for k in ("ours", "panco") if float(r[k]) > 0]
        lim = [min(allv) * 0.7, max(allv) * 1.4]
        ax.plot(lim, lim, "k--", linewidth=0.8)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("panco")
        ax.set_ylabel("Our gate")
        ax.set_title(title)
        ax.legend(fontsize=7.5, loc="upper left", framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle="--")
    fig.tight_layout()
    save(fig, "panco_agreement")


print(f"\nDone. All figures in: {OUT_DIR}")
print(f"Data source: {RESULTS_DIR}/")
