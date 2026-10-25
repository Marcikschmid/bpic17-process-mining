"""Independent Petri-net complexity measures (lower means simpler).

Cardoso and Cyclomatic: Lassen & van der Aalst (2009), definitions 13/15,
doi:10.1016/j.infsof.2008.08.005. Size (nodes/arcs): de San Pedro et al.
(2015), doi:10.1007/978-3-319-23063-4_30. No PM4Py metric is called here.
"""

from collections import deque
from time import perf_counter

import networkx as nx


def model_size(net):
    """Count all nodes and arcs, including invisible routing transitions."""
    return {"nodes": len(net.places) + len(net.transitions), "arcs": len(net.arcs)}


def extended_cardoso(net):
    """Sum, over places p, the number of distinct transition postsets at p."""
    return sum(len({frozenset(a.target for a in arc.target.out_arcs)
                    for arc in place.out_arcs}) for place in net.places)


def reachability_complexity(net, initial, final, max_states=30000, timeout=90):
    """ECyM = |E|-|V|+SCC, only after COMPLETE state-space exploration.

    E is a set of marking pairs (not a transition-labelled multigraph), as in
    the paper and PM4Py. Explore ordinary weighted P/T-net semantics, including
    silent transitions. A strict cover of an ancestor proves unboundedness by
    monotonicity; resource limits alone never prove unboundedness. A partial
    graph never receives a numeric complexity score or a soundness verdict.
    """
    started = perf_counter()
    if max_states < 1 or timeout <= 0:
        raise ValueError("Positive state/time limits required.")
    places = sorted(net.places, key=lambda p: p.name)
    index = {p: i for i, p in enumerate(places)}
    transitions = sorted(net.transitions, key=lambda t: t.name)
    for arc in net.arcs:
        if not isinstance(arc.weight, int) or arc.weight <= 0:
            raise ValueError("Only positive integer-weight ordinary P/T arcs supported.")
        if arc.properties:
            raise ValueError("Special arc properties require different semantics.")
    pre = [[(index[a.source], a.weight) for a in t.in_arcs] for t in transitions]
    post = [[(index[a.target], a.weight) for a in t.out_arcs] for t in transitions]
    def vector(marking):
        if any(p not in index or n < 0 for p, n in marking.items()):
            raise ValueError("Invalid marking.")
        return tuple(marking.get(p, 0) for p in places)
    start, end = vector(initial), vector(final)
    graph = nx.DiGraph()
    graph.add_node(start)
    parent = {start: None}
    via = {}
    queue = deque([start])
    fired = set()
    def result(status, **extra):
        return {"status": status, "states_seen": len(graph),
                "state_pairs_seen": graph.number_of_edges(),
                "seconds": round(perf_counter() - started, 3),
                "limits": {"max_states": max_states, "timeout_seconds": timeout}, **extra}
    while queue:
        marking = queue.popleft()
        for ti, transition in enumerate(transitions):
            if perf_counter() - started > timeout:
                return result("timeout", value=None)
            if not all(marking[p] >= weight for p, weight in pre[ti]):
                continue
            successor = list(marking)
            for p, weight in pre[ti]:
                successor[p] -= weight
            for p, weight in post[ti]:
                successor[p] += weight
            successor = tuple(successor)
            fired.add(transition.name)
            if successor not in parent:
                # Every parent chain is an actual firing path from the initial state.
                ancestor = marking
                while ancestor is not None:
                    if successor != ancestor and all(a <= b for a, b in zip(ancestor, successor)):
                        path, cursor = [], marking
                        while cursor != ancestor:
                            path.append(via[cursor])
                            cursor = parent[cursor]
                        path.reverse()
                        path.append(transition.name)
                        prefix, cursor = [], ancestor
                        while parent[cursor] is not None:
                            prefix.append(via[cursor])
                            cursor = parent[cursor]
                        prefix.reverse()
                        return result("unbounded", value=None, witness={
                            "place_order": [p.name for p in places],
                            "ancestor_marking": ancestor, "covering_marking": successor,
                            "prefix": prefix, "pump_sequence": path})
                    ancestor = parent[ancestor]
                if len(parent) >= max_states:
                    return result("state_limit", value=None)
                parent[successor] = marking
                via[successor] = transition.name
                queue.append(successor)
            graph.add_edge(marking, successor)
    scc = nx.number_strongly_connected_components(graph)
    can_finish = nx.ancestors(graph, end) | {end} if end in graph else set()
    proper_completion = all(not all(m[i] >= end[i] for i in range(len(end))) or m == end
                            for m in graph)
    dead = sorted(t.name for t in transitions if t.name not in fired)
    return result("ok", value=graph.number_of_edges() - len(graph) + scc,
                  strongly_connected_components=scc, bounded=True,
                  final_reachable=end in graph, option_to_complete=len(can_finish) == len(graph),
                  proper_completion=proper_completion, dead_transitions=dead,
                  sound=len(can_finish) == len(graph) and proper_completion and not dead)
