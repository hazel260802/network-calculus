"""Hand-computed example: every number is re-derivable on a board.

One switch sw0, three end stations. C = 1 Gbit/s, t_proc = 0.
  f1: es0 -> es1, low priority (1),  b = L = 12000 bit (1500 B), r = 12 Mbit/s
  f2: es2 -> es1, high priority (0), b = L =   800 bit (100 B),  r = 0.8 Mbit/s
Shared port: (sw0, es1).
"""
import pytest

from tsn_gate import Flow, FullGate, check_certificate
from tsn_gate.topologies import single_switch

C = 1e9
f1 = Flow(1, "es0", "es1", b=12000, r=12e6, L=12000, prio=1, deadline=100e-6)
f2 = Flow(2, "es2", "es1", b=800, r=0.8e6, L=800, prio=0, deadline=50e-6)

# hop 1 (source NICs, each flow alone)
d1_hop1 = 12000 / C                               # 12 us
d2_hop1 = 800 / C                                 # 0.8 us
b1_hop2 = 12000 + 12e6 * d1_hop1                  # 12144 bit
b2_hop2 = 800 + 0.8e6 * d2_hop1                   # 800.64 bit
# hop 2 (sw0 -> es1)
d2_hop2 = (0 + 12000 + b2_hop2) / (C - 0)         # high prio: blocked by one low frame
d1_hop2 = (b2_hop2 + 0 + b1_hop2) / (C - 0.8e6)   # low prio: behind the high burst


def run():
    g = FullGate(single_switch(3))
    assert g.admit(f1)[0]
    ok, cert = g.admit(f2)
    return g, ok, cert


def test_numbers_by_hand():
    assert d1_hop1 == pytest.approx(12e-6)
    assert b1_hop2 == pytest.approx(12144)
    assert d2_hop2 == pytest.approx(12.80064e-6)
    assert d1_hop2 == pytest.approx(12.955004e-6, rel=1e-6)


def test_gate_matches_hand_computation():
    g, ok, cert = run()
    assert ok and cert.verdict
    w1, w2 = cert.witnesses[1], cert.witnesses[2]
    assert [h.delay for h in w1.hops] == pytest.approx([d1_hop1, d1_hop2], rel=1e-12)
    assert [h.delay for h in w2.hops] == pytest.approx([d2_hop1, d2_hop2], rel=1e-12)
    assert w1.hops[1].b_in == pytest.approx(b1_hop2, rel=1e-12)
    assert w2.hops[1].b_in == pytest.approx(b2_hop2, rel=1e-12)
    assert w1.e2e == pytest.approx(d1_hop1 + d1_hop2, rel=1e-12)
    assert w2.e2e == pytest.approx(d2_hop1 + d2_hop2, rel=1e-12)
    # aggregates seen by the low-priority class at the shared port
    h = w1.hops[1]
    assert (h.B_H, h.R_H, h.L_lo) == pytest.approx((b2_hop2, 0.8e6, 0.0))
    # the high-priority class sees one low-priority frame of blocking
    assert w2.hops[1].L_lo == 12000


def test_certificate_checks():
    g, _, cert = run()
    ok, err = check_certificate(g.state.net, cert.witnesses)
    assert ok, err


def test_reject_when_deadline_too_tight():
    g = FullGate(single_switch(3))
    assert g.admit(f1)[0]
    tight = Flow(3, "es2", "es1", b=800, r=0.8e6, L=800, prio=0, deadline=10e-6)
    ok, cert = g.admit(tight)
    assert not ok and not cert.verdict
    assert any("deadline: flow 3" in v for v in cert.violations)
    assert 3 not in g.flows                 # the state is unchanged


def test_reject_when_it_breaks_an_admitted_flow():
    """The new flow meets its own deadline but pushes f1 over its (tight) deadline."""
    g = FullGate(single_switch(3))
    # alone: 12 + 12.144 = 24.144 us; with f2: 12 + 12.955 = 24.955 us
    f1_tight = Flow(1, "es0", "es1", b=12000, r=12e6, L=12000, prio=1, deadline=24.5e-6)
    assert g.admit(f1_tight)[0]
    ok, cert = g.admit(f2)
    assert not ok
    assert any("deadline: flow 1" in v for v in cert.violations)


def test_reject_unstable():
    g = FullGate(single_switch(3))
    big = Flow(1, "es0", "es1", b=12000, r=0.9e9, L=12000, prio=0, deadline=1.0)
    assert g.admit(big)[0]
    ok, cert = g.admit(Flow(2, "es2", "es1", b=12000, r=0.2e9, L=12000, prio=1, deadline=1.0))
    assert not ok and any(v.startswith("unstable") for v in cert.violations)
