"""Run selected discovery baselines and export auditable PNML and vector figures.

This command only writes results/. Selected report assets are copied separately.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.event_log import DEFAULT_LOG, load_event_log
from src.discovery import (
    HEURISTICS_PARAMETERS,
    INDUCTIVE_PARAMETERS,
    completion_projection,
    discover_heuristics,
    discover_inductive,
    structure_summary,
)
from src.runtime import configure_runtime
import pm4py
from pm4py.visualization.petri_net import visualizer


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export_model(name, model, output_dir=None):
    net, initial, final = model
    output_dir = Path(output_dir) if output_dir is not None else ROOT / "results"
    models = output_dir / "models"
    figures = output_dir / "figures"
    models.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    pnml = models / f"{name}.pnml"
    pm4py.write_pnml(net, initial, final, str(pnml))
    reloaded = pm4py.read_pnml(str(pnml))
    summary = structure_summary(*model)
    if structure_summary(*reloaded) != summary:
        raise ValueError(f"PNML round-trip changed the structure of {name}.")
    # Check topology and markings, not just element counts.
    def signature(model):
        n, im, fm = model
        return (
            sorted((p.name, im.get(p, 0), fm.get(p, 0)) for p in n.places),
            sorted((t.name, t.label) for t in n.transitions),
            sorted((a.source.name, a.target.name, a.weight) for a in n.arcs),
        )
    if signature(model) != signature(reloaded):
        raise ValueError(f"PNML round-trip changed the topology/markings of {name}.")
    graph = visualizer.apply(net, initial, final, parameters={
        "set_rankdir": "TB", "font_size": "14", "bgcolor": "white"
    })
    # Compact places and tau nodes, while keeping every node, arc and label.
    # PM4Py defaults to very large circles and black boxes; those would force
    # illegibly small activity text when fitting the full model into a page.
    graph.attr("graph", nodesep="0.10", ranksep="0.10", pad="0.08")
    graph.attr("edge", arrowsize="0.55")
    for place in net.places:
        graph.node(str(id(place)), width="0.20", height="0.20", fontsize="10", fixedsize="true")
    for transition in net.transitions:
        if transition.label is None:
            graph.node(str(id(transition)), width="0.08", height="0.08", fixedsize="true")
        else:
            graph.node(str(id(transition)), height="0.25", width="0.4", margin="0.04,0.02")
    artifacts = [pnml]
    dot_path = figures / f"{name}.gv"
    dot_path.write_text(graph.source, encoding="utf-8")
    artifacts.append(dot_path)
    for fmt in ("pdf", "svg", "png"):
        path = figures / f"{name}.{fmt}"
        path.write_bytes(graph.pipe(format=fmt))
        artifacts.append(path)
    return {
        **summary,
        "pnml_round_trip_verified": True,
        "artifacts": {
            path.relative_to(ROOT).as_posix(): {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in artifacts
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", choices=("both", "inductive", "heuristics"), default="both")
    parser.add_argument("--output-dir", type=Path, help="Output directory within results/.")
    args = parser.parse_args()
    output = args.output_dir or (
        ROOT / "results" if args.algorithm == "both" else ROOT / "results" / "runs" / args.algorithm
    )
    if not output.is_absolute():
        output = ROOT / output
    output = output.resolve()
    if not output.is_relative_to((ROOT / "results").resolve()):
        parser.error("--output-dir must be within the project's results/ directory.")
    dot = configure_runtime()
    if not dot:
        raise RuntimeError("Graphviz not found; run scripts/setup_graphviz.py first.")
    input_hash = sha256(DEFAULT_LOG)
    source_manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    expected_hash = next(item["sha256"] for item in source_manifest["files"]
                         if item["path"] == DEFAULT_LOG.relative_to(ROOT).as_posix())
    if input_hash != expected_hash:
        raise ValueError("Input checksum differs from the verified data manifest.")
    start = perf_counter()
    print("Loading the unchanged full BPIC-17 log...", flush=True)
    raw = load_event_log()
    log, preprocessing = completion_projection(raw)
    del raw
    print(f"Discovery input: {len(log):,} cases, {preprocessing['discovery_events']:,} completed events.", flush=True)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_algorithm": args.algorithm,
        "input": {"path": DEFAULT_LOG.relative_to(ROOT).as_posix(), "sha256": input_hash},
        "versions": {"python": platform.python_version(), "pm4py": version("pm4py"),
                     "graphviz_python": version("graphviz"),
                     "graphviz_executable": subprocess.run([dot, "-V"], capture_output=True, text=True, check=True).stderr.strip()},
        "preprocessing": preprocessing,
        "randomness": {"random_seed": None, "reason": "No stochastic discovery step or sampling; algorithms do not expose a random seed.",
                       "python_hash_seed": os.environ.get("PYTHONHASHSEED", "unset"),
                       "byte_reproducibility": "UUID node identifiers, timestamps and Graphviz layout may vary between runs; models represent the discovered behaviour."},
        "visualization": {"rankdir": "TB", "font_size": 14, "nodesep": 0.10, "ranksep": 0.10,
                          "place_diameter_inches": 0.20, "silent_transition_size_inches": 0.08,
                          "note": "Layout changes only; all model nodes, arcs and original activity labels retained."},
        "models": {},
        "quality_evaluation": "Not performed in task 1; fitness, precision, generalization, simplicity and replayable-case coverage remain to be evaluated.",
    }
    for name, algorithm, parameters, discover in (
        ("inductive_miner", "Inductive Miner (IM)", INDUCTIVE_PARAMETERS, discover_inductive),
        ("heuristics_miner", "Heuristics Miner (CLASSIC)", HEURISTICS_PARAMETERS, discover_heuristics),
    ):
        if args.algorithm != "both" and not name.startswith(args.algorithm):
            continue
        print(f"Running {algorithm}...", flush=True)
        before = perf_counter()
        model = discover(log)
        seconds = perf_counter() - before
        result = export_model(name, model, output_dir=output)
        result.update({"algorithm": algorithm, "parameters": parameters, "discovery_seconds": round(seconds, 3)})
        manifest["models"][name] = result
        print(f"Exported {name}: {result['places']} places, {result['transitions']} transitions, {result['arcs']} arcs ({seconds:.2f}s discovery).", flush=True)
    manifest["total_seconds"] = round(perf_counter() - start, 3)
    tables = output / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    (tables / "discovery_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Complete. See {tables / 'discovery_manifest.json'}. Report assets were not changed.", flush=True)


if __name__ == "__main__":
    main()
