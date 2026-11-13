"""Build the abstracted sequence cache and the evidence audit of src/event_abstraction.py.

Streams the unchanged raw XES once. Checks that its completion events reproduce
tmp/evaluation/projected_sequences.json (same cases, order and labels), applies
the abstraction rules with the original timestamps and writes:

- tmp/evaluation/abstracted_sequences.json: same schema as the projection cache
  (input of refinement, manual edits, final assessment and decision mining);
- results/abstraction/abstraction_audit.json: evidence per rule, removed and
  collapsed events, log statistics before/after;
- results/abstraction/abstraction_rules.tex: report table.
"""
import gzip
import hashlib
import json
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.event_abstraction import (DROPPED, MIRROR, RULES, SIMULTANEITY_SECONDS, SIMULTANEOUS, WORK_ITEM,
                                   abstract_labels)

RAW = ROOT / "data/raw/BPI Challenge 2017.xes.gz"
SOURCE = ROOT / "tmp/evaluation/projected_sequences.json"
TARGET = ROOT / "tmp/evaluation/abstracted_sequences.json"
OUT = ROOT / "results/abstraction"
PARTNER = {"O_Created": ("O_Create Offer", "before"), "O_Accepted": ("A_Pending", "after")}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def raw_cases():
    """Yield (case id, [(label, lifecycle, timestamp seconds)]) in XES order."""
    with gzip.open(RAW, "rb") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag.split("}")[-1] != "trace":
                continue
            case_id, events = None, []
            for child in element:
                tag = child.tag.split("}")[-1]
                if tag == "event":
                    raw = {e.attrib.get("key"): e.attrib.get("value") for e in child}
                    events.append((raw["concept:name"], raw["lifecycle:transition"],
                                   datetime.fromisoformat(raw["time:timestamp"]).timestamp()))
                elif child.attrib.get("key") == "concept:name":
                    case_id = child.attrib["value"]
            yield case_id, events
            element.clear()


def log_profile(sequences):
    counts = Counter(map(tuple, sequences))
    ranked = sorted(counts.values(), reverse=True)
    def needed(share):
        total = 0
        for k, n in enumerate(ranked, 1):
            total += n
            if total >= share * len(sequences):
                return k
    return {"cases": len(sequences), "events": sum(map(len, sequences)),
            "labels": len({a for s in sequences for a in s}), "variants": len(counts),
            "cases_in_singleton_variants_pct": 100 * sum(1 for n in ranked if n == 1) / len(sequences),
            "variants_for_60pct_of_cases": needed(0.60), "variants_for_80pct_of_cases": needed(0.80)}


def gap_stats(gaps):
    gaps = sorted(gaps)
    if not gaps:
        return {"n": 0}
    return {"n": len(gaps), "within_1s_pct": 100 * sum(g <= 1 for g in gaps) / len(gaps),
            "within_60s_pct": 100 * sum(g <= 60 for g in gaps) / len(gaps),
            "median_seconds": statistics.median(gaps)}


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    if sha(RAW) != source["raw_sha256"]:
        raise ValueError("Raw log differs from the projection cache")
    lifecycle = defaultdict(Counter)
    label_counts, label_cases = Counter(), Counter()
    mirror = {label: {"events": 0, "adjacent_partner": 0, "gaps": []} for label in MIRROR}
    work = {label: {"completions": 0, "adjacent_a_within_1s": 0, "neighbours": Counter()} for label in WORK_ITEM}
    repeats = {label: {"direct_repetitions": 0, "gaps": []} for label in SIMULTANEOUS}
    applied, traces, before, after = Counter(), [], [], []
    for index, (case_id, events) in enumerate(raw_cases()):
        expected = source["traces"][index]
        completed = [(a, t) for a, l, t in events if l == "complete"]
        labels = [a for a, _ in completed]
        if case_id != expected["case_id"] or labels != expected["activities"]:
            raise ValueError(f"Completion projection differs from cache at case {index} ({case_id})")
        for a, l, _ in events:
            lifecycle[a][l] += 1
        for a in set(labels):
            label_cases[a] += 1
        label_counts.update(labels)
        for i, (a, t) in enumerate(completed):
            if a in mirror:
                partner, side = PARTNER[a]
                j = i - 1 if side == "before" else i + 1
                mirror[a]["events"] += 1
                if 0 <= j < len(completed) and completed[j][0] == partner:
                    mirror[a]["adjacent_partner"] += 1
                    mirror[a]["gaps"].append(abs(t - completed[j][1]))
            if a in work:
                work[a]["completions"] += 1
                neighbours = [completed[j] for j in (i - 1, i + 1) if 0 <= j < len(completed)]
                close = [b for b, u in neighbours if b.startswith("A_") and abs(u - t) <= 1]
                work[a]["adjacent_a_within_1s"] += bool(close)
                for b in close:
                    work[a]["neighbours"][b] += 1
            if a in repeats and i and completed[i - 1][0] == a:
                repeats[a]["direct_repetitions"] += 1
                repeats[a]["gaps"].append(abs(t - completed[i - 1][1]))
        kept, rules = abstract_labels(labels, [t for _, t in completed])
        applied.update(rules)
        before.append(labels)
        after.append(kept)
        traces.append({"case_id": case_id, "activities": kept})
    if len(traces) != len(source["traces"]):
        raise ValueError("Case count differs from the projection cache")
    cases = len(traces)
    evidence = {
        "MIRROR": {a: {"events": v["events"], "partner": PARTNER[a][0],
                       "partner_directly_" + PARTNER[a][1] + "_pct": 100 * v["adjacent_partner"] / v["events"],
                       "gap_to_partner": gap_stats(v["gaps"])} for a, v in mirror.items()},
        "WORK_ITEM": {a: {"raw_events": sum(lifecycle[a].values()), "raw_lifecycle": dict(sorted(lifecycle[a].items())),
                          "complete_share_of_raw_pct": 100 * lifecycle[a]["complete"] / sum(lifecycle[a].values()),
                          "completion_events": v["completions"], "cases_with_completion_pct": 100 * label_cases[a] / cases,
                          "adjacent_A_event_within_1s_pct": 100 * v["adjacent_a_within_1s"] / v["completions"],
                          "adjacent_A_events": dict(v["neighbours"].most_common())} for a, v in work.items()},
        "SIMULTANEOUS": {a: {"direct_repetitions": v["direct_repetitions"], **gap_stats(v["gaps"])}
                         for a, v in repeats.items()},
        "KEPT": {a: {"events": label_counts[a], "cases_pct": 100 * label_cases[a] / cases}
                 for a in RULES["KEPT"]["labels"]},
    }
    for a in ("A_Complete", "A_Incomplete", "A_Validating", "A_Concept"):
        evidence.setdefault("reference_application_states", {})[a] = {
            "events": label_counts[a], "cases_pct": 100 * label_cases[a] / cases}
    removed = {a: label_counts[a] for a in sorted(DROPPED)}
    cache = {"raw_sha256": source["raw_sha256"], "source_cache": SOURCE.relative_to(ROOT).as_posix(),
             "source_cache_sha256": sha(SOURCE), "abstraction": {"rules": RULES, "applied": dict(applied),
             "implementation_sha256": sha(ROOT / "src/event_abstraction.py")},
             "projection": {**log_profile(after), "case_identifiers_and_order_preserved": True},
             "traces": traces}
    TARGET.write_text(json.dumps(cache, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    audit = {"created_utc": datetime.now(timezone.utc).isoformat(), "raw_sha256": source["raw_sha256"],
             "source_cache_sha256": sha(SOURCE), "abstracted_cache": TARGET.relative_to(ROOT).as_posix(),
             "abstracted_cache_sha256": sha(TARGET),
             "implementation_sha256": {p: sha(ROOT / p) for p in ("src/event_abstraction.py", "scripts/abstract_log.py")},
             "rules": RULES, "simultaneity_seconds": SIMULTANEITY_SECONDS, "evidence": evidence,
             "removed_events_per_label": removed, "applied_rule_counts": dict(applied),
             "before": log_profile(before), "after": log_profile(after),
             "cases_preserved": cases, "empty_cases": sum(not s for s in after)}
    write_json(OUT / "abstraction_audit.json", audit)
    write_table(audit)
    print(json.dumps({"applied": audit["applied_rule_counts"], "before": audit["before"], "after": audit["after"]},
                     indent=1), flush=True)


def tex(label):
    return "\\texttt{" + label.replace("_", "\\_") + "}"


def write_table(audit):
    ev = audit["evidence"]
    def pct(x):
        return f"{x:.1f}\\,\\%"
    rows = [r"\begin{tabular}{llrl}", r"\hline", r"Rule & Label & Events & Evidence \\", r"\hline"]
    for a, v in ev["MIRROR"].items():
        side = PARTNER[a][1]
        verb = "preceded by" if side == "before" else "followed by"
        rows.append(f"Mirror (drop) & {tex(a)} & {v['events']:,} & directly {verb} {tex(v['partner'])}: "
                    f"{pct(v['partner_directly_' + side + '_pct'])}; $\\le$60\\,s: "
                    f"{pct(v['gap_to_partner']['within_60s_pct'])} \\\\")
    for a, v in ev["WORK_ITEM"].items():
        rows.append(f"Work item (drop) & {tex(a)} & {v['completion_events']:,} & complete share "
                    f"{pct(v['complete_share_of_raw_pct'])}; A\\_ event $\\le$1\\,s: "
                    f"{pct(v['adjacent_A_event_within_1s_pct'])} \\\\")
    for a, v in ev["SIMULTANEOUS"].items():
        rows.append(f"Simultaneous (collapse) & {tex(a)} & {v['direct_repetitions']:,} & "
                    f"direct repetitions $\\le$1\\,s: {pct(v['within_1s_pct'])} \\\\")
    for a, v in ev["KEPT"].items():
        rows.append(f"Edge case (keep) & {tex(a)} & {v['events']:,} & in {pct(v['cases_pct'])} of cases \\\\")
    b, f = audit["before"], audit["after"]
    rows += [r"\hline",
             f"\\multicolumn{{4}}{{l}}{{Events {b['events']:,} $\\rightarrow$ {f['events']:,}; labels {b['labels']} "
             f"$\\rightarrow$ {f['labels']}; variants {b['variants']:,} $\\rightarrow$ {f['variants']:,}; "
             f"cases {f['cases']:,} (all kept)}} \\\\", r"\hline", r"\end{tabular}"]
    (OUT / "abstraction_rules.tex").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
