"""Full and incremental gates must agree exactly (verdicts, bounds, certificates)."""
import dataclasses

import pytest

from tsn_gate import FullGate, IncrementalGate, check_certificate, full_analysis
from tsn_gate.topologies import leaf_spine_large, leaf_spine_small
from tsn_gate.workload import random_flows


@pytest.mark.parametrize("make_net, n_req", [(leaf_spine_small, 150), (leaf_spine_large, 400)])
@pytest.mark.parametrize("seed", [0, 1])
def test_same_verdicts_and_bitwise_equal_bounds(make_net, n_req, seed):
    net = make_net()
    full, inc = FullGate(net), IncrementalGate(net)
    n_acc = 0
    for f in random_flows(net, n_req, seed=seed):
        ok_f, cert_f = full.admit(f)
        ok_i, cert_i = inc.admit(f)
        assert ok_f == ok_i, f"flow {f.id}"
        assert cert_f.state_after == cert_i.state_after
        n_acc += ok_f
    assert 0 < n_acc < n_req                    # the workload exercises both verdicts
    A = full_analysis(net, inc.flows, inc.paths)
    assert A.e2e == inc.e2e                    # exact float equality, not approx
    assert full.witnesses == inc.witnesses     # identical certificates


def test_incremental_certificate_checks_and_is_local():
    net = leaf_spine_small()
    inc = IncrementalGate(net)
    for f in random_flows(net, 80, seed=3):
        ok, cert = inc.admit(f)
        if ok:
            assert len(cert.witnesses) <= len(inc.flows)
    ok, err = check_certificate(net, inc.witnesses)
    assert ok, err[:5]


def test_checker_rejects_tampered_certificate():
    net = leaf_spine_large()
    g = FullGate(net)
    for f in random_flows(net, 40, seed=5):
        g.admit(f)
    wit = dict(g.witnesses)
    fid, w = next(iter(wit.items()))
    h0 = w.hops[-1]
    bad_hop = dataclasses.replace(h0, delay=h0.delay * 0.5)       # claim a smaller delay
    wit[fid] = dataclasses.replace(w, hops=w.hops[:-1] + (bad_hop,))
    ok, err = check_certificate(net, wit)
    assert not ok and any("below the NP-SP bound" in e for e in err)
    # Omitting a flow leaves the other aggregates as (sound) over-estimates, so only
    # the comparison with the flow database (C0) can detect it.
    wit2 = dict(g.witnesses)
    wit2.pop(fid)
    assert check_certificate(net, wit2)[0]
    assert not check_certificate(net, wit2, g.flows)[0]
    assert check_certificate(net, g.witnesses, g.flows)[0]
