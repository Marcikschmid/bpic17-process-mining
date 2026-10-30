"""Native Heuristics Miner net and a dependency-threshold sweep on the completion projection.

Input: tmp/evaluation/projected_sequences.json (31,509 cases; completed events in
XES order), turned into an EventLog whose events carry only concept:name. HM
CLASSIC reads only activity order (DFG, window-2 DFG, a-b-a triples, start/end
activities), so the default run must be isomorphic to results/models/heuristics_miner.pnml;
the check result is recorded, not assumed.

Writes results/heuristics/:
- native/: pm4py.discover_heuristics_net with the src.discovery defaults, drawn by
  the PM4Py heuristics-net visualizer (heuristics_net_pm4py: unchanged labels =
  frequencies; heuristics_net: edge label = dependency value (frequency)).
- dep_<t>/: dependency_thresh t, all other parameters as src.discovery; converted
  with PM4Py's HN-to-Petri-net converter, i.e. the two calls of heuristics_miner.apply
  CLASSIC (src.discovery.discover_heuristics); model.pnml, edges and figures.
- manifest.json: parameters, HN and Petri-net structure, sha256s, runtimes.

Limits: PM4Py iterates id-hashed sets and writes uuid4 localNodeIDs, so PNML bytes
can differ between runs; compare models by the recorded canonical signature. No
quality metric is computed here (scripts/assess_model.py).
"""
import csv
import hashlib
import itertools
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
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
HASH_SEED = "20261029"
OUT = ROOT / "results/heuristics"
BASELINE = ROOT / "results/models/heuristics_miner.pnml"
THRESHOLDS = (0.5, 0.7, 0.9, 0.99)
EXPECTED = {"places": 49, "transitions": 94, "arcs": 220}
FORMATS = ("svg", "png", "pdf")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def arcs(hn):
    """(source, target, Edge, kind); PM4Py adds L2L arcs with dependency 0 despite the threshold."""
    for a, node in hn.nodes.items():
        for other, found in node.output_connections.items():
            for edge in found:
                b = other.node_name
                yield a, b, edge, "self_loop" if a == b else "length_two_loop" if edge.dependency_value == 0 else "dependency"


def l2l(hn, a, b):
    """Length-two-loop measure (|aba|+|bab|)/(|aba|+|bab|+1) from PM4Py's a-b-a triple counts."""
    v = hn.freq_triples_matrix.get(a, {}).get(b, 0) + hn.freq_triples_matrix.get(b, {}).get(a, 0)
    return v / (v + 1)


def edges(hn):
    rows = [{"source": a, "target": b, "kind": kind, "frequency": edge.dfg_value,
             "dependency": hn.dependency_matrix.get(a, {}).get(b),
             "length_two_loop_measure": l2l(hn, a, b) if kind == "length_two_loop" else None}
            for a, b, edge, kind in arcs(hn)]
    return sorted(rows, key=lambda r: (r["source"], r["target"], r["kind"]))


def hn_signature(hn):
    return {"edges": edges(hn), "start": [dict(sorted(s.items())) for s in hn.start_activities],
            "end": [dict(sorted(e.items())) for e in hn.end_activities],
            "nodes": {n: {"occurrences": v.node_occ, "and_in": v.and_measures_in, "and_out": v.and_measures_out,
                          "loop_length_two": v.loop_length_two} for n, v in sorted(hn.nodes.items())}}


def hn_summary(hn, activities):
    rows = edges(hn)
    kinds = [r["kind"] for r in rows]
    kept = [r["dependency"] for r in rows if r["kind"] == "dependency"]
    pairs = lambda key: sum(len(v) for n in hn.nodes.values() for v in getattr(n, key).values())
    return {"nodes": len(hn.nodes), "arcs": len(kinds), "dependency_arcs": kinds.count("dependency"),
            "self_loops": kinds.count("self_loop"), "length_two_loop_arcs": kinds.count("length_two_loop"),
            "and_split_pairs": pairs("and_measures_out"), "and_join_pairs": pairs("and_measures_in"),
            "start_activities": sorted(hn.start_activities[0]), "end_activities": sorted(hn.end_activities[0]),
            "activities_without_node": sorted(set(activities) - set(hn.nodes)),
            "minimum_kept_dependency": min(kept) if kept else None}


def write_edges(path, hn):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["source", "target", "kind", "frequency", "dependency", "length_two_loop_measure"])
        for r in edges(hn):
            writer.writerow([r["source"], r["target"], r["kind"], r["frequency"],
                             "" if r["dependency"] is None else round(r["dependency"], 6),
                             "" if r["length_two_loop_measure"] is None else round(r["length_two_loop_measure"], 6)])
    return path


def render(hn, folder, stem, annotate):
    """PM4Py visualizer; annotate puts the dependency value into Edge.net_name, shown before the frequency."""
    from pm4py.visualization.heuristics_net import visualizer
    from pm4py.visualization.heuristics_net.variants import pydotplus_vis
    counter = itertools.count()
    pydotplus_vis.uuid4 = lambda: f"n{next(counter)}"  # deterministic DOT node ids instead of uuid4
    for a, b, edge, kind in arcs(hn):
        edge.net_name = (edge.start_node.net_name if not annotate else f"L2L {l2l(hn, a, b):.3f}"
                         if kind == "length_two_loop" else f"{edge.dependency_value:.3f}")
    graph = visualizer.apply(hn, parameters={"format": "svg", "bgcolor": "white"})
    paths = [folder / f"{stem}.gv"]
    paths[0].write_text(graph.source, encoding="utf-8", newline="\n")
    for fmt in FORMATS:
        paths.append(folder / f"{stem}.{fmt}")
        paths[-1].write_bytes(graph.pipe(format=fmt))
    return paths


def signature(net, im, fm):
    return {"places": sorted((p.name, im.get(p, 0), fm.get(p, 0)) for p in net.places),
            "transitions": sorted((t.name, t.label or "") for t in net.transitions),
            "arcs": sorted((a.source.name, a.target.name, a.weight) for a in net.arcs)}


def signature_sha(model):
    return hashlib.sha256(json.dumps(signature(*model), sort_keys=True).encode()).hexdigest()


def isomorphic(first, second):
    """Labelled isomorphism: place markings, transition labels and arc weights must match."""
    import networkx as nx
    def graph(net, im, fm):
        g = nx.DiGraph()
        for p in net.places:
            g.add_node(("p", p.name), key=("p", im.get(p, 0), fm.get(p, 0)))
        for t in net.transitions:
            g.add_node(("t", t.name), key=("t", t.label))
        for a in net.arcs:
            kind = lambda n: "p" if n in net.places else "t"
            g.add_edge((kind(a.source), a.source.name), (kind(a.target), a.target.name), weight=a.weight)
        return g
    return nx.is_isomorphic(graph(*first), graph(*second), node_match=lambda x, y: x["key"] == y["key"],
                            edge_match=lambda x, y: x["weight"] == y["weight"])


def export_pnml(model, path):
    import pm4py
    from src.discovery import structure_summary
    net, im, fm = model
    names = [n.name for n in [*net.places, *net.transitions]]
    if len(set(names)) != len(names) or not all(names):
        raise ValueError(f"Node names are not unique for {path}")
    pm4py.write_pnml(net, im, fm, str(path))
    reloaded = pm4py.read_pnml(str(path))
    if signature(*reloaded) != signature(*model):
        raise ValueError(f"PNML round trip changed {path}")
    return {**structure_summary(*model), "pnml_round_trip_verified": True, "canonical_signature_sha256": signature_sha(model)}


def artifacts(paths):
    return {p.relative_to(ROOT).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in paths}


def main():
    if os.environ.get("PYTHONHASHSEED") != HASH_SEED:
        env = dict(os.environ, PYTHONHASHSEED=HASH_SEED)
        raise SystemExit(subprocess.call([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], env=env, cwd=ROOT))
    from src.runtime import configure_runtime
    dot = configure_runtime()
    if not dot:
        raise RuntimeError("Graphviz not found; run scripts/setup_graphviz.py first.")
    import pm4py
    from pm4py.algo.discovery.dfg import algorithm as dfg_alg
    from pm4py.algo.discovery.heuristics.variants import classic
    from pm4py.objects.conversion.heuristics_net import converter as hn_converter
    from pm4py.objects.heuristics_net import defaults
    from src.discovery import HEURISTICS_PARAMETERS as P, structure_summary
    from src.event_log import DEFAULT_LOG
    from src.model_assessment import CACHE, event_log, load_sequences
    started = perf_counter()
    data, sequences = load_sequences()
    if sha(DEFAULT_LOG) != data["raw_sha256"]:
        raise ValueError("Raw log hash differs from the projection cache.")
    log = event_log(data)
    activities = sorted({a for s in sequences for a in s})
    if P["dfg_pre_cleaning_noise_thresh"] != defaults.DEFAULT_DFG_PRE_CLEANING_NOISE_THRESH:
        raise ValueError("pm4py.discover_heuristics_net cannot set dfg_pre_cleaning_noise_thresh.")
    api = {"dependency_threshold": P["dependency_thresh"], "and_threshold": P["and_measure_thresh"],
           "loop_two_threshold": P["loop_length_two_thresh"], "min_act_count": P["min_act_count"],
           "min_dfg_occurrences": P["min_dfg_occurrences"], "activity_key": P["pm4py:param:activity_key"],
           "timestamp_key": P["pm4py:param:timestamp_key"], "case_id_key": P["pm4py:param:case_id_key"],
           "decoration": "frequency"}
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "PM4Py Heuristics Miner CLASSIC; dependency_thresh sweep, all other parameters as src.discovery",
        "input": {"cache": CACHE.relative_to(ROOT).as_posix(), "cache_sha256": sha(CACHE), "raw_sha256": data["raw_sha256"],
                  "cases": len(sequences), "events": sum(map(len, sequences)), "variants": len(set(sequences)),
                  "activities": len(activities),
                  "event_log": "src.model_assessment.event_log: concept:name per event, case id as trace attribute; no timestamps",
                  "projection": data["projection"]["filter"], "event_order": data["projection"]["event_order"]},
        "versions": {"python": platform.python_version(), "pm4py": version("pm4py"), "networkx": version("networkx"),
                     "graphviz_python": version("graphviz"),
                     "graphviz_executable": subprocess.run([dot, "-V"], capture_output=True, text=True, check=True).stderr.strip()},
        "randomness": {"random_seed": None, "python_hash_seed": HASH_SEED,
                       "note": "HM has no stochastic step; the hash seed fixes string-set order (clique order, silent-transition names)."},
        "base_parameters": P, "thresholds": list(THRESHOLDS),
        "visualization": {"tool": "pm4py.visualization.heuristics_net (pydotplus variant), frequency decoration",
                          "node_label": "activity (occurrences)", "heuristics_net_pm4py": "unchanged PM4Py edge label: frequency",
                          "heuristics_net": "edge label: dependency value (frequency); L2L arcs: 'L2L' measure (frequency)",
                          "dot_node_ids": "uuid4 replaced by a counter for reproducible DOT"},
        "implementation_sha256": {p: sha(ROOT / p) for p in ("scripts/discover_heuristics_variants.py", "src/discovery.py",
                                                             "src/model_assessment.py")}}
    print("NATIVE pm4py.discover_heuristics_net " + json.dumps(api), flush=True)
    before = perf_counter()
    native = pm4py.discover_heuristics_net(log, **api)
    native_seconds = round(perf_counter() - before, 3)
    folder = OUT / "native"
    folder.mkdir(parents=True, exist_ok=True)
    paths = [write_edges(folder / "dependency_edges.csv", native), *render(native, folder, "heuristics_net_pm4py", False),
             *render(native, folder, "heuristics_net", True)]
    dependencies = [d for row in native.dependency_matrix.values() for d in row.values()]
    manifest["native"] = {"call": "pm4py.discover_heuristics_net", "arguments": api,
                          "dfg_pre_cleaning_noise_thresh": "PM4Py default " + str(defaults.DEFAULT_DFG_PRE_CLEANING_NOISE_THRESH),
                          "seconds": native_seconds, "heuristics_net": hn_summary(native, activities),
                          "dfg": {"arcs_before_pre_cleaning": len(dfg_alg.apply(log, parameters=P)),
                                  "arcs_after_pre_cleaning": len(native.dfg),
                                  "cleaned_arcs_with_dependency_at_least": {str(t): sum(d >= t for d in dependencies)
                                                                            for t in (0.0, *THRESHOLDS)}},
                          "artifacts": artifacts(paths)}
    baseline = pm4py.read_pnml(str(BASELINE))
    manifest["sweep"] = {}
    for threshold in THRESHOLDS:
        parameters = {**P, "dependency_thresh": threshold}
        before = perf_counter()
        hn = classic.apply_heu(log, parameters=parameters)
        middle = perf_counter()
        model = hn_converter.apply(hn, parameters=parameters)
        after = perf_counter()
        folder = OUT / f"dep_{threshold}"
        folder.mkdir(parents=True, exist_ok=True)
        labels = {t.label for t in model[0].transitions if t.label is not None}
        if labels != set(hn.nodes):
            raise ValueError("Petri-net labels differ from heuristics-net nodes.")
        record = {"parameters": parameters, "heuristics_net_seconds": round(middle - before, 3),
                  "conversion_seconds": round(after - middle, 3), "heuristics_net": hn_summary(hn, activities),
                  "petri_net": export_pnml(model, folder / "model.pnml")}
        if threshold == P["dependency_thresh"]:
            counts = structure_summary(*baseline)
            record["reproduces_baseline"] = {
                "baseline": BASELINE.relative_to(ROOT).as_posix(), "baseline_sha256": sha(BASELINE),
                "expected_counts": EXPECTED, "baseline_counts": {k: counts[k] for k in EXPECTED},
                "counts_match": all(record["petri_net"][k] == v == counts[k] for k, v in EXPECTED.items()),
                "labelled_isomorphic": isomorphic(model, baseline),
                "same_heuristics_net_as_native_api": hn_signature(hn) == hn_signature(native)}
            print("BASELINE CHECK " + json.dumps(record["reproduces_baseline"]), flush=True)
        paths = [folder / "model.pnml", write_edges(folder / "dependency_edges.csv", hn), *render(hn, folder, "heuristics_net", True)]
        record["artifacts"] = artifacts(paths)
        manifest["sweep"][f"dep_{threshold}"] = record
        print(f"dep_{threshold}: HN {record['heuristics_net']['nodes']} nodes / {record['heuristics_net']['arcs']} arcs; "
              f"PN {record['petri_net']['places']} places, {record['petri_net']['transitions']} transitions, "
              f"{record['petri_net']['arcs']} arcs", flush=True)
    manifest["total_seconds"] = round(perf_counter() - started, 3)
    write_json(OUT / "manifest.json", manifest)
    print(f"Complete. See {(OUT / 'manifest.json').relative_to(ROOT).as_posix()}", flush=True)


if __name__ == "__main__":
    main()
