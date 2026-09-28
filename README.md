# Certified Admission Control for TSN 

Preparation for the PhD **"Certified Dynamic Reconfiguration of Time-Sensitive Networks: Online Admission Control under Worst-Case Determinism Guarantees"**, LyRIDS (ECE) / CEDRIC (Cnam). Offer: [docs/projects/thesis theme.pdf](docs/projects/thesis%20theme.pdf).

## Problem formulation

TSN networks guarantee worst-case latency only if their configuration is fixed and verified offline. In practice, flows are added and removed while the network runs. Fast optimisers (heuristics, ILP/SMT, DRL/GNN) can propose changes, but none of them certifies worst-case delays.

The thesis places a **certified admission gate** between any proposer and the network. An action is committed only with a machine-checkable certificate showing that every admitted flow still meets its deadline. That guarantee is a safety property, and it holds only as far as the network model is accurate.

## Preliminary work

**Setting:** 1 Gbit/s switches, fixed routing, token-bucket flows (b, r), at least 2 priority classes, non-preemptive static priority, deterministic network calculus for the admission gate v0 in [`tsn-admission-gate/`](tsn-admission-gate/)

**Per-hop bound** for priority class k at a port of rate C:

- d_k = (B_H + L_lo + B_k) / (C − R_H) + t_proc, valid if R_H + R_k ≤ C
- Burst leaving the port: b' = b + r · d_k
- End-to-end bound: D = Σ d_k over the path

B_H and R_H are the total burst and rate of higher-priority flows, L_lo is the largest lower-priority frame (it blocks because transmission is not preempted), and B_k and R_k are the totals for class k itself.

## Repository

```
docs/projects/        Thesis offer, prior PPO project (background for learned proposers)
docs/courses/         AI introduction (search, constraint satisfaction, logic), deep learning
docs/math/            Linear algebra, probability
tsn-admission-gate/   Admission gate 
```

## Key references

1. J.-Y. Le Boudec, P. Thiran, *Network Calculus*, LNCS 2050, Springer, 2001.
2. L. Zhao, P. Pop, Z. Zheng, Q. Li, "Timing Analysis of AVB Traffic in TSN Networks Using Network Calculus," RTAS 2018. [PDF](https://www2.compute.dtu.dk/~paupo/publications/Zhao2017aa-Timing%20Analysis%20of%20AVB%20Traffic-.pdf)
3. M. Alshiekh et al., "Safe Reinforcement Learning via Shielding," AAAI 2018.