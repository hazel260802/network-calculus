# Certified Admission Control for TSN 

Preparation for the PhD **"Certified Dynamic Reconfiguration of Time-Sensitive Networks: Online Admission Control under Worst-Case Determinism Guarantees"**, in the collaboration between LyRIDS (ECE) and CEDRIC (Cnam) detail in the [docs/projects/thesis theme.pdf](docs/projects/thesis%20theme.pdf).

## Problem formulation

TSN networks guarantee worst-case latency only if their configuration is fixed and verified offline. In practice, flows are added and removed while the network runs. Fast optimisers (heuristics, ILP/SMT, DRL/GNN) can propose changes, but none of them certifies worst-case delays.

The thesis places a **certified admission gate** between any proposer and the network. An action is committed only with a machine-checkable certificate showing that every admitted flow still meets its deadline. That guarantee is a safety property, and it holds only as far as the network model is accurate.

## Preliminary work

**Setting:** 1 Gbit/s switches, fixed routing, token-bucket flows $(b, r)$, at least 2 priority classes, non-preemptive static priority, deterministic network calculus for the admission gate v0 in [`tsn-admission-gate/`](tsn-admission-gate/)

**Per-hop bound** for priority class $k$ at a port of rate $C$:

$$
d_k = \frac{B_H + L_{lo} + B_k}{C - R_H} + t_{proc}, \qquad \text{valid if } R_H + R_k \le C
$$

**Burst leaving the port:**

$$
b' = b + r \cdot d_k
$$

**End-to-end bound** over the path $\mathcal{P}$:

$$
D = \sum_{h \in \mathcal{P}} d_k^{(h)}
$$

$B_H$ and $R_H$ are the total burst and rate of higher-priority flows, $L_{lo}$ is the largest lower-priority frame (it blocks because transmission is not preempted), and $B_k$ and $R_k$ are the totals for class $k$ itself.

## Repository

```
ML-Learning/
├── docs/
│   ├── projects/                # Thesis offer, prior PPO project (background for learned proposers)
│   ├── courses/
│   │   ├── ai-introduction/     # Search, constraint satisfaction, logic, KNN, Naive Bayes
│   │   └── deep-learning/       # Deep learning notes and project understandings
│   └── math/
│       ├── algebra/             # Linear algebra
│       └── probabilistics/      # Probability
├── tsn-admission-gate/          # Certified admission gate v0
│   └── tsn_gate/                # Network model, etc
├── LICENSE
└── README.md
```

## References
### Academic resources

1. J.-Y. Le Boudec, P. Thiran, *Network Calculus*, LNCS 2050, Springer, 2001.
2. L. Zhao, P. Pop, Z. Zheng, Q. Li, "Timing Analysis of AVB Traffic in TSN Networks Using Network Calculus," RTAS 2018. [PDF](https://www2.compute.dtu.dk/~paupo/publications/Zhao2017aa-Timing%20Analysis%20of%20AVB%20Traffic-.pdf)
3. M. Alshiekh et al., "Safe Reinforcement Learning via Shielding," AAAI 2018.

### Code inspiration

4. S. Bondorf, J. B. Schmitt, "The DiscoDNC v2: A Comprehensive Tool for Deterministic Network Calculus," VALUETOOLS 2014. Code: [NetCal/DNC](https://github.com/NetCal/DNC) (Java). Reference TFA/SFA/PMOO analyses to cross-check the gate's per-hop bounds.
5. A. Bouillard, *panco: Performance Analysis with Network Calculus and Optimization*, 2022. Code: [anne-bou/panco](https://github.com/anne-bou/panco) (Python). Tighter LP-based bounds; theory in A. Bouillard, M. Boyer, E. Le Corronc, *Deterministic Network Calculus*, Wiley-ISTE, 2018.
6. C. Xue, T. Zhang, Y. Zhou, M. Nixon, A. Loveless, S. Han, "Real-Time Scheduling for 802.1Qbv Time-Sensitive Networking (TSN): A Systematic Review and Experimental Study," RTAS 2024. Code: [ChuanyuXue/tsnkit](https://github.com/ChuanyuXue/tsnkit) (Python). Benchmark of TSN schedulers usable as proposers behind the gate.
