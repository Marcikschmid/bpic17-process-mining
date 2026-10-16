"""Check the complete import and export a small first-case preview."""

import json
import sys
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.event_log import DEFAULT_LOG, load_event_log


def main():
    print("Loading the unchanged BPIC-17 log with PM4Py...", flush=True)
    log = load_event_log()
    if not log or not any(len(trace) for trace in log):
        raise ValueError("The imported log is empty.")

    activities = Counter()
    lifecycle = Counter()
    missing = Counter()
    case_attributes = set()
    event_attributes = set()
    events = 0
    for trace in log:
        case_attributes.update(trace.attributes)
        missing["case_id"] += trace.attributes.get("concept:name") is None
        for event in trace:
            events += 1
            event_attributes.update(event)
            activities[str(event.get("concept:name", "<missing>"))] += 1
            lifecycle[str(event.get("lifecycle:transition", "<missing>"))] += 1
            for key in ("concept:name", "time:timestamp"):
                missing[key] += event.get(key) is None

    summary = {
        "input": DEFAULT_LOG.relative_to(ROOT).as_posix(),
        "python": sys.version.split()[0],
        "pm4py": version("pm4py"),
        "preprocessing": "None; all original events and lifecycle states retained.",
        "cases": len(log),
        "events": events,
        "distinct_activities": len(activities),
        "case_attribute_names": sorted(case_attributes),
        "event_attribute_names": sorted(event_attributes),
        "activity_counts": dict(sorted(activities.items())),
        "lifecycle_counts": dict(sorted(lifecycle.items())),
        "missing_required_values": dict(missing),
        "preview_case_id": log[0].attributes.get("concept:name"),
        "preview_case_attributes": dict(log[0].attributes),
        "preview_order": "Original event order in the XES trace.",
    }
    if any(missing.values()):
        raise ValueError(f"Required identifiers or timestamps are missing: {missing}")

    output = ROOT / "results" / "tables"
    output.mkdir(parents=True, exist_ok=True)
    (output / "import_summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8"
    )
    preview = pd.DataFrame([dict(event) for event in log[0]])
    preview.insert(0, "case:concept:name", summary["preview_case_id"])
    preview.to_csv(output / "first_case.csv", index=False)
    print(
        f"Import successful: {len(log):,} cases, {events:,} events, "
        f"{len(activities)} activity labels.", flush=True
    )
    print(f"Import summary and first-case CSV saved in {output}", flush=True)


if __name__ == "__main__":
    main()
