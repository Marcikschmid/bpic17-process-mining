"""Exact net checks that need no complete state space (valid for unbounded nets).

- workflow_paths: WF-net definition (van der Aalst 1997) on DIRECTED paths: one
  source place, one sink place, every node on a directed source-sink path.
  PM4Py check_wfnet only tests connectivity of the undirected graph.
- final_marking_certificate: Farkas certificate y with y*C >= 0 and
  y*Mf < y*M0. y*M never decreases when a transition fires, so Mf is unreachable
  (no complete run exists). Sufficient test only; the LP merely proposes y, every
  accepted certificate is verified with exact fractions.
- deterministic_replay: exact whole-case replay for nets with injective visible
  labels and no silent transitions, where every trace fixes one firing sequence.
"""
from collections import Counter
from fractions import Fraction


def _name(node):
    return getattr(node, "label", None) or node.name


def workflow_paths(net):
    sources = [p for p in net.places if not p.in_arcs]
    sinks = [p for p in net.places if not p.out_arcs]
    result = {"source_places": sorted(p.name for p in sources), "sink_places": sorted(p.name for p in sinks)}
    if len(sources) != 1 or len(sinks) != 1:
        return {"workflow_net": False, **result, "reason": "not exactly one source and one sink place"}

    def reach(start, step):
        seen, stack = {start}, [start]
        while stack:
            for node in step(stack.pop()):
                if node not in seen:
                    seen.add(node)
                    stack.append(node)
        return seen
    forward = reach(sources[0], lambda n: [a.target for a in n.out_arcs])
    backward = reach(sinks[0], lambda n: [a.source for a in n.in_arcs])
    nodes = [*net.places, *net.transitions]
    unreached = sorted(_name(n) for n in nodes if n not in forward)
    stuck = sorted(_name(n) for n in nodes if n not in backward)
    return {"workflow_net": not unreached and not stuck, **result,
            "nodes_without_directed_path_from_source": unreached, "nodes_without_directed_path_to_sink": stuck}


def verify_final_marking_certificate(net, initial, final, certificate):
    names = {p.name for p in net.places}
    if len(names) != len(net.places) or set(certificate) - names:
        return False
    y = {p: Fraction(certificate.get(p.name, "0")) for p in net.places}
    for t in net.transitions:
        if sum(y[a.target] * a.weight for a in t.out_arcs) < sum(y[a.source] * a.weight for a in t.in_arcs):
            return False
    return sum(y[p] * n for p, n in final.items()) < sum(y[p] * n for p, n in initial.items())


def final_marking_certificate(net, initial, final):
    import numpy as np
    from scipy.optimize import linprog
    places = sorted(net.places, key=lambda p: p.name)
    transitions = sorted(net.transitions, key=lambda t: t.name)
    index = {p: i for i, p in enumerate(places)}
    C = np.zeros((len(places), len(transitions)))
    for j, t in enumerate(transitions):
        for arc in t.in_arcs:
            C[index[arc.source], j] -= arc.weight
        for arc in t.out_arcs:
            C[index[arc.target], j] += arc.weight
    delta = np.array([final.get(p, 0) - initial.get(p, 0) for p in places])
    candidate = linprog(np.zeros(len(places)), A_ub=np.vstack([-C.T, delta]), b_ub=np.r_[np.zeros(len(transitions)), -1],
                        bounds=(-100, 100), method="highs", options={"threads": 1, "time_limit": 10})
    if not candidate.success:
        return {"status": "no_certificate", "verdict": None,
                "note": "No Farkas vector found; the marking equation may be solvable, reachability undecided."}
    weights = [Fraction(float(v)).limit_denominator(10000) for v in candidate.x]
    proof = {p.name: str(w) for p, w in zip(places, weights) if w}
    if not verify_final_marking_certificate(net, initial, final, proof):
        return {"status": "rejected_candidate", "verdict": None}
    return {"status": "certified", "final_marking_reachable": False, "certificate": proof,
            "method": "Farkas: y*C >= 0 for every transition and y*Mf < y*M0; exact rational verification"}


def deterministic_replay(net, initial, final, sequences):
    labels = Counter(t.label for t in net.transitions)
    if None in labels or max(labels.values()) > 1:
        raise ValueError("Deterministic replay needs injective labels and no silent transitions.")
    by_label = {t.label: t for t in net.transitions}
    target = {p: n for p, n in final.items() if n}
    counts, fit, first = Counter(sequences), 0, Counter()
    for variant, n in counts.items():
        marking = Counter(dict(initial))
        for activity in variant:
            t = by_label.get(activity)
            if t is None or any(marking[a.source] < a.weight for a in t.in_arcs):
                first[("not_enabled" if t else "unknown_label", activity)] += n
                break
            for a in t.in_arcs:
                marking[a.source] -= a.weight
            for a in t.out_arcs:
                marking[a.target] += a.weight
        else:
            if {p: k for p, k in marking.items() if k} == target:
                fit += n
            else:
                first[("wrong_final_marking", "")] += n
    cases = sum(counts.values())
    return {"cases": cases, "variants": len(counts), "fitting_cases": fit, "fitting_percentage": 100 * fit / cases,
            "first_failure": [{"kind": k, "activity": a, "cases": n} for (k, a), n in first.most_common()],
            "method": "exact: injective labels, no silent transitions; fire each case in order, then compare with the final marking"}
