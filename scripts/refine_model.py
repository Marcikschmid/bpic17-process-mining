"""Trace-weighted refinement of the full common completion projection.

Stage 1: discover IMf candidates, exact coverage/finite-state prefix precision.
Target band 78-82% whole-case replay, defined before looking at candidates.
Selection inside the band: highest prefix precision, then fewer total nodes.
No log cases are removed; no hand-picked fitting-case subset is evaluated.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["PM4PY_DEFAULT_IS_THREADING_MANAGEMENT_ENABLED"] = "False"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
from src.runtime import configure_runtime
configure_runtime()
import pm4py
from pm4py.objects.log.obj import Event, EventLog, Trace
from src.replay_coverage import ExactReplay
from src.simplicity import extended_cardoso, model_size

CACHE = ROOT / "tmp/evaluation/projected_sequences.json"
OUT = ROOT / "results/refinement"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0,.01,.03,.05,.1,.15,.2,.3,.4,.5,.6,.7,.8])
    args = parser.parse_args()
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / "results/tables/quality_metrics.json").read_text(encoding="utf-8"))
    assert sha(CACHE) == baseline["input_cache_sha256"]
    sequences = [t["activities"] for t in data["traces"]]
    log = EventLog([Trace([Event({"concept:name": a}) for a in t["activities"]],
        attributes={"concept:name": t["case_id"]}) for t in data["traces"]])
    manifest_path = OUT / "candidates.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "input_cache_sha256": sha(CACHE), "raw_sha256": data["raw_sha256"],
        "projection": data["projection"], "target_band_percentage": [78,82],
        "selection_rule": "Within target band: maximize exact prefix precision; tie: fewer nodes",
        "candidate_rule": "IMf noise thresholds, full unchanged completion log; no case filtering",
        "candidates": {}}
    assert manifest["input_cache_sha256"] == sha(CACHE)
    for noise in args.thresholds:
        key = f"imf_{noise:.4f}"
        if key in manifest["candidates"]: continue
        started = perf_counter()
        print(f"START {key}", flush=True)
        tree = pm4py.discover_process_tree_inductive(log, noise_threshold=noise, multi_processing=False)
        net, initial, final = pm4py.convert_to_petri_net(tree)
        replay = ExactReplay(net, initial, final)
        coverage, _ = replay.evaluate(sequences)
        precision = replay.prefix_precision(sequences)
        model_dir = OUT / "candidates" / key
        model_dir.mkdir(parents=True, exist_ok=True)
        pm4py.write_pnml(net, initial, final, str(model_dir / "model.pnml"))
        pm4py.write_ptml(tree, str(model_dir / "tree.ptml"))
        record = {"noise_threshold": noise, "algorithm": "IM" if noise == 0 else "IMf",
            "coverage": coverage, "exact_prefix_precision": precision,
            "size": model_size(net), "cardoso": extended_cardoso(net),
            "tree": str(tree), "pnml_sha256": sha(model_dir / "model.pnml"),
            "seconds": round(perf_counter()-started, 3)}
        manifest["candidates"][key] = record
        manifest["updated_utc"] = datetime.now(timezone.utc).isoformat()
        write(manifest_path, manifest)
        print(json.dumps({"candidate": key, **record}), flush=True)
    eligible = [(key, record) for key, record in manifest["candidates"].items()
                if record["coverage"]["sound"] and 78 <= record["coverage"]["fitting_percentage"] <= 82]
    manifest["selected"] = max(eligible, key=lambda x: (x[1]["exact_prefix_precision"]["value"], -x[1]["size"]["nodes"]))[0] if eligible else None
    write(manifest_path, manifest)
    print(f"SELECTED {manifest['selected']}", flush=True)


if __name__ == "__main__": main()
