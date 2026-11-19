"""Comparison of all discovered models: four quality dimensions and soundness.

Copies values from results/assessment/<name>.json (scripts/assess_model.py) and
the certified dead-transition / replay-ceiling audits; nothing is recomputed.
Each row states its evaluation log: C = completion projection (24 labels),
A = abstracted log (17 labels, scripts/abstract_log.py). Values of C and A rows
are not directly comparable; results/abstraction/comparison.tex evaluates all
models on the common abstracted log.
Writes results/comparison/{model_comparison,soundness_summary}.{csv,tex} and
model_comparison.md. Rows whose record is missing are skipped and listed.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = ROOT / "results/assessment"
OUT = ROOT / "results/comparison"
MODELS = (("alpha_miner", "Alpha (classic)", None),
          ("heuristics_miner", "Heuristics, dep. 0.5 (default)", None),
          ("heuristics_dep_0.7", "Heuristics, dep. 0.7", None),
          ("heuristics_dep_0.9", "Heuristics, dep. 0.9", None),
          ("heuristics_dep_0.99", "Heuristics, dep. 0.99", None),
          ("genetic_miner", "Genetic (seed 20261025)", None),
          ("inductive_miner", "Inductive (IM, full log)", None),
          ("refined_imf", "IMf refined (before edits)", None),
          ("final_before_abstraction", "Final before abstraction (IMf + G2+G3+R3+R4)",
           ROOT / "results/before_abstraction/assessment/final_model.json"),
          ("abstracted_base_v1", "Abstracted IMf, no work items (before edits)",
           ROOT / "results/before_workitems/assessment/abstracted_base.json"),
          ("final_abstraction_r1", "Previous final (abstraction + IMf + R1)",
           ROOT / "results/before_domain/assessment/final_model.json"),
          ("abstracted_base", "Abstracted IMf with work items (before edits)", None),
          ("final_model", "Final model (work items + IMf + domain edits)", None))
# Evaluation log by event count: C = completion projection, A = abstracted without work items (v1),
# W = abstracted with one event per started work-item instance (current).
LOGS = {475306: "C", 364930: "A", 491858: "W"}


def certified():
    """Certified dead-transition lower bounds and exact-replay ceilings per record name."""
    found = {}
    audit = json.loads((ROOT / "results/tables/dead_transition_audit.json").read_text(encoding="utf-8"))["models"]
    alpha = json.loads((ROOT / "results/alpha/dead_transition_certificates.json").read_text(encoding="utf-8"))["models"]
    for name, record in {**audit, **alpha}.items():
        found[name] = {"dead": record["certified_dead_count_lower_bound"],
                       "complete": record["complete_dead_transition_enumeration"],
                       "ceiling_pct": record["case_replay_upper_bound"]["maximum_fitting_percentage"]}
    genetic = json.loads((ROOT / "results/genetic/seed_20261025/dead_transition_certificates.json").read_text(encoding="utf-8"))
    found["genetic_miner"] = {"dead": genetic["certified_dead_count"], "complete": genetic["complete_dead_transition_enumeration"],
                              "ceiling_pct": genetic["case_replay_ceiling"]["maximum_fitting_percentage"]}
    return found


def number(value, digits=3):
    if value is None:
        return "n/c"
    return f"{value:.{digits}f}" if isinstance(value, float) else f"{value:,}"


def flag(value):
    return {True: "yes", False: "no", None: "n/c"}[value]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    proofs, quality, soundness, missing = certified(), [], [], []
    for name, label, path in MODELS:
        path = path or ASSESSMENT / f"{name}.json"
        if not path.exists():
            missing.append(name)
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        log = LOGS[record["evaluation_input"]["events"]]
        h, s = record["headline"], record["soundness"]
        classical, behaviour = s["classical"], s.get("behavioural", {})
        bounded = classical["status"] == "ok"
        proof = proofs.get(name, {})
        replay = h["exact_replay_pct"]
        if replay is None and "ceiling_pct" in proof:
            replay_text = f"<= {proof['ceiling_pct']:.2f} (certified)"
        else:
            replay_text = number(replay, 2)
        quality.append({"model": label, "record": name, "log": log, "sound": flag(h["sound"]), "exact_replay_pct": replay_text,
                        "token_fitness": number(h["token_fitness"]), "alignment_fitness": number(h["alignment_fitness"]),
                        "token_precision": number(h["token_precision"]), "align_et_precision": number(h["align_et_precision"]),
                        "token_generalization": number(h["generalization"]),
                        "alignment_generalization": number(h.get("alignment_generalization")),
                        "arc_degree": number(h["arc_degree_simplicity"]), "nodes": number(h["nodes"]),
                        "extended_cardoso": number(h["extended_cardoso"]), "extended_cyclomatic": number(h["extended_cyclomatic"])})
        dead = classical.get("dead_transitions") if bounded else None
        dead_text = (str(len(dead)) if dead is not None else
                     (f"{'' if proof.get('complete') else '>= '}{proof['dead']} (certified)" if "dead" in proof else "n/c"))
        woflan = s.get("woflan", {})
        soundness.append({"model": label, "record": name, "workflow_net": flag(s["workflow_net"]),
                          "bounded": "yes" if bounded else ("no (witness)" if classical["status"] == "unbounded" else "n/c"),
                          "safe": flag(behaviour.get("safe")) if bounded else "no",
                          "option_to_complete": flag(classical.get("option_to_complete")),
                          "proper_completion": flag(classical.get("proper_completion")),
                          "dead_transitions": dead_text, "sound": flag(h["sound"]),
                          "easy_sound": flag(h["easy_sound"]), "relaxed_sound": flag(h["relaxed_sound"]),
                          "woflan": flag(woflan.get("sound")) if woflan.get("status") == "ok" else woflan.get("status", "n/c")})
    for rows, stem in ((quality, "model_comparison"), (soundness, "soundness_summary")):
        with (OUT / f"{stem}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    tex = lambda value: str(value).replace("_", r"\_").replace("<=", r"$\leq$").replace(">=", r"$\geq$")
    quality_tex = [r"\begin{tabular}{llrrrrrrrrrrr}", r"\hline",
                   r" & & \multicolumn{3}{c}{Fitness} & \multicolumn{2}{c}{Precision} & \multicolumn{2}{c}{Generalization} & \multicolumn{4}{c}{Simplicity} \\",
                   r"Model & Log & Exact \% & Token & Align. & Token & Align-ET & Token & Align. & Arc deg. & Nodes & Cardoso & ECyM \\", r"\hline"]
    for r in quality:
        quality_tex.append(" & ".join(tex(r[k]) for k in ("model", "log", "exact_replay_pct", "token_fitness", "alignment_fitness",
                                                          "token_precision", "align_et_precision", "token_generalization",
                                                          "alignment_generalization", "arc_degree", "nodes",
                                                          "extended_cardoso", "extended_cyclomatic")) + r" \\")
    quality_tex += [r"\hline", r"\multicolumn{13}{l}{Log: C = completion projection (24 labels), A = abstracted log "
                    r"without work items (17 labels), W = abstracted log with work items (24 labels); "
                    r"values on different logs are not directly comparable.} \\", r"\hline", r"\end{tabular}"]
    sound_tex = [r"\begin{tabular}{lllllllllll}", r"\hline",
                 r"Model & WF-net & Bounded & Safe & Opt.\ compl. & Proper compl. & Dead trans. & Sound & Easy & Relaxed & Woflan \\",
                 r"\hline"]
    for r in soundness:
        sound_tex.append(" & ".join(tex(r[k]) for k in ("model", "workflow_net", "bounded", "safe", "option_to_complete",
                                                        "proper_completion", "dead_transitions", "sound", "easy_sound",
                                                        "relaxed_sound", "woflan")) + r" \\")
    sound_tex += [r"\hline", r"\end{tabular}"]
    (OUT / "model_comparison.tex").write_text("\n".join(quality_tex) + "\n", encoding="utf-8", newline="\n")
    # Compact main-body version: the refinement path IM -> IMf -> final, one column per model.
    order = ("inductive_miner", "refined_imf", "final_before_abstraction", "abstracted_base", "final_model")
    path = {r["record"]: r for r in quality if r["record"] in order}
    if len(path) == len(order):
        compact = [r"\begin{tabular}{llrrrrr}", r"\hline",
                   r"Criterion & Measure & IM & IMf & Final (before) & Abstr.\ IMf & Final \\", r"\hline",
                   "& evaluation log & " + " & ".join(path[r]["log"] for r in order) + r" \\"]
        for criterion, measure, key in (("Fitness", "exact replay \\%", "exact_replay_pct"), ("", "alignment", "alignment_fitness"),
                                        ("Precision", "Align-ET", "align_et_precision"),
                                        ("Generalization", "alignment", "alignment_generalization"),
                                        ("Simplicity", "arc degree", "arc_degree"), ("", "nodes", "nodes"),
                                        ("", "Ext.\\ Cardoso", "extended_cardoso"), ("", "ECyM", "extended_cyclomatic")):
            compact.append(f"{criterion} & {measure} & " + " & ".join(tex(path[r][key]) for r in order) + r" \\")
        compact += [r"\hline", r"\multicolumn{7}{l}{C = completion projection, A = abstracted log; "
                    r"common-log comparison: results/abstraction/comparison.tex} \\", r"\hline", r"\end{tabular}"]
        (OUT / "final_quality.tex").write_text("\n".join(compact) + "\n", encoding="utf-8", newline="\n")
    (OUT / "soundness_summary.tex").write_text("\n".join(sound_tex) + "\n", encoding="utf-8", newline="\n")
    md = ["# Model comparison (generated by scripts/render_model_comparison.py)", "",
          "All models evaluated on all 31,509 cases. Column `log`: C = completion projection (24 labels), "
          "A = abstracted log (17 labels, [event abstraction](../../docs/EVENT_ABSTRACTION.md)); C and A values are "
          "not directly comparable, see [common-log comparison](../abstraction/comparison.csv). `n/c` = not computable "
          "(finite-state metric on an unbounded net). `(certified)` = exact-replay ceiling or dead-transition count "
          "from exact rational certificates, not from replay.", "", "## Quality dimensions", "",
          "| " + " | ".join(quality[0]) + " |", "|" + "---|" * len(quality[0])]
    md += ["| " + " | ".join(str(v) for v in r.values()) + " |" for r in quality]
    md += ["", "## Soundness", "", "| " + " | ".join(soundness[0]) + " |", "|" + "---|" * len(soundness[0])]
    md += ["| " + " | ".join(str(v) for v in r.values()) + " |" for r in soundness]
    if missing:
        md += ["", "Missing records (not assessed yet): " + ", ".join(f"`{m}`" for m in missing)]
    (OUT / "model_comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(quality)} models; missing: {missing or 'none'}", flush=True)


if __name__ == "__main__":
    main()
