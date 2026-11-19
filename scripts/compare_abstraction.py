"""Before/after comparison of the event abstraction on ONE common log.

Precision and size are not comparable across logs with different label sets.
Therefore every model is evaluated on one common log: the abstracted log
without work-item instances (v1, all 31,509 cases; the log of the previous final
model). Models are projected onto it by hiding every label that does not occur in
this log as a silent transition (their language restricted to its labels); for
the final model these are the W_ work items except the fraud check. Their values on the completion projection are taken unchanged from
their assessment records. The hold-out summary of both pipelines is read from
results/comparison/holdout_check.json (scripts/holdout_check.py).

Writes results/abstraction/comparison.{json,csv,tex}.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
import pm4py
from pm4py.objects.log.obj import Event, EventLog, Trace
from src.finite_precision import finite_alignment_precision
from src.model_assessment import alignment_fitness, load_sequences
from src.replay_coverage import ExactReplay
from src.simplicity import extended_cardoso, model_size

OUT = ROOT / "results/abstraction"
MODELS = (  # name, label, PNML, assessment record on its own log, log of discovery
    ("inductive_miner", "IM (baseline)", "results/models/inductive_miner.pnml",
     "results/assessment/inductive_miner.json", "completion"),
    ("refined_imf", "Refined IMf (before edits)", "results/refinement/final_model.pnml",
     "results/assessment/refined_imf.json", "completion"),
    ("final_before_abstraction", "Final before abstraction (G2+G3+R3+R4)",
     "results/before_abstraction/final/final_model.pnml", "results/before_abstraction/assessment/final_model.json",
     "completion"),
    ("abstracted_base_v1", "Abstracted IMf, no work items (before edits)",
     "results/before_workitems/abstraction/base/model.pnml",
     "results/before_workitems/assessment/abstracted_base.json", "abstracted (v1)"),
    ("final_abstraction_r1", "Previous final (abstraction + R1)", "results/before_domain/final/final_model.pnml",
     "results/before_domain/assessment/final_model.json", "abstracted (v1)"),
    ("abstracted_base", "Abstracted IMf with work items (before edits)", "results/abstraction/base/model.pnml",
     "results/assessment/abstracted_base.json", "abstracted with work items"),
    ("final_model", "Final (work items + domain edits)", "results/final/final_model.pnml",
     "results/assessment/final_model.json", "abstracted with work items"),
)
HOLDOUT = ROOT / "results/comparison/holdout_check.json"
# Common log: the abstracted log WITHOUT work-item instances (v1; log of the previous final model).
# Models are projected onto it: transitions whose label does not occur in this log become silent.
COMMON = ROOT / "tmp/evaluation/abstracted_sequences_v1.json"


def evaluate(net, initial, final, sequences, log):
    machine = ExactReplay(net, initial, final)
    coverage, fits = machine.evaluate(sequences)
    precision, _ = finite_alignment_precision(log, net, initial, final)
    aligned = alignment_fitness(net, initial, final, sequences, crosscheck=6)
    return {"exact_replay_pct": coverage["fitting_percentage"], "fitting_cases": coverage["fitting_cases"],
            "align_et_precision": precision["precision"], "alignment_fitness": aligned["log_fitness"],
            "alignment_generalization": aligned["alignment_generalization"], "sound": coverage["sound"],
            "states": coverage["states"]}


def holdout_summary():
    data = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    finals = {"before_abstraction": "final_before_abstraction", "abstracted_v1": "final_abstraction_r1",
              "abstracted": "final_model"}
    return {name: {"train_only_tree_identical": p["training_only_discovery"]["identical_to_selected_tree"],
                   "test_cases_with_unseen_variant_pct": p["test_cases_with_unseen_variant_pct"],
                   "final_train_exact_pct": p["exact_replay"][finals[name]]["train"]["percentage"],
                   "final_test_exact_pct": p["exact_replay"][finals[name]]["test"]["percentage"]}
            for name, p in data["pipelines"].items()}, sha(HOLDOUT)


AG_NOTE = ("Alignment generalization of projected models counts the hidden (now silent) transitions that "
           "optimal alignments never need as unused; it is biased against projected models and therefore "
           "not shown in the report table.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only", action="store_true", help="Re-render CSV/TeX from comparison.json.")
    if parser.parse_args().render_only:
        render(json.loads((OUT / "comparison.json").read_text(encoding="utf-8")))
        return
    data, sequences = load_sequences(COMMON)
    log = EventLog([Trace([Event({"concept:name": a}) for a in s]) for s in sequences])
    alphabet = {a for s in sequences for a in s}
    dropped = set()
    rows = []
    for name, label, pnml, record, origin in MODELS:
        net, initial, final = pm4py.read_pnml(str(ROOT / pnml))
        own = json.loads((ROOT / record).read_text(encoding="utf-8"))["headline"]
        hidden = 0
        for transition in net.transitions:
            if transition.label is not None and transition.label not in alphabet:
                dropped.add(transition.label)
                transition.label = None
                hidden += 1
        common = evaluate(net, initial, final, sequences, log)
        rows.append({"model": name, "label": label, "discovered_on": origin, "pnml": pnml, "pnml_sha256": sha(ROOT / pnml),
                     "hidden_transitions": hidden, "own_log": {k: own[k] for k in
                     ("exact_replay_pct", "align_et_precision", "alignment_generalization", "nodes", "extended_cardoso",
                      "extended_cyclomatic")},
                     "abstracted_log": {**common, **model_size(net), "visible_tasks": sum(t.label is not None for t in net.transitions),
                                        "extended_cardoso": extended_cardoso(net)}})
        print(label, json.dumps(rows[-1]["abstracted_log"]), flush=True)
    checks, holdout_sha = holdout_summary()
    result = {"common_log": COMMON.relative_to(ROOT).as_posix(), "common_log_sha256": sha(COMMON),
              "hidden_labels": sorted(dropped), "models": rows, "holdout": checks,
              "holdout_source": HOLDOUT.relative_to(ROOT).as_posix(), "holdout_sha256": holdout_sha,
              "alignment_generalization_note": AG_NOTE, "implementation_sha256": sha(Path(__file__))}
    write_json(OUT / "comparison.json", result)
    render(result)
    print(json.dumps(checks, indent=1), flush=True)


def render(result):
    rows, checks = result["models"], result["holdout"]
    with (OUT / "comparison.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["model", "discovered_on", "own_exact_pct", "own_align_et", "own_nodes", "common_exact_pct",
                         "common_align_et", "common_alignment_generalization", "common_nodes", "common_visible_tasks"])
        for r in rows:
            o, c = r["own_log"], r["abstracted_log"]
            writer.writerow([r["model"], r["discovered_on"], round(o["exact_replay_pct"], 4), round(o["align_et_precision"], 6),
                             o["nodes"], round(c["exact_replay_pct"], 4), round(c["align_et_precision"], 6),
                             round(c["alignment_generalization"], 6), c["nodes"], c["visible_tasks"]])
    tex = [r"\begin{tabular}{lrrrrrrr}", r"\hline",
           r" & \multicolumn{3}{c}{Own log} & \multicolumn{4}{c}{Common abstracted log} \\",
           r"Model & Exact \% & AP & Nodes & Exact \% & AP & Nodes & Tasks \\", r"\hline"]
    for r in rows:
        o, c = r["own_log"], r["abstracted_log"]
        tex.append(f"{r['label']} & {o['exact_replay_pct']:.2f} & {o['align_et_precision']:.3f} & {o['nodes']} & "
                   f"{c['exact_replay_pct']:.2f} & {c['align_et_precision']:.3f} & {c['nodes']} & {c['visible_tasks']} \\\\")
    # Hold-out values are in results/comparison/holdout_check.tex; tasks = visible transitions,
    # nodes include the hidden (silent) transitions of projected models (stated in the report caption).
    tex += [r"\hline", r"\end{tabular}"]
    (OUT / "comparison.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
