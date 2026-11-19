"""Held-out check of the control-flow pipeline (generalization evidence).

Repeats the discovery step on the 70% training cases only (case split of
results/decision_mining/case_split.json, seed 20261018) for both pipelines:

- before abstraction: completion projection, frequent variants up to 60%
  coverage, IMf noise 0.03 (base of the earlier final model);
- abstracted without work items (previous final, archived): abstracted log v1,
  coverage/noise of results/before_workitems/abstraction/base/selection.json;
- abstracted (final): abstracted log with work items, the coverage/noise of the
  selected abstracted base (results/abstraction/base/selection.json).

If the training-only tree equals the selected tree, test cases played no role
in discovery and exact whole-case replay on the 30% test cases is a held-out
measurement. Also reports the share of test cases whose variant never occurs
in training. Writes results/comparison/holdout_check.{json,tex}.
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
from src.model_assessment import ABSTRACTED_CACHE, CACHE
from src.replay_coverage import ExactReplay

SPLIT = ROOT / "results/decision_mining/case_split.json"
BASE = json.loads((ROOT / "results/abstraction/base/selection.json").read_text(encoding="utf-8"))
BASE_V1 = json.loads((ROOT / "results/before_workitems/abstraction/base/selection.json").read_text(encoding="utf-8"))
CACHE_V1 = ROOT / "tmp/evaluation/abstracted_sequences_v1.json"
PIPELINES = {
    "before_abstraction": {"cache": CACHE, "coverage": 0.60, "noise": 0.03,
                           "reference": json.loads((ROOT / "results/refinement/final_metrics.json")
                                                   .read_text(encoding="utf-8"))["selected_candidate"]["tree"],
                           "models": {"refined_imf": ("IMf before abstraction (before edits)",
                                                      ROOT / "results/refinement/final_model.pnml"),
                                      "final_before_abstraction": ("Final before abstraction",
                                                                   ROOT / "results/before_abstraction/final/final_model.pnml")}},
    "abstracted_v1": {"cache": CACHE_V1, "coverage": BASE_V1["training_coverage"], "noise": BASE_V1["noise_threshold"],
                      "reference": BASE_V1["tree"],
                      "models": {"abstracted_base_v1": ("Abstracted IMf, no work items (before edits)",
                                                        ROOT / "results/before_workitems/abstraction/base/model.pnml"),
                                 "final_abstraction_r1": ("Previous final (abstraction + R1)",
                                                          ROOT / "results/before_domain/final/final_model.pnml")}},
    "abstracted": {"cache": ABSTRACTED_CACHE, "coverage": BASE["training_coverage"], "noise": BASE["noise_threshold"],
                   "reference": BASE["tree"],
                   "models": {"abstracted_base": ("Abstracted IMf with work items (before edits)",
                                                  ROOT / "results/abstraction/base/model.pnml"),
                              "final_model": ("Final (work items + domain edits)", ROOT / "results/final/final_model.pnml")}},
}


def check(config, train):
    data = json.loads(config["cache"].read_text(encoding="utf-8"))
    traces = {part: [tuple(t["activities"]) for t in data["traces"] if (t["case_id"] in train) == (part == "train")]
              for part in ("train", "test")}
    frequencies = Counter(traces["train"])
    selected, count = set(), 0
    for sequence in sorted(frequencies, key=lambda t: (-frequencies[t], t)):
        selected.add(sequence)
        count += frequencies[sequence]
        if count >= config["coverage"] * len(traces["train"]):
            break
    log = EventLog([Trace([Event({"concept:name": a}) for a in s]) for s in traces["train"] if s in selected])
    tree = pm4py.discover_process_tree_inductive(log, noise_threshold=config["noise"], multi_processing=False)
    seen = set(traces["train"])
    result = {"cache": config["cache"].relative_to(ROOT).as_posix(), "input_cache_sha256": sha(config["cache"]),
              "training_only_discovery": {"training_variants": len(selected), "training_cases": len(log),
                                          "training_coverage": config["coverage"], "noise_threshold": config["noise"],
                                          "tree": str(tree), "identical_to_selected_tree": str(tree) == config["reference"]},
              "test_cases_with_unseen_variant_pct": 100 * sum(s not in seen for s in traces["test"]) / len(traces["test"]),
              "exact_replay": {}}
    for name, (label, path) in config["models"].items():
        machine = ExactReplay(*pm4py.read_pnml(str(path)))
        record = {"label": label, "model": path.relative_to(ROOT).as_posix()}
        for part, seqs in traces.items():
            fitting = sum(machine.accepts(s) for s in seqs)
            record[part] = {"cases": len(seqs), "fitting": fitting, "percentage": 100 * fitting / len(seqs)}
        result["exact_replay"][name] = record
    return result


def main():
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    train = set(split["train_cases"])
    result = {"split": {"source": SPLIT.relative_to(ROOT).as_posix(), "seed": split["seed"],
                        "train_cases": len(split["train_cases"]), "test_cases": len(split["test_cases"])},
              "pipelines": {name: check(config, train) for name, config in PIPELINES.items()},
              "implementation_sha256": sha(Path(__file__))}
    write_json(ROOT / "results/comparison/holdout_check.json", result)
    rows = [r"\begin{tabular}{lrrrr}", r"\hline",
            r"Model & Train $n$ & Train exact \% & Test $n$ & Test exact \% \\", r"\hline"]
    for pipeline in result["pipelines"].values():
        for record in pipeline["exact_replay"].values():
            train_, test = record["train"], record["test"]
            rows.append(f"{record['label']} & {train_['cases']:,} & {train_['percentage']:.2f} & {test['cases']:,} & "
                        f"{test['percentage']:.2f} \\\\")
    rows.append(r"\hline")
    for name, pipeline in result["pipelines"].items():
        discovery = pipeline["training_only_discovery"]
        title = {"before_abstraction": "before abstraction", "abstracted_v1": "abstracted, no work items",
                 "abstracted": "abstracted with work items"}[name]
        rows.append(f"Train-only IMf, {title} & \\multicolumn{{4}}{{l}}{{"
                    f"{'identical' if discovery['identical_to_selected_tree'] else 'different'} tree "
                    f"({discovery['training_variants']} variants); unseen test variants "
                    f"{pipeline['test_cases_with_unseen_variant_pct']:.2f}\\,\\%}} \\\\")
    rows += [r"\hline", r"\end{tabular}"]
    (ROOT / "results/comparison/holdout_check.tex").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=1), flush=True)


if __name__ == "__main__":
    main()
