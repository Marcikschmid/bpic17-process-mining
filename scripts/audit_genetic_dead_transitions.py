"""Exact dead-transition and replay-ceiling audit of the saved Genetic Miner net.

Dead: nonnegative place subinvariant certificates (src.validation), verified with
exact fractions. Not dead: shortest firing sequence from the initial marking,
found by breadth-first search over at most --max-states markings and replayed
with PM4Py firing semantics. Certified plus witnessed transitions covering the
net make the dead list complete; otherwise the rest stays undecided. Replay
ceiling: cases containing an unreachable activity cannot fit (as in
scripts/audit_dead_transitions.py); a Farkas certificate for the final marking
(src.net_certificates) proves that no case can fit. The model is not changed.
"""
import argparse
import hashlib
import json
import sys
from collections import deque
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.runtime import configure_runtime
configure_runtime()
import pm4py
from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking
from src.net_certificates import final_marking_certificate, workflow_paths
from src.validation import dead_transition_certificates

MODEL = ROOT / "results/genetic/seed_20261025/models/genetic_miner.pnml"
OUT = ROOT / "results/genetic/seed_20261025/dead_transition_certificates.json"
CACHE = ROOT / "tmp/evaluation/projected_sequences.json"
IMPLEMENTATION = ("src/validation.py", "src/net_certificates.py", "scripts/audit_genetic_dead_transitions.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def firing_witnesses(net, initial, wanted, max_states):
    """Shortest firing sequence ending with each wanted transition; BFS in name order."""
    places = sorted(net.places, key=lambda p: p.name)
    index = {p: i for i, p in enumerate(places)}
    transitions = sorted(net.transitions, key=lambda t: t.name)
    pre = [[(index[a.source], a.weight) for a in t.in_arcs] for t in transitions]
    post = [[(index[a.target], a.weight) for a in t.out_arcs] for t in transitions]
    start = tuple(initial.get(p, 0) for p in places)
    parent, queue, found = {start: None}, deque([start]), {}
    while queue and len(found) < len(wanted):
        state = queue.popleft()
        for k, t in enumerate(transitions):
            if not all(state[p] >= w for p, w in pre[k]):
                continue
            if t.name in wanted and t.name not in found:
                path, node = [t.name], state
                while parent[node] is not None:
                    node, name = parent[node]
                    path.append(name)
                found[t.name] = path[::-1]
            target = list(state)
            for p, w in pre[k]: target[p] -= w
            for p, w in post[k]: target[p] += w
            target = tuple(target)
            if target not in parent and len(parent) < max_states:
                parent[target] = (state, t.name)
                queue.append(target)
    by_name = {t.name: t for t in net.transitions}
    for sequence in found.values():
        marking = Marking(initial)
        for name in sequence:
            if not semantics.is_enabled(by_name[name], net, marking):
                raise ValueError(f"Witness step {name} not enabled under PM4Py semantics")
            marking = semantics.execute(by_name[name], net, marking)
    return dict(sorted(found.items())), len(parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-states", type=int, default=30000)
    args = parser.parse_args()
    net, initial, final = pm4py.read_pnml(str(MODEL))
    labels = {t.name: t.label for t in net.transitions}
    proofs = dict(sorted(dead_transition_certificates(net, initial).items()))
    witnesses, states = firing_witnesses(net, initial, set(labels) - proofs.keys(), args.max_states)
    undecided = sorted(set(labels) - proofs.keys() - witnesses.keys())
    # A label is unreachable only if EVERY transition carrying it is dead.
    unreachable = sorted(label for label in {l for l in labels.values() if l is not None}
                         if all(n in proofs for n, l in labels.items() if l == label))
    traces = json.loads(CACHE.read_text(encoding="utf-8"))["traces"]
    affected = sum(any(a in unreachable for a in t["activities"]) for t in traces)
    final_proof = final_marking_certificate(net, initial, final)
    certified = final_proof["status"] == "certified"
    ceiling = 0 if certified else len(traces) - affected
    record = {
        "model": MODEL.relative_to(ROOT).as_posix(), "model_sha256": sha(MODEL),
        "method": "Dead: nonnegative place subinvariants, exact rational verification. Fireable: BFS shortest "
                  "firing sequence replayed with PM4Py semantics. Final marking: Farkas certificate on the "
                  "marking equation, exact rational verification.",
        "workflow_net_directed_paths": workflow_paths(net),
        "transitions": len(labels), "silent_transitions": sum(l is None for l in labels.values()),
        "certified_dead_count": len(proofs), "fireable_witnessed_count": len(witnesses),
        "undecided_count": len(undecided), "complete_dead_transition_enumeration": not undecided,
        "witness_search": {"max_states": args.max_states, "states_stored": states,
                           "longest_witness": max(map(len, witnesses.values()), default=0)},
        "dead_silent_transitions": sum(labels[n] is None for n in proofs),
        "activity_labels": sorted(labels[n] for n in proofs if labels[n] is not None),
        "unreachable_activity_labels": unreachable,
        "undecided_transitions": undecided,
        "certificates": proofs,
        "fireable_witnesses": witnesses,
        "transition_labels": dict(sorted(labels.items())),
        "case_replay_upper_bound": {
            "basis": "cases containing an unreachable activity label cannot fit",
            "cases": len(traces), "provably_unfit_cases": affected, "maximum_fitting_cases": len(traces) - affected,
            "maximum_fitting_percentage": 100 * (len(traces) - affected) / len(traces)},
        "final_marking": final_proof,
        "case_replay_ceiling": {
            "basis": "final marking unreachable from the initial marking (certified)" if certified
                     else "label bound only; final marking reachability undecided",
            "cases": len(traces), "maximum_fitting_cases": ceiling,
            "maximum_fitting_percentage": 100 * ceiling / len(traces)},
        "input_cache_sha256": sha(CACHE), "pm4py": version("pm4py"), "scipy": version("scipy"),
        "implementation_sha256": {p: sha(ROOT / p) for p in IMPLEMENTATION}}
    write_json(OUT, record)
    print(json.dumps({k: record[k] for k in ("certified_dead_count", "fireable_witnessed_count", "undecided_count",
                                             "unreachable_activity_labels", "case_replay_upper_bound",
                                             "case_replay_ceiling")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
