"""Report tables of the abstraction stage (factual; numbers copied from saved results).

Reads results/abstraction/candidates.json and writes discovery_candidates.tex.
The single-edit and guard-stage tables of the first abstraction (log without work
items) are only written if results/abstraction/manual_edits/ exists; since
2026-11-19 the edit stage is scripts/domain_edits.py (scripts/render_domain_edits.py).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/abstraction"


def tex(text):
    return str(text).replace("_", r"\_").replace("%", r"\%")


def main():
    candidates = json.loads((OUT / "candidates.json").read_text(encoding="utf-8"))
    selected = candidates["selection"]["selected"]
    # One row per distinct tree among evaluated candidates >= 70 % replay, best precision first.
    seen, rows = {}, []
    for name, r in candidates["candidates"].items():
        if "exact_replay" in r and r["exact_replay"]["fitting_percentage"] >= 70:
            seen.setdefault(r["tree"], []).append((name, r))
    for tree, group in seen.items():
        name, r = min(group, key=lambda nr: (nr[1]["training_coverage"], nr[1]["noise_threshold"]))
        rows.append((r, len(group), name == selected or any(n == selected for n, _ in group)))
    rows.sort(key=lambda x: -x[0]["align_et_precision"])
    lines = [r"\begin{tabular}{rrrrrrl}", r"\hline",
             r"Coverage & Noise & Settings & Exact \% & Align-ET & Nodes & \\", r"\hline"]
    for r, n, chosen in rows[:10]:
        lines.append(f"{r['training_coverage']:.2f} & {r['noise_threshold']:.2f} & {n} & "
                     f"{r['exact_replay']['fitting_percentage']:.2f} & {r['align_et_precision']:.3f} & "
                     f"{r['size']['nodes']} & {'selected' if chosen else ('$<$80\\,\\%' if r['exact_replay']['fitting_percentage'] < 80 else '')} \\\\")
    lines += [r"\hline", f"\\multicolumn{{7}}{{l}}{{{candidates['selection']['evaluated']} evaluated settings, "
              f"{len(seen)} distinct trees $\\geq$70\\,\\%; rule: $\\geq$80\\,\\% exact, max.\\ Align-ET}} \\\\",
              r"\hline", r"\end{tabular}"]
    (OUT / "discovery_candidates.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    if not (OUT / "manual_edits/screen.json").exists():
        print("written: discovery_candidates.tex", flush=True)
        return
    screen = json.loads((OUT / "manual_edits/screen.json").read_text(encoding="utf-8"))
    e = json.loads((OUT / "manual_edits/evidence.json").read_text(encoding="utf-8"))
    proof = {"R1": f"A\\_Complete before first sent offer: {e['R1']['A_Complete_before_first_sent_offer']} of "
                   f"{e['R1']['cases_with_A_Complete']:,} cases",
             "R2": f"O\\_Returned / A\\_Incomplete before first A\\_Validating: "
                   f"{e['R2']['O_Returned_before_first_A_Validating']} / {e['R2']['A_Incomplete_before_first_A_Validating']}; "
                   f"reverse order in {e['R2']['A_Incomplete_directly_followed_by_O_Returned_cases']:,} cases",
             "R3": f"A\\_Pending / A\\_Denied without prior validation: {e['R3']['A_Pending']['without_prior_A_Validating']} / "
                   f"{e['R3']['A_Denied']['without_prior_A_Validating']} cases",
             "G1": f"O\\_Sent (online only) in {e['G1']['cases_with_O_Sent_online_only']:,} cases",
             "G2": f"O\\_Create Offer after first A\\_Validating in "
                   f"{e['G2']['cases_with_O_Create_Offer_after_first_A_Validating']:,} cases"}
    base = screen["candidates"]["base"]
    lines = [r"\begin{tabular}{lp{9cm}rrr}", r"\hline", r"Edit & Log evidence (all 31,509 cases) & Exact \% & Align-ET & Nodes \\",
             r"\hline", f"base & abstracted IMf & {base['coverage']['fitting_percentage']:.2f} & "
             f"{base['align_et_precision']:.3f} & {base['size']['nodes']} \\\\"]
    for edit in sorted(screen["edits"]):
        r = screen["candidates"][edit]
        lines.append(f"{edit} & {proof[edit]} & {r['coverage']['fitting_percentage']:.2f} & {r['align_et_precision']:.3f} & "
                     f"{r['size']['nodes']} \\\\")
    lines += [r"\hline", r"\end{tabular}"]
    (OUT / "single_edits.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    selection = screen["selection"]
    lines = [r"\begin{tabular}{lrrrrll}", r"\hline",
             r"Candidate & Exact \% & Align-ET & Align.\ gen. & Nodes & Failed guard & \\", r"\hline",
             f"base & {base['coverage']['fitting_percentage']:.2f} & {base['align_et_precision']:.3f} & "
             f"{selection['base']['alignment_generalization']:.3f} & {base['size']['nodes']} & & \\\\"]
    for c in selection["checked"]:
        r = screen["candidates"][c["candidate"]]
        failed = ", ".join(k.replace("_", " ") for k, ok in c["guards"].items() if not ok)
        lines.append(f"{tex(c['candidate'])} & {r['coverage']['fitting_percentage']:.2f} & {r['align_et_precision']:.3f} & "
                     f"{c['alignment_generalization']:.3f} & {r['size']['nodes']} & {failed} & "
                     f"{'selected' if c['candidate'] == selection['selected'] else ''} \\\\")
    lines += [r"\hline", f"\\multicolumn{{7}}{{l}}{{{len(screen['candidates'])} combinations, {selection['eligible']} with "
              f"$\\geq$80\\,\\%; guards: gen.\\ drop $\\leq$0.01, arc-degree drop $\\leq$0.05, nodes $\\leq$+25\\,\\%}} \\\\",
              r"\hline", r"\end{tabular}"]
    (OUT / "guard_stage.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("written: discovery_candidates.tex, single_edits.tex, guard_stage.tex", flush=True)


if __name__ == "__main__":
    main()
