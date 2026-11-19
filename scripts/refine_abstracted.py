"""Refinement discovery on the abstracted log (tmp/evaluation/abstracted_sequences.json).

Same discovery family as scripts/refine_frequent.py (training = most frequent
variants up to a case coverage, stable lexicographic tie break; IMf with a
noise threshold), plus IMf on all cases (coverage 1.00). Every candidate is
evaluated on ALL 31,509 abstracted cases.

Selection rule of the base model (stated before the manual-edit stage):
1. sound and exact whole-case replay >= 80 % (lecture of 2026-10-29, slide 36);
2. maximize Align-ET precision (exact finite-state solver);
3. tie: fewer nodes, then lower coverage, then lower noise.
Deviation from the unabstracted refinement, stated openly: the upper band bound
82 % (own choice) is dropped. In the first abstracted sweep (log without work
items, archived in results/before_workitems/) no candidate lay in [80, 82] % (gap
77.61 -> 85.35 %); the lecture requires at least 80 %, not at most 82 %.
Since 2026-11-19 the abstracted log contains one event per started W_ work-item
instance (src/event_abstraction.py); the same grid and rule are applied to it.

Writes results/abstraction/candidates.{json,csv} and results/abstraction/base/.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
import pm4py
from pm4py.objects.log.obj import Event, EventLog, Trace
from src.finite_precision import finite_alignment_precision
from src.model_assessment import ABSTRACTED_CACHE, load_sequences
from src.replay_coverage import ExactReplay
from src.simplicity import extended_cardoso, model_size

OUT = ROOT / "results/abstraction"
COVERAGES = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00)
NOISE = (0.00, 0.03, 0.05, 0.10, 0.20)
FLOOR = 80.0


def training_set(sequences, coverage):
    counts = Counter(sequences)
    if coverage >= 1:
        return set(counts)
    selected, total = set(), 0
    for sequence in sorted(counts, key=lambda s: (-counts[s], s)):
        selected.add(sequence)
        total += counts[sequence]
        if total >= coverage * len(sequences):
            return selected


def main():
    data, sequences = load_sequences(ABSTRACTED_CACHE)
    log = EventLog([Trace([Event({"concept:name": a}) for a in s], attributes={"concept:name": t["case_id"]})
                    for s, t in zip(sequences, data["traces"])])
    path = OUT / "candidates.json"
    identity = {"input_cache_sha256": sha(ABSTRACTED_CACHE), "implementation_sha256": sha(Path(__file__))}
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if result.get("identity") != identity:
        result = {"identity": identity, "evaluation_cases": len(sequences),
                  "training_rule": "Most frequent variants up to the case coverage; stable lexicographic tie break; "
                                   "coverage 1.00 = all cases", "candidates": {}}
    for coverage in COVERAGES:
        selected = training_set(sequences, coverage)
        training = EventLog([t for t, s in zip(log, sequences) if s in selected])
        for noise in NOISE:
            key = f"abstracted_{coverage:.2f}_imf_{noise:.2f}"
            if key in result["candidates"]:
                continue
            started = perf_counter()
            tree = pm4py.discover_process_tree_inductive(training, noise_threshold=noise, multi_processing=False)
            net, initial, final = pm4py.convert_to_petri_net(tree)
            try:
                machine = ExactReplay(net, initial, final)
            except ValueError as error:
                # No exact replay/precision without the complete state space: excluded from selection.
                result["candidates"][key] = {"training_coverage": coverage, "noise_threshold": noise,
                    "training_cases": len(training), "training_variants": len(selected), "status": str(error),
                    "size": model_size(net), "tree": str(tree), "seconds": round(perf_counter() - started, 3)}
                print(f"{key}: not evaluated ({error})", flush=True)
                write_json(path, result)
                continue
            coverage_result, _ = machine.evaluate(sequences)
            precision, _ = finite_alignment_precision(log, net, initial, final)
            result["candidates"][key] = {
                "training_coverage": coverage, "noise_threshold": noise, "training_cases": len(training),
                "training_variants": len(selected), "exact_replay": coverage_result,
                "align_et_precision": precision["precision"], "size": model_size(net),
                "silent_transitions": sum(t.label is None for t in net.transitions),
                "extended_cardoso": extended_cardoso(net), "tree": str(tree),
                "seconds": round(perf_counter() - started, 3)}
            record = result["candidates"][key]
            print(f"{key}: {coverage_result['fitting_percentage']:.2f}% align-ET {precision['precision']:.4f} "
                  f"nodes {record['size']['nodes']}", flush=True)
            write_json(path, result)
    evaluated = {k: r for k, r in result["candidates"].items() if "exact_replay" in r}
    eligible = [(k, r) for k, r in evaluated.items()
                if r["exact_replay"]["sound"] and r["exact_replay"]["fitting_percentage"] >= FLOOR]
    name, chosen = min(eligible, key=lambda kr: (-kr[1]["align_et_precision"], kr[1]["size"]["nodes"],
                                                kr[1]["training_coverage"], kr[1]["noise_threshold"]))
    # Candidates with identical trees are one model; report how many parameter settings produced it.
    same = sorted(k for k, r in result["candidates"].items() if r["tree"] == chosen["tree"])
    result["selection"] = {"rule": __doc__.split("Selection rule of the base model (stated before the manual-edit stage):")[1]
                           .split("Writes")[0].strip(), "evaluated": len(evaluated),
                           "not_evaluated": sorted(set(result["candidates"]) - set(evaluated)),
                           "eligible": len(eligible), "selected": name, "identical_tree_settings": same}
    write_json(path, result)
    rows = [(k, r["training_coverage"], r["noise_threshold"], r["training_variants"], r["training_cases"],
             r["exact_replay"]["fitting_cases"], round(r["exact_replay"]["fitting_percentage"], 4),
             round(r["align_et_precision"], 6), r["size"]["nodes"], r["size"]["arcs"], r["silent_transitions"],
             r["extended_cardoso"], r["exact_replay"]["states"], r["exact_replay"]["sound"])
            for k, r in evaluated.items()]
    with (OUT / "candidates.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["candidate", "training_coverage", "noise_threshold", "training_variants", "training_cases",
                         "fitting_cases", "exact_replay_pct", "align_et_precision", "nodes", "arcs", "silent",
                         "extended_cardoso", "states", "sound"])
        writer.writerows(sorted(rows))
    folder = OUT / "base"
    folder.mkdir(parents=True, exist_ok=True)
    tree = pm4py.objects.process_tree.utils.generic.parse(chosen["tree"])
    pm4py.write_ptml(tree, str(folder / "model.ptml"))
    pm4py.write_pnml(*pm4py.convert_to_petri_net(tree), str(folder / "model.pnml"))
    write_json(folder / "selection.json", {"candidate": name, **chosen, "selection": result["selection"],
                                           "input_cache_sha256": identity["input_cache_sha256"]})
    print("SELECTED", name, chosen["exact_replay"]["fitting_percentage"], chosen["align_et_precision"],
          chosen["size"]["nodes"], "\n", chosen["tree"], flush=True)


if __name__ == "__main__":
    main()
