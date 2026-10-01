"""No simulated delay may exceed the network-calculus bound."""
import pytest

from tsn_gate import IncrementalGate
from tsn_gate.simulator import simulate
from tsn_gate.topologies import leaf_spine_large, leaf_spine_small
from tsn_gate.workload import random_flows


@pytest.mark.parametrize("make_net", [leaf_spine_small, leaf_spine_large])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_simulated_delays_below_bounds(make_net, seed):
    net = make_net(t_proc=1e-6)
    g = IncrementalGate(net)
    for f in random_flows(net, 60, seed=seed):
        g.admit(f)
    worst = simulate(net, g.flows, g.paths, horizon=5e-3, seed=seed)
    for f, d in worst.items():
        assert d <= g.e2e[f] * (1 + 1e-9), f"flow {f}: simulated {d} > bound {g.e2e[f]}"
