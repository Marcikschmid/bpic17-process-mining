"""Compare the decision-mining feature stages per XOR split (case -> +event -> +engineered).

Reads the 'stages' block of results/decision_mining/decision_mining.json (same
case-wise split, CART parameters and test cases for every stage). Writes
feature_stages.csv and feature_stages.tex. Balanced accuracy 1/k (k = number of
branches) = the tree never beats always predicting one branch.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/decision_mining"
STAGES = ("case", "case_event", "engineered")


def main():
    data = json.loads((OUT / "decision_mining.json").read_text(encoding="utf-8"))
    rows = []
    for g in data["gateways"]:
        if g["kind"] != "split":
            continue
        stages = g["stages"]
        rows.append({"split": g["id"], "branches": len(g["outgoing"]), "test": g["test"],
                     "majority_accuracy": round(g["majority_accuracy"], 4),
                     **{f"{s}_accuracy": round(stages[s]["accuracy"], 4) for s in STAGES},
                     **{f"{s}_balanced": round(stages[s]["balanced_accuracy"], 4) for s in STAGES},
                     "engineered_features": " ".join(stages["engineered"]["used_features"])})
    with (OUT / "feature_stages.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    informative = {s: sum(r[f"{s}_balanced"] > 1 / r["branches"] + 1e-9 for r in rows) for s in STAGES}
    mean = {s: sum(r[f"{s}_balanced"] for r in rows) / len(rows) for s in STAGES}
    tex = [r"\begin{tabular}{lrrrrrr}", r"\hline",
           r" & & & & \multicolumn{3}{c}{Balanced accuracy (test)} \\",
           r"Split & Branches & Test $n$ & Majority acc. & Case & Case+event & +Engineered \\", r"\hline"]
    for r in rows:
        tex.append(f"{r['split']} & {r['branches']} & {r['test']:,} & {r['majority_accuracy']:.3f} & {r['case_balanced']:.3f} & "
                   f"{r['case_event_balanced']:.3f} & {r['engineered_balanced']:.3f} \\\\")
    tex += [r"\hline", "Mean & & & & " + " & ".join(f"{mean[s]:.3f}" for s in STAGES) + r" \\",
            "Splits above chance ($1/k$) & & & & " + " & ".join(f"{informative[s]} / {len(rows)}" for s in STAGES) + r" \\",
            r"\hline", r"\end{tabular}"]
    (OUT / "feature_stages.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"mean_balanced_accuracy": mean, "splits_above_chance": informative}, indent=1), flush=True)


if __name__ == "__main__":
    main()
