"""Held-out check of the control-flow pipeline (generalization evidence).

Repeats the refinement discovery step on the 70% training cases only (case split
of results/decision_mining/case_split.json, seed 20261018): frequent variants of
the training cases up to 60% coverage, IMf noise 0.03. If the training-only tree
equals the refined tree, test cases played no role in discovery and exact
whole-case replay on the 30% test cases is a held-out measurement. Writes
results/comparison/holdout_check.json.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
import pm4py
from pm4py.objects.log.obj import Event, EventLog, Trace
from src.model_assessment import CACHE
from src.replay_coverage import ExactReplay

SPLIT = ROOT / "results/decision_mining/case_split.json"
MODELS = {"refined_imf": ROOT / "results/refinement/final_model.pnml", "final_model": ROOT / "results/final/final_model.pnml"}


def main():
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    train = set(split["train_cases"])
    traces = {part: [tuple(t["activities"]) for t in data["traces"] if (t["case_id"] in train) == (part == "train")]
              for part in ("train", "test")}
    frequencies = Counter(traces["train"])
    selected, count = set(), 0
    for sequence in sorted(frequencies, key=lambda t: (-frequencies[t], t)):
        selected.add(sequence)
        count += frequencies[sequence]
        if count >= 0.60 * len(traces["train"]):
            break
    log = EventLog([Trace([Event({"concept:name": a}) for a in s]) for s in traces["train"] if s in selected])
    tree = pm4py.discover_process_tree_inductive(log, noise_threshold=0.03, multi_processing=False)
    refined = json.loads((ROOT / "results/refinement/final_metrics.json").read_text(encoding="utf-8"))["selected_candidate"]["tree"]
    result = {"split": {"source": SPLIT.relative_to(ROOT).as_posix(), "seed": split["seed"],
                        "train_cases": len(traces["train"]), "test_cases": len(traces["test"])},
              "training_only_discovery": {"training_variants": len(selected), "training_cases": len(log),
                                          "noise_threshold": 0.03, "tree": str(tree),
                                          "identical_to_refined_tree": str(tree) == refined},
              "exact_replay": {}, "input_cache_sha256": sha(CACHE), "implementation_sha256": sha(Path(__file__))}
    for name, path in MODELS.items():
        if not path.exists():
            continue
        machine = ExactReplay(*pm4py.read_pnml(str(path)))
        result["exact_replay"][name] = {part: {"cases": len(seqs), "fitting": sum(machine.accepts(s) for s in seqs)}
                                        for part, seqs in traces.items()}
        for part in result["exact_replay"][name].values():
            part["percentage"] = 100 * part["fitting"] / part["cases"]
    write_json(ROOT / "results/comparison/holdout_check.json", result)
    discovery = result["training_only_discovery"]
    rows = [r"\begin{tabular}{lrrrr}", r"\hline",
            r"Model & Train $n$ & Train exact \% & Test $n$ & Test exact \% \\", r"\hline"]
    for name, label in (("refined_imf", "IMf (before edits)"), ("final_model", "Final (after edits)")):
        if name in result["exact_replay"]:
            train, test = result["exact_replay"][name]["train"], result["exact_replay"][name]["test"]
            rows.append(f"{label} & {train['cases']:,} & {train['percentage']:.2f} & {test['cases']:,} & {test['percentage']:.2f} \\\\")
    rows += [r"\hline", f"Train-only IMf & \\multicolumn{{4}}{{l}}{{{'identical' if discovery['identical_to_refined_tree'] else 'different'} "
             f"tree ({discovery['training_variants']} variants, {discovery['training_cases']:,} cases)}} \\\\",
             r"\hline", r"\end{tabular}"]
    (ROOT / "results/comparison/holdout_check.tex").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=1), flush=True)


if __name__ == "__main__":
    main()
