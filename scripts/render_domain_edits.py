"""LaTeX tables of the domain revision (reads results/domain/{screen,evidence}.json).

Writes results/domain/domain_edits.tex (each domain edit alone and cumulatively,
with its log evidence) and results/domain/screened_edits.tex (stage 2 on top of
the domain model, in selection order, with guard values).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/domain"
ORDER = ("R1", "D1", "G1", "D2", "D4", "D5")


def tt(label):
    return r"\texttt{" + label.replace("_", r"\_") + "}"


def main():
    screen = json.loads((OUT / "screen.json").read_text(encoding="utf-8"))
    ev = json.loads((OUT / "evidence.json").read_text(encoding="utf-8"))
    cand, full = screen["candidates"], screen["full_assessment"]
    fraud = ev["D2_D3"]
    denied = fraud["outcome_with_fraud_check"]["A_Denied"] / fraud["fraud_cases"] * 100
    denied_all = fraud["outcome_all_cases"]["A_Denied"] / ev["cases"] * 100
    evidence = {
        "R1": f"{tt('A_Complete')} before first sent offer: {ev['R1']['A_Complete_before_first_sent_offer']} "
              f"of {ev['R1']['cases_with_A_Complete']:,}",
        "D1": f"{tt('A_Pending')} without prior validation: {ev['D1']['A_Pending']['without_prior_A_Validating']} "
              f"of {ev['D1']['A_Pending']['cases']:,}; early {tt('A_Denied')} kept ({ev['D1']['A_Denied']['without_prior_A_Validating']})",
        "G1": f"{tt('O_Sent (online only)')} in {ev['G1']['cases_with_O_Sent_online_only']:,} cases",
        "D2": f"fraud check in {fraud['fraud_cases']} cases, {fraud['fraud_events_by_phase']['during_validation']} "
              f"events during validation; denied {denied:.1f}\\% vs.\\ {denied_all:.1f}\\%",
        "D4": f"{tt('W_Shortened completion')} in {ev['D4']['cases']} cases",
        "D5": f"{tt('W_Personal Loan collection')} in {ev['D5']['cases']} cases, {ev['D5']['after_A_Pending']} after "
              f"{tt('A_Pending')}",
    }
    lines = [r"\begin{tabular}{llp{6.2cm}rrrrr}", r"\hline",
             r" & & & \multicolumn{2}{c}{alone on base} & \multicolumn{3}{c}{cumulative} \\",
             r"Edit & Kind & Log evidence (all 31,509 cases) & Exact \% & Align-ET & Exact \% & Align-ET & Nodes \\", r"\hline"]
    b = cand["base"]
    lines.append(f"base & -- & abstracted IMf & {b['coverage']['fitting_percentage']:.2f} & {b['align_et_precision']:.3f} & "
                 f"{b['coverage']['fitting_percentage']:.2f} & {b['align_et_precision']:.3f} & {b['size']['nodes']} \\\\")
    active = []
    for edit in ORDER:
        active.append(edit)
        alone, cum = cand[edit], cand["+".join(sorted(active))]
        lines.append(f"{edit} & {screen['edits'][edit]['kind']} & {evidence[edit]} & "
                     f"{alone['coverage']['fitting_percentage']:.2f} & {alone['align_et_precision']:.3f} & "
                     f"{cum['coverage']['fitting_percentage']:.2f} & {cum['align_et_precision']:.3f} & {cum['size']['nodes']} \\\\")
    lines += [r"\hline", r"\end{tabular}"]
    (OUT / "domain_edits.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    domain = "+".join(sorted(screen["domain"]))
    rows = [r"\begin{tabular}{lrrrrl}", r"\hline",
            r"Candidate & Exact \% & Align-ET & Align.\ gen. & Nodes & Result \\", r"\hline"]
    stage2 = [n for n in cand if n.startswith(domain.split("+")[0]) and set(screen["domain"]) <= set(cand[n]["edits"])]
    ranked = sorted(stage2, key=lambda n: (-round(cand[n]["align_et_precision"], 4), cand[n]["size"]["nodes"]))
    selected = screen["selection"]["selected"]
    for n in ranked:
        extra = "+".join(e for e in cand[n]["edits"] if e not in screen["domain"]) or "--"
        gen = full.get(n, {}).get("alignment_generalization")
        result = "selected" if n == selected else ("tie, more nodes" if round(cand[n]["align_et_precision"], 4)
                                                    == round(cand[selected]["align_et_precision"], 4) else "lower precision")
        rows.append(f"domain model + {extra} & {cand[n]['coverage']['fitting_percentage']:.2f} & "
                    f"{cand[n]['align_et_precision']:.3f} & {'' if gen is None else f'{gen:.3f}'} & "
                    f"{cand[n]['size']['nodes']} & {result} \\\\")
    rows += [r"\hline", r"\end{tabular}"]
    (OUT / "screened_edits.tex").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines + rows))


if __name__ == "__main__":
    main()
