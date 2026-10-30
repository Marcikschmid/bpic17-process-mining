"""Assess one saved model (PNML or PTML) on the full completion projection.

Writes <out>/<name>.json: soundness (WF-net, classical, easy, relaxed, Woflan),
all four quality dimensions and a flat headline row. With --diagnostics also
writes conformance CSVs (log/model moves per activity, escaping edges, trace
fitness distribution, deviating variants) to <out>/<name>_diagnostics/.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["PM4PY_DEFAULT_IS_THREADING_MANAGEMENT_ENABLED"] = "False"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
from src.runtime import configure_runtime
configure_runtime()
import pm4py
from src.model_assessment import CACHE, assess, headline, load_sequences

IMPLEMENTATION = ("src/model_assessment.py", "src/soundness.py", "src/simplicity.py", "src/replay_coverage.py",
                  "src/finite_alignment.py", "src/finite_precision.py", "scripts/assess_model.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def load_model(path, out, name):
    if path.suffix == ".ptml":
        net, initial, final = pm4py.convert_to_petri_net(pm4py.read_ptml(str(path)))
        pnml = out / f"{name}.pnml"
        pm4py.write_pnml(net, initial, final, str(pnml))
        return net, initial, final, pnml
    net, initial, final = pm4py.read_pnml(str(path))
    return net, initial, final, path


def write_diagnostics(folder, found, sequences):
    counts = Counter(sequences)
    cases = len(sequences)
    write_csv(folder / "moves_per_activity.csv", ["activity", "log_moves_cases", "model_moves_cases"],
              sorted(((a, found["moves"].get(("log", a), 0), found["moves"].get(("model", a), 0))
                      for a in {label for _, label in found["moves"]}), key=lambda r: -(r[1] + r[2])))
    write_csv(folder / "escaping_edges.csv", ["after_activity", "escaping_activity", "weighted_prefixes"],
              sorted(((a, b, n) for (a, b), n in found["escaping"].items()), key=lambda r: -r[2]))
    # Perfectly fitting cases get their own bin 1.0; others use 0.05-wide bins.
    bins = Counter(1.0 if f == 1 else min(int(f * 20), 19) / 20
                   for v, f in found["trace_fitness"].items() for _ in range(counts[v]))
    write_csv(folder / "trace_fitness_histogram.csv", ["fitness_bin_lower", "cases"], sorted(bins.items()))
    deviating = sorted((v for v in counts if found["trace_fitness"][v] < 1), key=lambda v: -counts[v])
    first = Counter()
    for v in deviating:
        first[found["first_deviation"][v]] += counts[v]
    write_csv(folder / "first_deviation_summary.csv", ["kind", "activity", "cases", "share_of_deviating_cases_pct"],
              [(k, a, n, round(100 * n / sum(first.values()), 4)) for (k, a), n in first.most_common()])
    write_csv(folder / "deviating_variants.csv",
              ["cases", "case_share_pct", "trace_fitness", "first_deviation_kind", "first_deviation_activity", "variant"],
              [(counts[v], round(100 * counts[v] / cases, 4), round(found["trace_fitness"][v], 6),
                *found["first_deviation"].get(v, ("", "")), " > ".join(v)) for v in deviating])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path, help="PNML or PTML file (relative to the repository root)")
    parser.add_argument("--name", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results/assessment")
    parser.add_argument("--no-token", action="store_true", help="Skip PM4Py token replay metrics.")
    parser.add_argument("--no-alignments", action="store_true", help="Skip alignment fitness and Align-ET.")
    parser.add_argument("--diagnostics", action="store_true", help="Write conformance diagnostics CSVs.")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    model = args.model if args.model.is_absolute() else ROOT / args.model
    out.mkdir(parents=True, exist_ok=True)
    net, initial, final, pnml = load_model(model, out, args.name)
    data, sequences = load_sequences()
    record, found = assess(net, initial, final, pnml_path=pnml, data=data, sequences=sequences,
                           token=not args.no_token, alignments=not args.no_alignments, diagnostics=args.diagnostics)
    result = {"name": args.name, "model": model.relative_to(ROOT).as_posix(), "model_sha256": sha(model),
              "pnml_sha256": sha(pnml), "input_cache_sha256": sha(CACHE), "raw_sha256": data["raw_sha256"],
              "pm4py": version("pm4py"), "created_utc": datetime.now(timezone.utc).isoformat(),
              "implementation_sha256": {p: sha(ROOT / p) for p in IMPLEMENTATION},
              "headline": headline(record), **record}
    write_json(out / f"{args.name}.json", result)
    if found is not None:
        write_diagnostics(out / f"{args.name}_diagnostics", found, sequences)
    print(json.dumps(result["headline"], indent=2), flush=True)


if __name__ == "__main__":
    main()
