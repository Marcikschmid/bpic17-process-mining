"""Compute Assignment 3.2 statistics from the complete, unchanged PM4Py log."""

import csv
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["PM4PY_DEFAULT_IS_THREADING_MANAGEMENT_ENABLED"] = "False"
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "2"
from src.event_log import DEFAULT_LOG, load_event_log
from src.log_statistics import compute_statistics


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    started = perf_counter()
    publisher = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    expected = next(f["sha256"] for f in publisher["files"] if f["path"] == DEFAULT_LOG.relative_to(ROOT).as_posix())
    if sha256(DEFAULT_LOG) != expected:
        raise ValueError("Raw data SHA256 differs from the download manifest")
    print("Loading ALL raw cases and lifecycle states with PM4Py...", flush=True)
    log = load_event_log()
    print(f"Loaded {len(log):,} cases; calculating raw-log statistics...", flush=True)
    summary, cases, variants = compute_statistics(log)
    summary.update(input={"path": DEFAULT_LOG.relative_to(ROOT).as_posix(), "sha256": expected,
                          "doi": publisher["doi"]},
        python=platform.python_version(), pm4py=version("pm4py"),
        created_utc=datetime.now(timezone.utc).isoformat(),
        implementation_sha256={p: sha256(ROOT / p) for p in
            ("src/event_log.py", "src/log_statistics.py", "scripts/analyze_log.py")},
        seconds=round(perf_counter() - started, 3))
    output = ROOT / "results/tables"
    output.mkdir(parents=True, exist_ok=True)
    attributes = [{"scope": scope, "attribute": name,
                   **{k: v for k, v in item.items() if k != "value_types"},
                   "value_types": json.dumps(item["value_types"], sort_keys=True)}
        for scope in ("case", "event") for name, item in summary[f"{scope}_attributes"].items()]
    write_csv(output / "raw_case_statistics.csv", cases)
    write_csv(output / "raw_variants.csv", variants)
    write_csv(output / "raw_attribute_profile.csv", attributes)
    for key, filename, label in (("activity_counts", "raw_activity_counts.csv", "activity"),
                                 ("lifecycle_counts", "raw_lifecycle_counts.csv", "lifecycle"),
                                 ("case_start_month_counts_utc", "raw_monthly_cases.csv", "month_utc")):
        write_csv(output / filename, [{label: key_value, "count": count} for key_value, count in summary[key].items()])
    summary["exports"] = {p.name: sha256(p) for p in [output / name for name in (
        "raw_case_statistics.csv", "raw_variants.csv", "raw_attribute_profile.csv",
        "raw_activity_counts.csv", "raw_lifecycle_counts.csv", "raw_monthly_cases.csv")]}
    (output / "raw_log_statistics.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8", newline="\n")
    print(json.dumps({key: summary[key] for key in ("cases", "events", "variants", "categorical_event_attribute_count", "seconds")}), flush=True)


if __name__ == "__main__":
    main()
