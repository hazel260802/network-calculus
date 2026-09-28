# Certified admission gate v0

`admit(state, flow) to (verdict, certificate)` for a TSN domain with 1 Gbit/s switches, fixed routing, token-bucket flows, non-preemptive static priority, and deterministic network calculus (TFA). A flow is accepted only if **every** admitted flow still meets its worst-case deadline. The certificate can be re-checked independently of the gate.

## Layout

| Path | Content |
|---|---|
| `tsn_gate/model.py` | `Flow`, `Network`, fixed BFS routing, feed-forward check |
| `tsn_gate/analysis.py` | Per-port NP-SP bound (`analyze_port`), full TFA |
| `tsn_gate/gate.py` | `admit`, `FullGate`, `IncrementalGate` |
| `tsn_gate/certificate.py` | Witnesses and the independent checker (C0–C6) |
| `tsn_gate/simulator.py` | Packet-level simulator (sanity check only) |
| `tsn_gate/topologies.py`, `workload.py` | Line and tree topologies, seeded random flows |
| `tests/` | Hand calculation, full = incremental, tampered certificates, simulation |
| `validation/panco_check.py` | Cross-check against panco |

## Reproduce

```bash
pip install -r requirements.txt
python -m pytest -q
```

To run the panco cross-check:

```bash
git clone https://github.com/anne-bou/panco ../panco && git -C ../panco checkout f035ccc5
PANCO_PATH=../panco python validation/panco_check.py --mode hop   # per hop, pure Python
PANCO_PATH=../panco python validation/panco_check.py --mode e2e   # end to end, needs lp_solve
```

Results are written to `results/panco_check_<mode>.csv`. On Windows, panco calls `lp_solve` through WSL, so install it inside WSL first: `sudo apt install lp-solve`. The scaling experiments (10–1,000 flows, time and admission rate) and the greedy proposer are not yet implemented.
