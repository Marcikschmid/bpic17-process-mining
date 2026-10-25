"""Exact complete-trace acceptance for bounded ordinary P/T nets.

Enumerate the COMPLETE reachable marking graph, then treat invisible transitions
as epsilon moves. No inserted tokens, alignment timeouts or fitness rounding.
Case weights are retained. A state limit raises, never produces a partial score.
"""
from collections import defaultdict, deque
from functools import lru_cache


class ExactReplay:
    def __init__(self, net, initial, final, max_states=50000):
        places = sorted(net.places, key=lambda p: p.name)
        index = {p: i for i, p in enumerate(places)}
        transitions = sorted(net.transitions, key=lambda t: t.name)
        for arc in net.arcs:
            if not isinstance(arc.weight, int) or arc.weight <= 0 or arc.properties:
                raise ValueError("Only positive integer-weight ordinary arcs supported")
        pre = [[(index[a.source], a.weight) for a in t.in_arcs] for t in transitions]
        post = [[(index[a.target], a.weight) for a in t.out_arcs] for t in transitions]
        start = tuple(initial.get(p, 0) for p in places)
        end = tuple(final.get(p, 0) for p in places)
        states, numbers = [start], {start: 0}
        self.edges = defaultdict(lambda: defaultdict(set))
        predecessors = defaultdict(set)
        fired = set()
        for state in states:
            source = numbers[state]
            for k, transition in enumerate(transitions):
                if not all(state[p] >= weight for p, weight in pre[k]):
                    continue
                target = list(state)
                for p, weight in pre[k]: target[p] -= weight
                for p, weight in post[k]: target[p] += weight
                target = tuple(target)
                if target not in numbers:
                    if len(states) >= max_states:
                        raise ValueError("Reachability cap reached; no exact coverage reported")
                    numbers[target] = len(states)
                    states.append(target)
                destination = numbers[target]
                self.edges[source][transition.label].add(destination)
                predecessors[destination].add(source)
                fired.add(transition)
        self.final = numbers.get(end)
        finishable = set() if self.final is None else {self.final}
        queue = deque(finishable)
        while queue:
            for previous in predecessors[queue.popleft()]:
                if previous not in finishable:
                    finishable.add(previous)
                    queue.append(previous)
        # Proper completion for a workflow net: final tokens cannot coexist
        # with leftover tokens, and the final marking has no outgoing moves.
        proper = all(s == end for s in states if all(x >= y for x, y in zip(s, end)))
        self.state_count = len(states)
        self.sound = (len(finishable) == len(states) and proper and len(fired) == len(transitions)
                      and self.final is not None and not self.edges[self.final])
        self.initial = self.closure(frozenset({0}))

    @lru_cache(maxsize=None)
    def closure(self, states):
        seen, queue = set(states), list(states)
        for state in queue:
            for target in self.edges[state].get(None, ()):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        return frozenset(seen)

    @lru_cache(maxsize=None)
    def advance(self, states, label):
        return self.closure(frozenset(t for s in states for t in self.edges[s].get(label, ())))

    def accepts(self, sequence):
        states = self.initial
        for label in sequence:
            states = self.advance(states, label)
            if not states:
                return False
        return self.final in states

    def language_equivalent(self, other, max_pairs=100000):
        """Complete equivalence of finite epsilon-NFAs; return a counterexample."""
        alphabet = {label for machine in (self, other) for edges in machine.edges.values()
                    for label in edges if label is not None}
        initial = (self.initial, other.initial)
        queue, seen = deque([(initial, ())]), {initial}
        while queue:
            (left, right), witness = queue.popleft()
            if (self.final in left) != (other.final in right):
                return {"equivalent": False, "counterexample": list(witness), "pairs": len(seen)}
            for label in sorted(alphabet):
                pair = (self.advance(left, label), other.advance(right, label))
                if pair not in seen:
                    if len(seen) >= max_pairs:
                        raise ValueError("Language equivalence cap reached; no equivalence claimed")
                    seen.add(pair)
                    queue.append((pair, (*witness, label)))
        return {"equivalent": True, "counterexample": None, "pairs": len(seen)}

    def evaluate(self, traces):
        values = {}
        accepted = []
        for trace in traces:
            sequence = tuple(trace)
            if sequence not in values:
                values[sequence] = self.accepts(sequence)
            accepted.append(values[sequence])
        count = sum(accepted)
        return {"cases": len(accepted), "fitting_cases": count,
            "fitting_percentage": 100 * count / len(accepted), "variants": len(values),
            "states": self.state_count, "sound": self.sound}, accepted

    def prefix_precision(self, traces):
        """Exact escaping-edge precision over replayable prefixes (diagnostic).

        Report excluded weighted prefixes explicitly. This is a finite-state
        ET measure, not renamed as PM4Py alignment precision.
        """
        prefixes = {}
        for trace in traces:
            for k, label in enumerate(trace):
                prefix = tuple(trace[:k])
                if prefix not in prefixes: prefixes[prefix] = [0, set()]
                prefixes[prefix][0] += 1
                prefixes[prefix][1].add(label)
        enabled_sum = escaping_sum = excluded = total = 0
        for prefix, (weight, observed) in prefixes.items():
            states = self.initial
            for label in prefix:
                states = self.advance(states, label)
                if not states: break
            total += weight
            if not states:
                excluded += weight
                continue
            enabled = {label for s in states for label in self.edges[s] if label is not None}
            enabled_sum += weight * len(enabled)
            escaping_sum += weight * len(enabled - observed)
        return {"value": 1-escaping_sum/enabled_sum if enabled_sum else 1.0,
                "weighted_prefixes": total, "excluded_weighted_prefixes": excluded,
                "weighted_enabled": enabled_sum, "weighted_escaping": escaping_sum}
