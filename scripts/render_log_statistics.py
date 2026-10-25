"""Render factual raw-log tables and plots; outputs stay under results/."""

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
from matplotlib.ticker import PercentFormatter, StrMethodFormatter
import numpy as np


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tex(value):
    return str(value).replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def table_rows(data):
    rows = [("Cases", f"{data['cases']:,}"), ("Events", f"{data['events']:,}"),
        ("Variants (activity sequence)", f"{data['variants']:,}"),
        ("Distinct case attribute names", str(data["case_attribute_count"])),
        ("Distinct event attribute names", str(data["event_attribute_count"])),
        ("Case length: mean (events)", f"{data['case_length']['mean']:,.3f}"),
        ("Case length: population SD", f"{data['case_length']['std_population']:,.3f}")]
    for stat, name in (("mean", "mean"), ("std_population", "population SD")):
        for unit in ("days", "minutes", "seconds"):
            rows.append((f"Duration: {name} ({unit})", f"{data['case_duration'][unit][stat]:,.3f}"))
    rows.extend([("Categorical event attributes (incl. IDs)", str(data["categorical_event_attribute_count"])),
        ("Categorical event attributes (excl. IDs)", str(len(data["categorical_event_attributes_excluding_event_offer_ids"]))),
        ("Distinct activity names", str(data["distinct_activities"])),
        ("Distinct resource values (incl. system)", str(data["resource_count"])),
        ("Variants occurring once", f"{data['singleton_variants']:,}"),
        ("Top 10 variants: cases (%)", f"{data['variant_concentration']['top_10_case_percentage']:.2f}")])
    return rows


def main():
    tables, figures = ROOT / "results/tables", ROOT / "results/figures"
    source = tables / "raw_log_statistics.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    figures.mkdir(parents=True, exist_ok=True)
    with (tables / "raw_case_statistics.csv").open(encoding="utf-8", newline="") as stream:
        cases = list(csv.DictReader(stream))
    with (tables / "raw_variants.csv").open(encoding="utf-8", newline="") as stream:
        variants = list(csv.DictReader(stream))
    assert len(cases) == data["cases"] and len(variants) == data["variants"]
    for name in ("raw_case_statistics.csv", "raw_variants.csv"):
        assert sha256(tables / name) == data["exports"][name]
    rows = table_rows(data)
    heading = f"% Factual statistics; source raw_log_statistics.json; SHA256 {sha256(source)}\n"
    table = [heading, r"\begin{table}[htbp]", r"\centering", r"\small",
        r"\caption{Raw log statistics~\cite{vanDongen2017BPIC}: all lifecycle states; population SD (ddof=0); nominal IDs: EventID and OfferID.}",
        r"\label{tab:raw-log-statistics}", r"\begin{tabular}{@{}lr@{}}", r"\toprule",
        r"Statistic & Value \\", r"\midrule"]
    table.extend(tex(label) + " & " + value + r" \\" for label, value in rows)
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (tables / "raw_log_statistics.tex").write_text("\n".join(table), encoding="utf-8", newline="\n")
    attribute_table = [heading, r"\begin{table}[htbp]", r"\centering", r"\small",
        r"\caption{Raw XES attribute profile: union of names; categorical includes strings and booleans; missing = absent or null.}",
        r"\label{tab:raw-attributes}", r"\begin{tabular}{@{}llrr@{}}", r"\toprule",
        r"Attribute & Type & Distinct & Missing (\%) \\"]
    md = ["# Raw event log statistics (Assignment 3.2)", "", f"Source SHA256: `{data['input']['sha256']}`", "",
          "| Statistic | Value |", "|---|---:|", *[f"| {label} | {value} |" for label, value in rows], "",
          "Duration: max timestamp minus min timestamp in UTC; original event order retained for variants.",
          "Population SD (ddof=0); sample SD and quantiles are also in the JSON export.", "",
          "| Scope | Attribute | Classification | Distinct | Missing (%) |", "|---|---|---|---:|---:|"]
    for scope in ("case", "event"):
        attribute_table.extend([r"\midrule", r"\multicolumn{4}{l}{\textbf{" + scope.title() + r" attributes}} \\"])
        for name, item in data[f"{scope}_attributes"].items():
            kind = "nominal ID" if item["identifier"] else item["classification"]
            attribute_table.append(f"{tex(name)} & {kind} & {item['distinct_non_null']:,} & {item['missing_percentage']:.2f}" + r" \\")
            md.append(f"| {scope} | `{name}` | {kind} | {item['distinct_non_null']:,} | {item['missing_percentage']:.2f} |")
    attribute_table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (tables / "raw_attribute_profile.tex").write_text("\n".join(attribute_table), encoding="utf-8", newline="\n")
    md.extend(["", f"Timestamp order: {data['quality_checks']['cases_with_descending_timestamps']:,} cases with descending adjacent timestamps.",
        f"Alternative (activity, lifecycle) variant count: {data['activity_lifecycle_variants']:,}.",
        f"Observed event span (UTC): {data['first_event_utc']} to {data['last_event_utc']}.", ""])
    (tables / "raw_log_statistics.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
                        "axes.spines.top": False, "axes.spines.right": False,
                        "pdf.fonttype": 42, "svg.fonttype": "none"})
    outputs = []
    def save(fig, name):
        for suffix in ("pdf", "svg", "png"):
            path = figures / f"{name}.{suffix}"
            fig.savefig(path, dpi=180, facecolor="white", bbox_inches="tight")
            outputs.append(path)
        plt.close(fig)
    blue, orange = "#25699b", "#c47624"
    fig, axes = plt.subplots(2, 2, figsize=(9, 6.6), layout="constrained")
    lengths = np.array([int(c["events"]) for c in cases])
    days = np.array([float(c["duration_seconds"])/86400 for c in cases])
    for ax, values, title, xlabel in ((axes[0, 0], lengths, "Case length", "Events (all lifecycle states)"),
                                     (axes[0, 1], days, "Case duration", "Elapsed days (max - min timestamp)")):
        ax.hist(values, bins=45, color=blue, edgecolor="white", linewidth=.4)
        ax.axvline(values.mean(), color=orange, linewidth=1.6, label=f"Mean {values.mean():.2f}")
        ax.set(title=title, xlabel=xlabel, ylabel="Cases")
        ax.legend(frameon=False, fontsize=9)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    labels, values = zip(*sorted(data["lifecycle_counts"].items(), key=lambda x: x[1]))
    axes[1, 0].barh(labels, values, color=blue)
    axes[1, 0].set(title="Lifecycle frequency", xlabel="Events")
    axes[1, 0].xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    counts = np.array([int(v["cases"]) for v in variants])
    ranks = np.arange(1, len(counts)+1)
    axes[1, 1].plot(ranks, np.cumsum(counts)/len(cases), color=blue, linewidth=1.8)
    axes[1, 1].set(title="Variant coverage", xlabel="Variants, ranked by case frequency", ylabel="Cumulative share of cases", xscale="log", ylim=(0, 1.02))
    axes[1, 1].yaxis.set_major_formatter(PercentFormatter(1))
    axes[1, 1].grid(alpha=.2)
    fig.suptitle(f"Raw BPIC-17 log | {data['cases']:,} cases | {data['events']:,} events", fontsize=13)
    save(fig, "raw_log_overview")
    labels, values = zip(*sorted(data["activity_counts"].items(), key=lambda x: (x[1], x[0])))
    # Make the actual trailing blank visible without modifying the data/export.
    displayed = [label.rstrip() + (" [trailing space]" if label != label.rstrip() else "") for label in labels]
    fig, ax = plt.subplots(figsize=(8.5, 6.8), layout="constrained")
    ax.barh(displayed, values, color=blue)
    ax.set(title="Activity frequencies - unchanged raw log", xlabel="Events (all lifecycle states)")
    ax.tick_params(axis="y", labelsize=9)
    ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="x", alpha=.2)
    ax.set_axisbelow(True)
    save(fig, "raw_activity_frequencies")
    outputs += [tables / name for name in ("raw_log_statistics.tex", "raw_attribute_profile.tex", "raw_log_statistics.md")]
    manifest = {"source_sha256": sha256(source), "renderer_sha256": sha256(Path(__file__)),
                "artifacts": {p.relative_to(ROOT).as_posix(): sha256(p) for p in outputs}}
    (tables / "raw_statistics_artifacts.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Rendered {len(outputs)} raw-log artifacts", flush=True)


if __name__ == "__main__":
    main()
