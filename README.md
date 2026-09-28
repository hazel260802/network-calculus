# Certified Admission Control for TSN

Preparatory work for the PhD *"Certified Dynamic Reconfiguration of Time-Sensitive Networks: Online Admission Control under Worst-Case Determinism Guarantees"* (LyRIDS, ECE × CEDRIC, Cnam) — [thesis theme](docs/projects/thesis%20theme.pdf).

## Overview

TSN guarantees worst-case latency only for a configuration fixed and verified offline. Online reconfiguration can be proposed quickly by heuristics, ILP/SMT or DRL/GNN, but none of these certifies worst-case delays. We place a **certified admission gate** between any proposer and the network: a flow is committed only with a machine-checkable certificate that every admitted flow still meets its deadline. The guarantee holds as far as the network model does.

## Model

1 Gbit/s switches, fixed shortest-path routing, token-bucket flows $(b, r)$, non-preemptive static priority (NP-SP), deterministic network calculus (Total Flow Analysis). For class $k$ at a port of rate $C$:

$$
d_k = \frac{B_H + L_{lo} + B_k}{C - R_H} + t_{proc}, \qquad R_H + R_k \le C
$$

$$
b' = b + r \, d_k, \qquad D = \sum_{h \in \mathcal{P}} d_k^{(h)}
$$

$B_H, R_H$: aggregate burst and rate of higher-priority flows; $L_{lo}$: largest lower-priority frame (non-preemptive blocking); $B_k, R_k$: aggregates of class $k$; $b'$: output burst; $D$: end-to-end bound over path $\mathcal{P}$.

## Repository structure

```
├── src/
│   ├── tsn_gate/        # model, NP-SP analysis, full/incremental gates, certificate checker, simulator
│   ├── tests/           # hand calculation, full = incremental, tampered certificates, simulation
│   ├── validation/      # cross-check against panco
│   ├── experiments/     # run_experiments.py, plot_figures.py
│   ├── results/         # raw CSVs
│   └── figures/         # PNG/PDF
└── docs/                # thesis offer, courses, math background
```

## Reproduction

```bash
cd src
pip install -r requirements.txt
python -m pytest -q                        # tests
python experiments/run_experiments.py      # -> results/*.csv
python experiments/plot_figures.py         # -> figures/*.{png,pdf}

# optional: panco cross-check 
git clone https://github.com/anne-bou/panco ../panco && git -C ../panco checkout f035ccc5
PANCO_PATH=../panco python validation/panco_check.py --mode hop
PANCO_PATH=../panco python validation/panco_check.py --mode e2e
```

## References

1. J.-Y. Le Boudec, P. Thiran, *Network Calculus*, LNCS 2050, Springer, 2001.
2. L. Zhao, P. Pop, Z. Zheng, Q. Li, "Timing Analysis of AVB Traffic in TSN Networks Using Network Calculus," RTAS 2018. [PDF](https://www2.compute.dtu.dk/~paupo/publications/Zhao2017aa-Timing%20Analysis%20of%20AVB%20Traffic-.pdf)
3. M. Alshiekh et al., "Safe Reinforcement Learning via Shielding," AAAI 2018.
4. S. Bondorf, J. B. Schmitt, "The DiscoDNC v2: A Comprehensive Tool for Deterministic Network Calculus," VALUETOOLS 2014. [NetCal/DNC](https://github.com/NetCal/DNC)
5. A. Bouillard, *panco: Performance Analysis with Network Calculus and Optimization*, 2022. [anne-bou/panco](https://github.com/anne-bou/panco); theory in A. Bouillard, M. Boyer, E. Le Corronc, *Deterministic Network Calculus*, Wiley-ISTE, 2018.
6. C. Xue et al., "Real-Time Scheduling for 802.1Qbv Time-Sensitive Networking (TSN): A Systematic Review and Experimental Study," RTAS 2024. [ChuanyuXue/tsnkit](https://github.com/ChuanyuXue/tsnkit)
