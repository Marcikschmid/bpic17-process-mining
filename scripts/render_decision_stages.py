"""Compare the decision-mining feature stages and report the tuned final trees.

Reads results/decision_mining/decision_mining.json. Stages (case -> +event ->
+engineered) use the same split, test cases and FIXED CART parameters; 'final'
is the tuned engineered tree whose rules are the BPMN conditions. Writes
feature_stages.{csv,tex} and decision_tuning.tex. Balanced accuracy 1/k (k =
number of branches) = the tree never beats always predicting one branch.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/decision_mining"
STAGES = ("case", "case_event", "engineered")


def main():
    data = json.loads((OUT / "decision_mining.json").read_text(encoding="utf-8"))
    splits = [g for g in data["gateways"] if g["kind"] == "split"]
    rows = []
    for g in splits:
        stages, chosen = g["stages"], g["tuning"]["selected"]
        rows.append({"split": g["id"], "branches": len(g["outgoing"]), "test": g["test"],
                     "majority_accuracy": round(g["majority_accuracy"], 4),
                     **{f"{s}_balanced": round(stages[s]["balanced_accuracy"], 4) for s in STAGES},
                     "final_balanced": round(g["balanced_accuracy"], 4), "final_accuracy": round(g["accuracy"], 4),
                     "max_depth": chosen["max_depth"], "min_samples_leaf": chosen["min_samples_leaf"],
                     "class_weight": chosen["class_weight"] or "none", "leaves": len(g["leaves"]),
                     "cv_balanced": round(g["tuning"]["selected_cv_balanced_accuracy"], 4),
                     "final_features": " ".join(g["used_features"])})
    with (OUT / "feature_stages.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    columns = (*STAGES, "final")
    above = {c: sum(r[f"{c}_balanced"] > 1 / r["branches"] + 1e-9 for r in rows) for c in columns}
    mean = {c: sum(r[f"{c}_balanced"] for r in rows) / len(rows) for c in columns}
    tex = [r"\begin{tabular}{lrrrrrrr}", r"\hline",
           r" & & & & \multicolumn{4}{c}{Balanced accuracy (test)} \\",
           r" & & & & \multicolumn{3}{c}{fixed: depth 3, leaf 50} & tuned \\",
           r"Split & Branches & Test $n$ & Majority acc. & Case & +Event & +History & Final \\", r"\hline"]
    for r in rows:
        tex.append(f"{r['split']} & {r['branches']} & {r['test']:,} & {r['majority_accuracy']:.3f} & {r['case_balanced']:.3f} & "
                   f"{r['case_event_balanced']:.3f} & {r['engineered_balanced']:.3f} & {r['final_balanced']:.3f} \\\\")
    tex += [r"\hline", "Mean & & & & " + " & ".join(f"{mean[c]:.3f}" for c in columns) + r" \\",
            "Splits above chance ($1/k$) & & & & " + " & ".join(f"{above[c]} / {len(rows)}" for c in columns) + r" \\",
            r"\hline", r"\end{tabular}"]
    (OUT / "feature_stages.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")
    tuning = [r"\begin{tabular}{lrrlrrrr}", r"\hline",
              r"Split & Depth & Min.\ leaf & Class weight & Leaves & CV bal.\ acc. & Test bal.\ acc. & Test acc. \\", r"\hline"]
    for r in rows:
        tuning.append(f"{r['split']} & {r['max_depth']} & {r['min_samples_leaf']} & {r['class_weight']} & {r['leaves']} & "
                      f"{r['cv_balanced']:.3f} & {r['final_balanced']:.3f} & {r['final_accuracy']:.3f} \\\\")
    tuning += [r"\hline", r"\end{tabular}"]
    (OUT / "decision_tuning.tex").write_text("\n".join(tuning) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"mean_balanced_accuracy": mean, "splits_above_chance": above}, indent=1), flush=True)


if __name__ == "__main__":
    main()
