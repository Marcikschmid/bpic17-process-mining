"""Exact certificates for structurally unreachable Petri-net transitions.

Find nonnegative place weights w with w*C <= 0. Every reachable marking then
satisfies w*M <= w*M0. If w*pre(t) > w*M0, t can never be enabled. Floating-point
LP is only a candidate generator; every accepted inequality is checked exactly
using fractions. This is a sufficient test, not an enumeration of all dead tasks.
"""

from fractions import Fraction


def _ordinary(net):
    if any(a.properties or not isinstance(a.weight, int) or a.weight <= 0 for a in net.arcs):
        raise ValueError("Certificates require ordinary positive-integer-weight P/T arcs.")


def verify_dead_transition_certificate(net, initial, transition_name, certificate):
    """Verify the proof against every ORIGINAL transition, without an LP solver."""
    _ordinary(net)
    places = {p.name: p for p in net.places}
    transitions = {t.name: t for t in net.transitions}
    if len(places) != len(net.places) or len(transitions) != len(net.transitions):
        raise ValueError("Unique node names required for certificate exchange.")
    if transition_name not in transitions or set(certificate) - places.keys():
        return False
    weights = {places[name]: Fraction(value) for name, value in certificate.items()}
    if any(w < 0 for w in weights.values()):
        return False
    for t in net.transitions:
        change = sum(weights.get(a.target, 0) * a.weight for a in t.out_arcs) - sum(
            weights.get(a.source, 0) * a.weight for a in t.in_arcs)
        if change > 0:
            return False
    target = transitions[transition_name]
    required = sum(weights.get(a.source, 0) * a.weight for a in target.in_arcs)
    available = sum(weights.get(p, 0) * n for p, n in initial.items())
    return required > available


def dead_transition_certificates(net, initial):
    """Find proofs; accept ONLY rational certificates that pass exact checking."""
    import numpy as np
    from scipy.optimize import linprog
    _ordinary(net)
    places = sorted(net.places, key=lambda p: p.name)
    transitions = sorted(net.transitions, key=lambda t: t.name)
    pi = {p: i for i, p in enumerate(places)}
    C = np.zeros((len(places), len(transitions)), dtype=int)
    pre = np.zeros_like(C)
    for j, t in enumerate(transitions):
        for arc in t.in_arcs:
            C[pi[arc.source], j] -= arc.weight
            pre[pi[arc.source], j] += arc.weight
        for arc in t.out_arcs:
            C[pi[arc.target], j] += arc.weight
    start = np.array([initial.get(p, 0) for p in places])
    certificates = {}
    for j, t in enumerate(transitions):
        delta = pre[:, j] - start
        candidate = linprog(np.ones(len(places)), A_ub=np.vstack([C.T, -delta]),
                            b_ub=np.r_[np.zeros(len(transitions)), -1], bounds=(0, None),
                            method="highs", options={"threads": 1, "time_limit": 2})
        if not candidate.success:
            continue
        weights = [Fraction(float(v)).limit_denominator(10000) for v in candidate.x]
        proof = {p.name: str(w) for p, w in zip(places, weights) if w}
        if verify_dead_transition_certificate(net, initial, t.name, proof):
            certificates[t.name] = proof
    return certificates
