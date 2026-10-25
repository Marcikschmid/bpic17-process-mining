"""Create factual metric tables and figures in results/ only (no report writes)."""

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.runtime import configure_runtime
configure_runtime()
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({"font.size": 11, "axes.titlesize": 11, "axes.labelsize": 11,
                     "xtick.labelsize": 9, "ytick.labelsize": 10})

MODELS = ("inductive_miner", "heuristics_miner")
NAMES = ("Inductive Miner", "Heuristics Miner")
COLORS = ("#2364AA", "#C26818")


def main():
    source = ROOT / "results/tables/quality_metrics.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    results = data["models"]
    audit_path = ROOT / "results/tables/dead_transition_audit.json"
    structural_audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else None
    additional_sources = {}
    if structural_audit is not None:
        additional_sources[audit_path.relative_to(ROOT).as_posix()] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
        for model in MODELS:
            record = structural_audit["models"][model]
            assert record["model_sha256"] == results[model]["structure"]["model_sha256"]
            if "case_replay_upper_bound" in record:
                assert record["case_replay_upper_bound"]["input_cache_sha256"] == data["input_cache_sha256"]
    rows = []
    def add(key, label, job, field, higher=True, percentage=False):
        row = {"key": key, "label": label, "higher": higher, "percentage": percentage, "models": {}}
        for model in MODELS:
            record = results[model][job]
            value = record
            for part in field.split("."):
                value = value.get(part) if isinstance(value, dict) else None
            status = record["status"]
            if field.startswith("reachability."):
                status = record["reachability"]["status"]
            if value is None and status == "ok":
                status = "not_applicable"
            row["models"][model] = {"value": value if status == "ok" else None,
                                    "status": status, "reason": record.get("reason", "")}
        rows.append(row)
    add("token_fitness", "Token replay fitness", "token", "fitness.log_fitness")
    add("token_mean", "Token mean trace fitness", "token", "fitness.average_trace_fitness")
    add("token_fit_pct", "Token fitting cases (\\%)", "token", "fitness.perc_fit_traces", percentage=True)
    add("alignment_fitness", "Alignment fitness", "alignment", "fitness.log_fitness")
    add("alignment_mean", "Alignment mean trace fitness", "alignment", "fitness.average_trace_fitness")
    add("alignment_fit_pct", "Alignment fitting cases (\\%)", "alignment", "fitness.percFitTraces", percentage=True)
    if structural_audit is not None:
        row = {"key": "replay_bound_pct", "label": "Replay upper bound (\\%)", "higher": True,
               "percentage": True, "models": {}}
        for model in MODELS:
            value = structural_audit["models"][model].get("case_replay_upper_bound", {}).get("maximum_fitting_percentage")
            row["models"][model] = {"value": value, "status": "ok" if value is not None else "not_applicable", "reason": "Certificate-based upper bound, not a measured fitting fraction."}
        rows.append(row)
    add("token_precision", "Token precision", "token_precision", "precision")
    add("alignment_precision", "Alignment precision", "alignment_precision", "precision")
    rejected = {"key": "unfit_prefix_pct", "label": "Unfit Align-ET prefixes (\\%)",
                "higher": False, "percentage": True, "models": {}}
    for model in MODELS:
        record = results[model]["alignment_precision"]
        denominator = record.get("events", 0) - record.get("cases", 0)
        value = 100 * record["weighted_unfit_prefixes"] / denominator if record["status"] == "ok" and denominator else None
        rejected["models"][model] = {"value": value, "status": "ok" if value is not None else "not_applicable", "reason": ""}
    rows.append(rejected)
    add("generalization", "Token generalization", "token", "generalization")
    add("simplicity", "Arc-degree simplicity", "structure", "simplicity_arc_degree")
    add("nodes", "Nodes (own)", "structure", "size_own.nodes", higher=False)
    add("arcs", "Arcs (own)", "structure", "size_own.arcs", higher=False)
    add("cardoso", "Extended Cardoso (own)", "structure", "cardoso_own", higher=False)
    add("cyclomatic", "Extended Cyclomatic (own)", "structure", "reachability.value", higher=False)
    add("cyclomatic_pm4py", "PM4Py Cyclomatic$^*$", "structure", "cyclomatic_pm4py", higher=False)
    tables = ROOT / "results/tables"
    figures = ROOT / "results/figures"
    figures.mkdir(parents=True, exist_ok=True)
    csv_path = tables / "quality_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["model", "metric", "value", "status", "direction", "reason"])
        for row in rows:
            for model in MODELS:
                cell = row["models"][model]
                writer.writerow([model, row["key"], cell["value"], cell["status"],
                                 "higher" if row["higher"] else "lower", cell["reason"]])
    def formatted(cell, row):
        if cell["value"] is None:
            return "--"
        if row["key"] in ("nodes", "arcs", "cardoso", "cyclomatic", "cyclomatic_pm4py"):
            return str(cell["value"])
        return f"{cell['value']:.2f}" if row["percentage"] else f"{cell['value']:.4f}"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    tex = ["% Factual output; source results/tables/quality_metrics.json",
           f"% Source SHA256: {source_hash}", "\\begin{table}[htbp]", "\\centering", "\\small",
           "\\begin{tabular}{lrr}", "\\toprule", "Metric & IM & HM \\\\", "\\midrule"]
    for path, digest in additional_sources.items():
        tex.insert(2, f"% Additional source {path}; SHA256 {digest}")
    for i, row in enumerate(rows):
        if row["key"] == "nodes":
            tex.append("\\midrule")
        tex.append(row["label"] + " & " + " & ".join(formatted(row["models"][m], row) for m in MODELS) + " \\\\")
    tex += ["\\bottomrule", "\\end{tabular}", "\\par\\smallskip",
            "\\begin{minipage}{\\linewidth}\\scriptsize",
            "$--$: unavailable; HM Cyclomatic: unbounded state space.\\\\",
            "$^*$PM4Py 2.7.23.11: edge-name targets; own ECyM: marking targets.\\\\",
            "Complexity: smaller values; quality scores and coverage: larger values.\\\\",
            "Unfit-prefix share: smaller values; weighted nonempty prefixes.\\\\",
            "Replay upper bound: unreachable-activity certificates.\\\\",
            "Metric context~\\cite{carmona2018conformance}; size~\\cite{pedro2015simplification}; ECaM/ECyM~\\cite{lassen2009complexity}.",
            "\\end{minipage}",
            "\\caption{Baseline metrics: 31,509 cases, 475,306 completed events.}",
            "\\label{tab:baseline-quality}", "\\end{table}"]
    tex += ["% Author: explain the metric definitions, model limitations, and the PM4Py Cyclomatic discrepancy.",
            "% Definitions 13/15: Lassen and van der Aalst (2009), doi:10.1016/j.infsof.2008.08.005.",
            "% Size: de San Pedro et al. (2015), doi:10.1007/978-3-319-23063-4_30."]
    tex_path = tables / "quality_metrics.tex"
    tex_path.write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")
    md_path = tables / "quality_metrics.md"
    markdown = ["# BPIC-17: Qualitätsvergleich", "",
                "31.509 Fälle, 475.306 abgeschlossene Events; dieselbe Projektion für beide Modelle.", "",
                "| Metrik | Inductive Miner | Heuristics Miner | Richtung |", "|---|---:|---:|---|"]
    for row in rows:
        values = [formatted(row["models"][m], row) if row["models"][m]["value"] is not None
                  else row["models"][m]["status"] for m in MODELS]
        label = row["label"].replace("\\%", "%").replace("$^*$", "*")
        markdown.append(f"| {label} | {' | '.join(values)} | {'größer' if row['higher'] else 'kleiner'} |")
    markdown += ["", "*PM4Py Cyclomatic: dokumentierter Implementierungsfehler in Version 2.7.23.11; siehe docs/EVALUATION.md.",
                 "", "Token Replay ist heuristisch. HM ist unbeschränkt; ein hoher Token-Precisionwert allein belegt keine Modellqualität.",
                 "", "[Definitionen, Quellen und Einschränkungen](../../docs/EVALUATION.md)."]
    if structural_audit is not None:
        bound = structural_audit["models"]["heuristics_miner"].get("case_replay_upper_bound")
        if bound is not None:
            markdown += ["", f"HM: Mindestens {bound['provably_unfit_cases']:,} Fälle sind wegen unerreichbarer Aktivitäten nicht vollständig replaybar; höchstens {bound['maximum_fitting_cases']:,} von {bound['cases']:,} Fällen könnten passen. Das ist eine bewiesene Obergrenze, kein gemessener Alignment-Anteil."]
    missing = results["heuristics_miner"]["alignment"]
    if missing["status"] != "ok":
        markdown += ["", f"Zusätzliche HM-Alignment-Fitness: {missing['status']}; letzter gespeicherter begrenzter Lauf mit {missing.get('evaluated_cases', 'unbekannt')} vollständig berechneten Fällen. Kein Gesamtmittelwert einer Teilmenge."]
    md_path.write_text("\n".join(markdown) + "\n", encoding="utf-8", newline="\n")
    index = {row["key"]: row for row in rows}
    score_keys = ("token_fitness", "alignment_fitness", "token_precision", "alignment_precision", "generalization", "simplicity")
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 5.4), gridspec_kw={"width_ratios": [2.4, 1]})
    labels = ("Token\nfitness", "Alignment\nfitness", "Token\nprecision", "Alignment\nprecision", "Token\ngeneralization", "Arc-degree\nsimplicity")
    x = np.arange(len(score_keys))
    for mi, model in enumerate(MODELS):
        for ki, key in enumerate(score_keys):
            value = index[key]["models"][model]["value"]
            xpos = x[ki] + (mi - 0.5) * .36
            if value is None:
                axes[0].text(xpos, .035, "N/A", ha="center", va="bottom", rotation=90, fontsize=8, color=COLORS[mi])
            else:
                axes[0].bar(xpos, value, .33, color=COLORS[mi], label=NAMES[mi] if ki == 0 else None)
                axes[0].text(xpos, value + .015, f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    axes[0].set(xticks=x, xticklabels=labels, ylim=(0, 1.23), ylabel="Score (higher is better)", title="PM4Py quality metrics")
    axes[0].set_yticks(np.arange(0, 1.01, .2))
    axes[0].legend(loc="upper center", ncol=2, fontsize=10)
    for mi, model in enumerate(MODELS):
        for ki, key in enumerate(("token_fit_pct", "alignment_fit_pct")):
            value = index[key]["models"][model]["value"]
            xpos = ki + (mi - .5) * .36
            if value is not None:
                axes[1].bar(xpos, value, .33, color=COLORS[mi])
                axes[1].text(xpos, value + 1, f"{value:.1f}%", ha="center", fontsize=9)
            else:
                bound = index.get("replay_bound_pct", {}).get("models", {}).get(model, {}).get("value")
                if key == "alignment_fit_pct" and bound is not None:
                    axes[1].bar(xpos, bound, .33, facecolor="none", edgecolor=COLORS[mi], hatch="////", linewidth=1.2)
                    axes[1].text(xpos, bound + 1.5, f"≤{bound:.1f}%", ha="center", color=COLORS[mi], fontsize=9)
                else:
                    axes[1].text(xpos, 3, "N/A", ha="center", color=COLORS[mi])
    axes[1].set(xticks=[0, 1], xticklabels=["Token\nreplay", "Alignments"], ylim=(0, 114), xlim=(-.6, 1.6),
                ylabel="Fitting cases (%)", title="Case coverage")
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=.18)
        axis.set_axisbelow(True)
    fig.suptitle("BPIC-17 discovery baselines · common completion projection", fontsize=13)
    excluded = index["unfit_prefix_pct"]["models"]["heuristics_miner"]["value"]
    exclusion_note = f"HM Align-ET: {excluded:.1f}% of nonempty prefix occurrences excluded." if excluded is not None else "See evaluation records for prefix coverage."
    coverage_note = "Hatched coverage bar: certified upper bound." if structural_audit is not None else ""
    fig.text(.5, .025, "All 31,509 cases; no sampling. " + exclusion_note + "\n" + coverage_note,
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .95))
    artifacts = [csv_path, tex_path, md_path]
    for fmt in ("pdf", "svg", "png"):
        path = figures / f"quality_comparison.{fmt}"
        fig.savefig(path, dpi=180)
        artifacts.append(path)
    plt.close(fig)
    fig, axes = plt.subplots(1, 4, figsize=(8.5, 3.8))
    for axis, key, title in zip(axes, ("nodes", "arcs", "cardoso", "cyclomatic"),
                                ("Node count", "Arc count", "Extended Cardoso", "Extended Cyclomatic")):
        for mi, model in enumerate(MODELS):
            cell = index[key]["models"][model]
            value = cell["value"]
            if value is None:
                axis.text(mi, .1, cell["status"].replace("_", " "), ha="center", transform=axis.get_xaxis_transform(), rotation=90, color=COLORS[mi])
            else:
                axis.bar(mi, value, .6, color=COLORS[mi])
                axis.annotate(str(value), (mi, value), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
        axis.set(title=title, xticks=[0, 1], xticklabels=["IM", "HM"], xlim=(-.6, 1.6))
        axis.margins(y=.18)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=.18)
        axis.set_axisbelow(True)
    fig.suptitle("Independent complexity measures · lower means simpler", fontsize=13)
    fig.text(.5, .025, "All places, visible and silent transitions included. Cyclomatic requires a finite reachability graph.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .07, 1, .94))
    for fmt in ("pdf", "svg", "png"):
        path = figures / f"simplicity_comparison.{fmt}"
        fig.savefig(path, dpi=180)
        artifacts.append(path)
    plt.close(fig)
    manifest = {"source": source.relative_to(ROOT).as_posix(), "source_sha256": source_hash,
                "additional_sources": additional_sources,
                "artifacts": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}}
    (tables / "quality_artifacts.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Created {len(artifacts)} tables/figures in results/.")


if __name__ == "__main__":
    main()
