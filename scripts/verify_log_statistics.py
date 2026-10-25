"""Independently verify statistics by streaming the original XES XML.

Uses only the standard library, not PM4Py or src.log_statistics. Every raw case
is compared with the case CSV; variant multiplicities, attribute unions,
cardinalities/missingness and population moments are checked independently.
"""

import csv
import gzip
import hashlib
import json
import math
import statistics
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def attributes(element):
    output = {}
    for child in element:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "event":
            continue
        name, value = child.get("key"), child.get("value")
        if name is None:
            continue
        if tag in ("string", "id"):
            kind, value = "string", value
        elif tag == "boolean":
            assert value in ("true", "false")
            kind, value = "boolean", value == "true"
        elif tag in ("int", "float"):
            kind, value = "numeric", int(value) if tag == "int" else float(value)
        elif tag == "date":
            kind, value = "timestamp", datetime.fromisoformat(value).astimezone(timezone.utc)
        else:
            raise ValueError(f"Unhandled raw XES attribute type: {tag}")
        output[name] = (kind, value)
    return output


def main():
    tables = ROOT / "results/tables"
    source = tables / "raw_log_statistics.json"
    summary = json.loads(source.read_text(encoding="utf-8"))
    raw = ROOT / summary["input"]["path"]
    assert sha256(raw) == summary["input"]["sha256"]
    for name, expected in summary["exports"].items():
        assert sha256(tables / name) == expected, name
    with (tables / "raw_case_statistics.csv").open(encoding="utf-8", newline="") as stream:
        cases = list(csv.DictReader(stream))
    with (tables / "raw_variants.csv").open(encoding="utf-8", newline="") as stream:
        variant_export = list(csv.DictReader(stream))
    variants, joint_variants, activity, lifecycle, resource, months = (Counter() for _ in range(6))
    profiles = {scope: {} for scope in ("case", "event")}
    lengths, durations = [], []
    backwards_cases = backwards_pairs = events = 0
    first_event = last_event = None
    print("Independent streaming XML verification of the COMPLETE raw log...", flush=True)
    with gzip.open(raw, "rb") as stream:
        parser = ET.iterparse(stream, events=("start", "end"))
        _, root = next(parser)
        for event_type, element in parser:
            if event_type != "end" or element.tag.rsplit("}", 1)[-1] != "trace":
                continue
            case = attributes(element)
            evs = [attributes(e) for e in element if e.tag.rsplit("}", 1)[-1] == "event"]
            times = [e["time:timestamp"][1] for e in evs]
            sequence = tuple(e["concept:name"][1] for e in evs)
            first, last = min(times), max(times)
            elapsed = (last - first).total_seconds()
            digest = hashlib.sha256(json.dumps(sequence, ensure_ascii=False,
                separators=(",", ":")).encode("utf-8")).hexdigest()
            descending = sum(y < x for x, y in zip(times, times[1:]))
            row = cases[len(lengths)]
            assert row["case_id"] == case["concept:name"][1]
            assert int(row["events"]) == len(evs) and float(row["duration_seconds"]) == elapsed
            assert row["start_utc"] == first.isoformat() and row["end_utc"] == last.isoformat()
            assert row["variant_id"] == digest
            assert int(row["descending_timestamp_pairs"]) == descending
            for scope, items in (("case", [case]), ("event", evs)):
                for item in items:
                    for name, (kind, value) in item.items():
                        profile = profiles[scope].setdefault(name, {"present": 0, "values": set(), "kinds": Counter()})
                        profile["present"] += 1
                        profile["values"].add((kind, value))
                        profile["kinds"][kind] += 1
            variants[digest] += 1
            joint_variants[tuple((e["concept:name"][1], e.get("lifecycle:transition", (None, None))[1]) for e in evs)] += 1
            activity.update(sequence)
            lifecycle.update(e.get("lifecycle:transition", (None, "<missing>"))[1] for e in evs)
            resource.update(str(e["org:resource"][1]) for e in evs if "org:resource" in e)
            months[first.strftime("%Y-%m")] += 1
            lengths.append(len(evs))
            durations.append(elapsed)
            events += len(evs)
            backwards_cases += descending > 0
            backwards_pairs += descending
            first_event = first if first_event is None else min(first_event, first)
            last_event = last if last_event is None else max(last_event, last)
            root.clear()
            if len(lengths) % 5000 == 0:
                print(f"Verified {len(lengths):,} raw cases", flush=True)
    assert len(lengths) == len(cases) == summary["cases"]
    assert len({c["case_id"] for c in cases}) == len(cases)
    assert events == summary["events"] and len(variants) == summary["variants"]
    assert len(joint_variants) == summary["activity_lifecycle_variants"]
    assert dict(variants) == {r["variant_id"]: int(r["cases"]) for r in variant_export}
    assert len(variant_export) == len({r["variant_id"] for r in variant_export})
    assert sum(int(r["cases"]) * int(r["events"]) for r in variant_export) == events
    for key, counts in (("activity_counts", activity), ("lifecycle_counts", lifecycle),
                         ("resource_event_counts", resource), ("case_start_month_counts_utc", months)):
        assert dict(counts) == summary[key], key
    for scope, count in (("case", len(lengths)), ("event", events)):
        assert set(profiles[scope]) == set(summary[f"{scope}_attributes"])
        assert len(profiles[scope]) == summary[f"{scope}_attribute_count"]
        for name, profile in profiles[scope].items():
            reported = summary[f"{scope}_attributes"][name]
            assert reported["present"] == profile["present"] and reported["null"] == 0
            assert reported["missing"] == count - profile["present"]
            assert reported["distinct_non_null"] == len(profile["values"])
            assert reported["value_types"] == dict(profile["kinds"])
            expected_type = ("categorical" if set(profile["kinds"]) <= {"boolean", "string"}
                             else next(iter(profile["kinds"])) if len(profile["kinds"]) == 1 else "mixed_or_empty")
            assert reported["classification"] == expected_type
    cats = [name for name, p in summary["event_attributes"].items() if p["classification"] == "categorical"]
    assert cats == summary["categorical_event_attributes"]
    assert len(cats) == summary["categorical_event_attribute_count"]
    for values, result in ((lengths, summary["case_length"]),
                            (durations, summary["case_duration"]["seconds"])):
        mean = sum(values) / len(values)
        expected = {"n": len(values), "mean": sum(values)/len(values),
            "std_population": math.sqrt(sum((v - mean)**2 for v in values)/len(values)),
            "std_sample": statistics.stdev(values), "min": min(values), "max": max(values),
            "q25": statistics.quantiles(values, n=4, method="inclusive")[0],
            "median": statistics.median(values),
            "q75": statistics.quantiles(values, n=4, method="inclusive")[2],
            "p95": statistics.quantiles(values, n=100, method="inclusive")[94]}
        for key, value in expected.items():
            assert math.isclose(result[key], value, rel_tol=1e-10, abs_tol=1e-8), (key, result[key], value)
    for unit, divisor in (("minutes", 60), ("days", 86400)):
        for key, value in summary["case_duration"]["seconds"].items():
            assert summary["case_duration"][unit][key] == (value if key == "n" or value is None else value/divisor)
    assert summary["quality_checks"]["cases_with_descending_timestamps"] == backwards_cases
    assert summary["quality_checks"]["descending_timestamp_pairs"] == backwards_pairs
    assert summary["first_event_utc"] == first_event.isoformat() and summary["last_event_utc"] == last_event.isoformat()
    assert summary["resource_count"] == len(resource)
    assert summary["events_without_resource"] == events - sum(resource.values())
    result = {"status": "ok", "independent_reader": "stdlib gzip + ElementTree; no PM4Py or src.log_statistics reuse",
        "all_raw_cases_checked": len(lengths), "all_raw_events_checked": events,
        "variants_checked": len(variants), "raw_sha256": summary["input"]["sha256"],
        "summary_sha256": sha256(source), "case_rows_checked": True,
        "variant_weights_checked": True, "attribute_profiles_checked": True,
        "moments_and_units_checked": True,
        "verifier_sha256": sha256(Path(__file__))}
    (tables / "raw_log_statistics_verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
