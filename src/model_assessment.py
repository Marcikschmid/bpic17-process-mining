"""Four quality dimensions, soundness and conformance diagnostics for any Petri net.

One gate for every model (miners, refinement candidates, manual edits), all
evaluated on the same full completion projection (31,509 cases):

- Fitness: exact whole-case replay; PM4Py token replay; alignment fitness from
  exact finite-state alignments with PM4Py's cost profile and fitness formula.
- Precision: PM4Py ETC token precision; Align-ET from the finite-state solver.
- Generalization: PM4Py token-based generalization.
- Simplicity: PM4Py arc degree; own size, Extended Cardoso and ECyM.

Finite-state methods need a bounded net. Own results are cross-checked against
PM4Py on fixed-seed samples (alignment costs, prefix enabled sets).
"""
import json
import random
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path
from time import perf_counter

from pm4py.objects.log.obj import Event, EventLog, Trace

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "tmp/evaluation/projected_sequences.json"
SEED = 20261029
TOKEN_PARAMETERS = {"pm4py:param:activity_key": "concept:name", "show_progress_bar": False,
                    "multiprocessing": False, "cleaning_token_flood": False}


def load_sequences():
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    return data, [tuple(t["activities"]) for t in data["traces"]]


def event_log(data):
    return EventLog([Trace([Event({"concept:name": a}) for a in t["activities"]],
                           attributes={"concept:name": t["case_id"]}) for t in data["traces"]])


def token_metrics(log, net, initial, final):
    from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
    from pm4py.algo.evaluation.generalization.variants.token_based import get_generalization
    from pm4py.algo.evaluation.precision.variants import etconformance_token
    from pm4py.algo.evaluation.replay_fitness.variants import token_replay as token_fitness
    started = perf_counter()
    replay = token_replay.apply(log, net, initial, final,
                                parameters={**TOKEN_PARAMETERS, "consider_remaining_in_fitness": True})
    if len(replay) != len(log) or any(r is None for r in replay):
        raise ValueError("Token replay did not cover every case.")
    result = {"fitness": token_fitness.evaluate(replay), "generalization": get_generalization(net, replay),
              "fitting_cases": sum(r["trace_is_fit"] for r in replay)}
    result["precision"] = etconformance_token.apply(log, net, initial, final, parameters=dict(TOKEN_PARAMETERS))
    result["seconds"] = round(perf_counter() - started, 3)
    return result


def duplicate_labels(net):
    counts = Counter(t.label for t in net.transitions if t.label is not None)
    return sorted(label for label, n in counts.items() if n > 1)


def alignment_fitness(net, initial, final, sequences, crosscheck=24, diagnostics=False):
    """PM4Py formula: trace 1-(cost//10000)/((|t|*10000+bwc)//10000); log 1-sum(cost)/sum(|t|*10000+bwc).

    Also alignment-based generalization: PM4Py's formula 1-(sum 1/sqrt(n_t)+unused)/|T|
    with n_t counted from the case-weighted optimal alignments instead of token
    replay, which maps each label to one transition and fails on duplicate labels.
    """
    from src.finite_alignment import FiniteAligner
    started = perf_counter()
    aligner = FiniteAligner(net, initial, final)
    best_worst = aligner.align((), moves=False)["cost"]
    counts = Counter(sequences)
    labels = {t.name: t.label for t in aligner.transitions}
    costs, moves, fired = {}, Counter(), Counter()
    first_deviation = {}
    for variant in counts:
        aligned = aligner.align(variant)
        aligner.verify(variant, aligned)
        costs[variant] = aligned["cost"]
        for move in aligned["moves"]:
            if move["transition"] is not None:
                fired[move["transition"]] += counts[variant]
            if move["kind"] == "log":
                label = variant[move["event_index"]]
            elif move["kind"] == "model":
                label = labels[move["transition"]]
            else:
                continue
            moves[(move["kind"], label)] += counts[variant]
            first_deviation.setdefault(variant, (move["kind"], label))
    fitness = {v: 1 - (c // 10000) / ((len(v) * 10000 + best_worst) // 10000) for v, c in costs.items()}
    cases = len(sequences)
    unused = sum(t.name not in fired for t in net.transitions)
    generalization = 1 - (sum(1 / sqrt(n) for n in fired.values()) + unused) / len(net.transitions)
    result = {"log_fitness": 1 - sum(costs[v] * n for v, n in counts.items())
                             / sum((len(v) * 10000 + best_worst) * n for v, n in counts.items()),
              "average_trace_fitness": sum(fitness[v] * n for v, n in counts.items()) / cases,
              "percentage_of_fitting_traces": 100 * sum(n for v, n in counts.items() if fitness[v] == 1) / cases,
              "best_worst_cost": best_worst, "variants": len(counts), "cases": cases,
              "alignment_generalization": generalization, "transitions_never_fired": unused,
              "method": "exact finite-state Dijkstra alignments; PM4Py cost profile and fitness formula",
              "pm4py_crosscheck": _crosscheck_alignments(net, initial, final, costs, crosscheck)}
    result["seconds"] = round(perf_counter() - started, 3)
    if diagnostics:
        result["moves"] = moves
        result["trace_fitness"] = fitness
        result["first_deviation"] = first_deviation
    return result


def _crosscheck_alignments(net, initial, final, costs, size):
    from pm4py.algo.conformance.alignments.petri_net.variants import state_equation_a_star as a_star
    variants = sorted(costs, key=lambda v: (len(v), v))
    rng = random.Random(SEED)
    sample = list(dict.fromkeys(variants[:size // 3] + rng.sample(variants, min(size // 3, len(variants)))
                                + variants[-(size // 3):]))
    for variant in sample:
        trace = Trace([Event({"concept:name": a}) for a in variant])
        reference = a_star.apply(trace, net, initial, final, parameters={"show_progress_bar": False})
        if reference is None or reference["cost"] != costs[variant]:
            raise ValueError(f"Alignment cost disagrees with PM4Py for {variant}")
    return {"status": "ok", "variants_checked": len(sample), "seed": SEED,
            "selection": "shortest third, fixed-seed random third, longest third"}


def align_et_precision(log, net, initial, final, crosscheck=192, diagnostics=False):
    """Finite-state Align-ET; PM4Py prefix alignments re-derive sampled enabled sets."""
    from pm4py.algo.evaluation.precision import utils
    from pm4py.algo.evaluation.precision.variants import align_etconformance as reference
    from pm4py.objects.petri_net.utils.align_utils import get_visible_transitions_eventually_enabled_by_marking
    from pm4py.util import constants
    from src.finite_precision import finite_alignment_precision
    started = perf_counter()
    result, labels = finite_alignment_precision(log, net, initial, final)
    keys = list(labels)
    rng = random.Random(SEED)
    selected = list(dict.fromkeys(keys[:crosscheck // 6] + rng.sample(keys, min(2 * crosscheck // 3, len(keys)))
                                  + sorted(keys, key=len, reverse=True)[:crosscheck // 6]))
    for start in range(0, len(selected), 32):
        batch = selected[start:start + 32]
        fake = utils.form_fake_log(batch, activity_key="concept:name")
        aligned = reference.align_fake_log_stop_marking(fake, net, initial, final,
                                                        parameters={"show_progress_bar": False, "multiprocessing": False})
        reached = reference.transform_markings_from_sync_to_original_net(aligned, net)
        for key, markings in zip(batch, reached):
            expected = None if markings is None else sorted({t.label for m in markings
                for t in get_visible_transitions_eventually_enabled_by_marking(net, m) if t.label is not None})
            if labels[key] != expected:
                raise ValueError(f"Enabled set disagrees with PM4Py for prefix {key!r}")
    result["pm4py_crosscheck"] = {"status": "ok", "prefixes_checked": len(selected), "seed": SEED}
    result["seconds"] = round(perf_counter() - started, 3)
    if diagnostics:
        # Escaping edges: model-enabled next activities never observed after a prefix.
        prefixes, counts = utils.get_log_prefixes(log, activity_key="concept:name")
        escaping = defaultdict(int)
        for key, observed in prefixes.items():
            if labels[key] is None:
                continue
            last = key.split(constants.DEFAULT_VARIANT_SEP)[-1] or "<start>"
            for label in set(labels[key]) - observed:
                escaping[(last, label)] += counts[key]
        result["escaping"] = escaping
    return result


def simplicity(net, initial, final, reachability=None):
    from pm4py.algo.evaluation.simplicity.variants import arc_degree
    from src.simplicity import extended_cardoso, model_size, reachability_complexity
    reachability = reachability or reachability_complexity(net, initial, final)
    return {"arc_degree_pm4py": arc_degree.apply(net, {"k": 2}), "size_own": model_size(net),
            "extended_cardoso_own": extended_cardoso(net),
            "extended_cyclomatic_own": reachability["value"] if reachability["status"] == "ok" else None,
            "places": len(net.places), "transitions": len(net.transitions),
            "silent_transitions": sum(t.label is None for t in net.transitions)}


def assess(net, initial, final, pnml_path=None, data=None, sequences=None, log=None,
           token=True, alignments=True, diagnostics=False):
    """Return (record, diagnostics or None). Finite-state metrics need a bounded net."""
    from src.replay_coverage import ExactReplay
    from src.soundness import soundness_report
    if data is None:
        data, sequences = load_sequences()
    log = log if log is not None else event_log(data)
    record = {"soundness": soundness_report(net, initial, final, pnml_path=pnml_path),
              "duplicate_visible_labels": duplicate_labels(net)}
    bounded = record["soundness"]["classical"]["status"] == "ok"
    record["simplicity"] = simplicity(net, initial, final, record["soundness"]["classical"])
    found = None
    if token:
        record["token"] = token_metrics(log, net, initial, final)
        # PM4Py token replay keeps one transition per label (token_replay.py trans_map).
        record["token"]["valid"] = not record["duplicate_visible_labels"]
    if bounded and record["soundness"]["behavioural"]["easy_sound"]:
        coverage, fits = ExactReplay(net, initial, final).evaluate(sequences)
        record["exact_replay"] = coverage
        if alignments:
            fitness = alignment_fitness(net, initial, final, sequences, diagnostics=diagnostics)
            precision = align_et_precision(log, net, initial, final, diagnostics=diagnostics)
            if diagnostics:
                found = {"moves": fitness.pop("moves"), "trace_fitness": fitness.pop("trace_fitness"),
                         "first_deviation": fitness.pop("first_deviation"), "escaping": precision.pop("escaping"),
                         "case_fits": fits}
            record["alignment_fitness"], record["align_et_precision"] = fitness, precision
    else:
        record["finite_state_metrics"] = "not computed: net is not bounded with a reachable final marking"
    record["evaluation_input"] = {"cases": len(sequences), "events": sum(map(len, sequences)),
                                  "variants": len(set(sequences)), "cache": CACHE.relative_to(ROOT).as_posix()}
    return record, found


def headline(record):
    """Flat row with one or more values per quality dimension."""
    token = record.get("token", {}) if record.get("token", {}).get("valid") else {}
    sound = record["soundness"]
    return {"workflow_net": sound["workflow_net"], "sound": sound["sound"],
            "easy_sound": sound["behavioural"]["easy_sound"], "relaxed_sound": sound["behavioural"]["relaxed_sound"],
            "exact_replay_pct": record.get("exact_replay", {}).get("fitting_percentage"),
            "token_fitness": token.get("fitness", {}).get("log_fitness"),
            "alignment_fitness": record.get("alignment_fitness", {}).get("log_fitness"),
            "token_precision": token.get("precision"),
            "align_et_precision": record.get("align_et_precision", {}).get("precision"),
            "generalization": token.get("generalization"),
            "alignment_generalization": record.get("alignment_fitness", {}).get("alignment_generalization"),
            "arc_degree_simplicity": record["simplicity"]["arc_degree_pm4py"],
            "nodes": record["simplicity"]["size_own"]["nodes"], "arcs": record["simplicity"]["size_own"]["arcs"],
            "extended_cardoso": record["simplicity"]["extended_cardoso_own"],
            "extended_cyclomatic": record["simplicity"]["extended_cyclomatic_own"]}
