"""Log evidence per manual edit and factual tables of the edit screening.

Reads results/manual_edits/screen.json (scripts/manual_edits.py), the full
completion projection and the conformance diagnostics of the pre-edit model
(results/assessment/refined_imf_diagnostics); writes results/manual_edits/
evidence.json, single_edits.tex, guard_stage.tex and conformance_to_edits.tex.
Evidence counts use all 31,509 cases, no filtering.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
from src.model_assessment import CACHE, load_sequences

OUT = ROOT / "results/manual_edits"
DIAGNOSTICS = ROOT / "results/assessment/refined_imf_diagnostics"
SENT = ("O_Sent (mail and online)", "O_Sent (online only)")
OUTCOMES = ("A_Pending", "A_Denied", "A_Cancelled")
# Conformance finding on the pre-edit model -> edit that targets it (precision leak = escaping
# edge of Align-ET, weighted prefixes; fitness leak = log move, cases).
ESCAPING = {("O_Create Offer", "A_Complete"): "R1", ("O_Created", "A_Complete"): "R1", ("A_Accepted", "A_Complete"): "R1",
            ("O_Sent (mail and online)", "O_Sent (mail and online)"): "R2",
            ("A_Validating", "A_Validating"): "R3", ("A_Validating", "W_Call incomplete files"): "R3",
            ("A_Complete", "O_Returned"): "R3", ("A_Complete", "A_Incomplete"): "R3"}
LOG_MOVES = {"O_Sent (online only)": "G1", "O_Cancelled": "G2, R4", "O_Refused": "G3"}


def first(sequence, labels):
    return next((i for i, a in enumerate(sequence) if a in labels), None)


def outcome(sequence):
    found = [a for a in sequence if a in OUTCOMES]
    return found[-1] if found else "none"


def evidence(sequences):
    """One counter per edit; every count is a number of cases unless named *_events."""
    found = {k: Counter() for k in ("R1", "R2", "R3", "R4", "G1", "G2", "G3")}
    for s in sequences:
        complete, sent = first(s, ("A_Complete",)), first(s, SENT)
        if complete is not None:
            found["R1"]["cases_with_A_Complete"] += 1
            found["R1"]["A_Complete_before_first_O_Sent" if sent is None or complete < sent
                        else "A_Complete_after_first_O_Sent"] += 1
        repeats = sum(a == b == SENT[0] for a, b in zip(s, s[1:]))
        found["R2"]["direct_repetition_events"] += repeats
        found["R2"]["cases_with_direct_repetition"] += repeats > 0
        validating = first(s, ("A_Validating",))
        for label, name in (("O_Returned", "O_Returned"), ("A_Incomplete", "A_Incomplete")):
            position = first(s, (label,))
            if position is not None:
                found["R3"][f"cases_with_{name}"] += 1
                found["R3"][f"{name}_before_first_A_Validating"] += validating is None or position < validating
        found["R3"]["A_Validating_direct_repetition_events"] += sum(a == b == "A_Validating" for a, b in zip(s, s[1:]))
        found["R4"][f"{outcome(s)}|{'with' if 'O_Cancelled' in s else 'without'}_O_Cancelled"] += 1
        found["G1"]["cases_with_O_Sent_online_only"] += SENT[1] in s
        found["G1"]["O_Sent_online_only_events"] += s.count(SENT[1])
        cancelled = first(s, ("A_Cancelled",))
        found["G2"]["cases_with_A_Cancelled"] += cancelled is not None
        found["G2"]["A_Cancelled_after_A_Validating"] += cancelled is not None and validating is not None and validating < cancelled
        found["G3"]["cases_with_O_Refused"] += "O_Refused" in s
        found["G3"]["cases_with_2plus_O_Refused"] += s.count("O_Refused") >= 2
    return {k: dict(sorted(v.items())) for k, v in found.items()}


def summary(edit, counts, cases):
    counts = Counter(counts)
    pct = lambda n: f"{n:,} ({100 * n / cases:.2f}\\%)"
    return {"R1": f"A\\_Complete after first O\\_Sent: {pct(counts['A_Complete_after_first_O_Sent'])}; before: {counts['A_Complete_before_first_O_Sent']:,}",
            "R2": f"direct O\\_Sent repetition in {pct(counts['cases_with_direct_repetition'])}",
            "R3": f"O\\_Returned / A\\_Incomplete before first A\\_Validating: {counts['O_Returned_before_first_A_Validating']:,} / {counts['A_Incomplete_before_first_A_Validating']:,}",
            "R4": f"O\\_Cancelled after A\\_Denied: {counts['A_Denied|with_O_Cancelled']:,}; after A\\_Cancelled: {counts['A_Cancelled|with_O_Cancelled']:,}",
            "G1": f"O\\_Sent (online only) in {pct(counts['cases_with_O_Sent_online_only'])}",
            "G2": f"A\\_Cancelled after A\\_Validating: {pct(counts['A_Cancelled_after_A_Validating'])}",
            "G3": f"$\\geq$2 O\\_Refused: {pct(counts['cases_with_2plus_O_Refused'])}"}[edit]


def main():
    screen = json.loads((OUT / "screen.json").read_text(encoding="utf-8"))
    _, sequences = load_sequences()
    found = evidence(sequences)
    cases = len(sequences)
    write_json(OUT / "evidence.json", {"input_cache_sha256": sha(CACHE), "cases": cases, "evidence": found,
                                       "implementation_sha256": sha(Path(__file__))})
    candidates, base = screen["candidates"], screen["candidates"]["base"]
    rows = [r"\begin{tabular}{llp{0.36\textwidth}rrrr}", r"\hline",
            r"Edit & Type & Log evidence (all 31,509 cases) & Exact replay \% & $\Delta$pp & Align-ET & Nodes \\", r"\hline",
            f"base & -- & refined IMf (frequent\\_0.60\\_imf\\_0.03) & {base['coverage']['fitting_percentage']:.2f} & -- & "
            f"{base['align_et_precision']:.3f} & {base['size']['nodes']} \\\\"]
    for edit in sorted(screen["edits"], key=lambda e: (e[0] != "R", e)):
        record = candidates[edit]
        replay = record["coverage"]["fitting_percentage"]
        rows.append(f"{edit} & {'restricting' if edit[0] == 'R' else 'generalizing'} & {summary(edit, found[edit], cases)} & "
                    f"{replay:.2f} & {replay - base['coverage']['fitting_percentage']:+.2f} & "
                    f"{record['align_et_precision']:.3f} & {record['size']['nodes']} \\\\")
    rows += [r"\hline", r"\end{tabular}"]
    (OUT / "single_edits.tex").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    selection = screen.get("selection", {})
    full = screen.get("full_assessment", {}).get("values", {})
    rows = [r"\begin{tabular}{lrrrrll}", r"\hline",
            r"Candidate & Exact replay \% & Align-ET & Nodes & Align. gen. & Failed guards & Result \\", r"\hline"]
    base_gen = full.get("base", selection.get("base", {})).get("alignment_generalization")
    rows.append(f"base & {base['coverage']['fitting_percentage']:.2f} & {base['align_et_precision']:.3f} & "
                f"{base['size']['nodes']} & {base_gen:.4f} & -- & reference \\\\")
    for check in selection.get("checked", []):
        record = candidates[check["candidate"]]
        failed = ", ".join(k.replace("_", " ") for k, ok in check["guards"].items() if not ok) or "none"
        rows.append(f"{check['candidate']} & {record['coverage']['fitting_percentage']:.2f} & {record['align_et_precision']:.3f} & "
                    f"{record['size']['nodes']} & {check['alignment_generalization']:.4f} & {failed} & "
                    f"{'selected' if check['passes'] else 'rejected'} \\\\")
    rows += [r"\hline", r"\end{tabular}"]
    (OUT / "guard_stage.tex").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    def read(name):
        with (DIAGNOSTICS / name).open(encoding="utf-8") as stream:
            return list(csv.DictReader(stream))
    escape = lambda text: text.replace("_", r"\_")
    rows = [r"\begin{tabular}{llp{0.40\textwidth}rl}", r"\hline",
            r"Leak & Diagnostic & Where & Weight & Edit \\", r"\hline"]
    for i, record in enumerate(read("escaping_edges.csv")[:12]):
        pair = (record["after_activity"], record["escaping_activity"])
        rows.append(f"{'precision' if i == 0 else ''} & {'escaping edge' if i == 0 else ''} & {escape(pair[0])} $\\rightarrow$ "
                    f"{escape(pair[1])} & {int(record['weighted_prefixes']):,} & {ESCAPING.get(pair, '--')} \\\\")
    rows.append(r"\hline")
    for i, record in enumerate(sorted(read("moves_per_activity.csv"), key=lambda r: -int(r["log_moves_cases"]))[:6]):
        rows.append(f"{'fitness' if i == 0 else ''} & {'log move' if i == 0 else ''} & {escape(record['activity'])} & "
                    f"{int(record['log_moves_cases']):,} & {LOG_MOVES.get(record['activity'], '--')} \\\\")
    rows += [r"\hline", r"\end{tabular}"]
    (OUT / "conformance_to_edits.tex").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(found, indent=1), flush=True)
    print("selected:", selection.get("selected"), flush=True)


if __name__ == "__main__":
    main()
