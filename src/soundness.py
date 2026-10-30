"""Structural WF-net property and behavioural soundness notions of one Petri net.

Structural: unique source and sink place, every node on a source-sink path
(PM4Py check_wfnet). Classical soundness (van der Aalst 1997): option to
complete, proper completion and no dead transitions, decided only on a
COMPLETE bounded state space (src.simplicity.reachability_complexity).
Weaker behavioural notions: easy soundness (some complete run exists) and
relaxed soundness (every transition occurs in some complete run). An
incomplete exploration only yields verdicts that a found witness proves;
everything else stays None. PM4Py Woflan is an independent cross-check.
"""
import multiprocessing
from collections import defaultdict, deque
from time import perf_counter

from pm4py.objects.petri_net.utils.check_soundness import check_wfnet

from src.simplicity import reachability_complexity


def workflow_structure(net):
    return {"workflow_net": bool(check_wfnet(net)),
            "source_places": sorted(p.name for p in net.places if not p.in_arcs),
            "sink_places": sorted(p.name for p in net.places if not p.out_arcs)}


def behavioural_properties(net, initial, final, max_states=30000):
    """Explore up to max_states markings; derive easy/relaxed soundness and safeness."""
    places = sorted(net.places, key=lambda p: p.name)
    index = {p: i for i, p in enumerate(places)}
    transitions = sorted(net.transitions, key=lambda t: t.name)
    pre = [[(index[a.source], a.weight) for a in t.in_arcs] for t in transitions]
    post = [[(index[a.target], a.weight) for a in t.out_arcs] for t in transitions]
    start = tuple(initial.get(p, 0) for p in places)
    end = tuple(final.get(p, 0) for p in places)
    states, numbers, edges, complete = [start], {start: 0}, [], True
    for state in states:
        for k in range(len(transitions)):
            if not all(state[p] >= w for p, w in pre[k]):
                continue
            target = list(state)
            for p, w in pre[k]: target[p] -= w
            for p, w in post[k]: target[p] += w
            target = tuple(target)
            if target not in numbers:
                if len(states) >= max_states:
                    complete = False
                    continue
                numbers[target] = len(states)
                states.append(target)
            edges.append((numbers[state], k, numbers[target]))
    predecessors = defaultdict(set)
    for source, _, target in edges:
        predecessors[target].add(source)
    finishing = set()
    if end in numbers:
        finishing.add(numbers[end])
        queue = deque(finishing)
        while queue:
            for previous in predecessors[queue.popleft()]:
                if previous not in finishing:
                    finishing.add(previous)
                    queue.append(previous)
    # A transition lies on a complete run iff it leads from a reachable marking
    # into a marking from which the final marking is reachable.
    on_run = {k for _, k, target in edges if target in finishing}
    missing = sorted(transitions[k].name for k in range(len(transitions)) if k not in on_run)
    maximum = max(max(s) for s in states) if places else 0
    return {"exploration_complete": complete, "states_explored": len(states),
            "easy_sound": True if end in numbers else (False if complete else None),
            "relaxed_sound": True if not missing else (False if complete else None),
            "transitions_not_on_complete_run": missing,
            "max_tokens_in_a_place": maximum,
            "safe": False if maximum > 1 else (True if complete else None)}


def _woflan_worker(pnml_path, queue):
    import pm4py
    net, initial, final = pm4py.read_pnml(pnml_path)
    queue.put(bool(pm4py.check_soundness(net, initial, final)[0]))


def woflan_crosscheck(pnml_path, timeout=120):
    """PM4Py Woflan in a separate process; a timeout yields no verdict."""
    started = perf_counter()
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_woflan_worker, args=(str(pnml_path), queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        return {"status": "timeout", "sound": None, "timeout_seconds": timeout}
    if queue.empty():
        return {"status": "error", "sound": None, "exit_code": process.exitcode}
    return {"status": "ok", "sound": queue.get(), "seconds": round(perf_counter() - started, 3)}


def soundness_report(net, initial, final, pnml_path=None, max_states=30000, timeout=90, woflan_timeout=120):
    classical = reachability_complexity(net, initial, final, max_states=max_states, timeout=timeout)
    if classical["status"] == "ok":
        verdict, reason = classical["sound"], None if classical["sound"] else "classical condition violated"
    elif classical["status"] == "unbounded":
        # A sound WF-net is bounded, so an unboundedness witness refutes soundness.
        verdict, reason = False, "unbounded"
    else:
        verdict, reason = None, f"state space {classical['status']}; no verdict"
    report = {**workflow_structure(net), "classical": classical, "sound": verdict,
              "unsound_reason": reason, "behavioural": behavioural_properties(net, initial, final, max_states)}
    if pnml_path is not None:
        report["woflan"] = woflan_crosscheck(pnml_path, woflan_timeout)
        if report["woflan"]["sound"] is not None and verdict is not None:
            report["woflan_agrees"] = report["woflan"]["sound"] == verdict
    return report
