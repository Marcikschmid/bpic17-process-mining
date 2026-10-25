"""Evaluate the two saved discovery baselines on the COMPLETE common projection.

Run from the project root. Outputs stay in results/; report assets are selected
separately. Alignment variants are checkpointed immediately, with no default time limit.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Enforce sequential PM4Py scheduling before importing the package.
os.environ["PM4PY_DEFAULT_IS_THREADING_MANAGEMENT_ENABLED"] = "False"
# Small LP matrices perform poorly with dozens of BLAS threads per worker.
# Restrict only these evaluation processes, never the user's system settings.
for numeric_thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[numeric_thread_variable] = "2"
from src.runtime import configure_runtime
configure_runtime()

import pm4py
from pm4py.util import constants
constants.DEFAULT_IS_THREADING_MANAGEMENT_ENABLED = False
from src.simplicity import extended_cardoso, model_size, reachability_complexity

MODELS = ("inductive_miner", "heuristics_miner")
JOBS = ("structure", "token", "token_precision", "alignment", "alignment_precision")
TABLES = ROOT / "results/tables/evaluation"
CACHE = ROOT / "tmp/evaluation/projected_sequences.json"
PARAMETERS = {"pm4py:param:activity_key": "concept:name", "show_progress_bar": False,
              "multiprocessing": False, "cleaning_token_flood": False}


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                         encoding="utf-8", newline="\n")
    temporary.replace(path)


def prepare():
    from src.event_log import DEFAULT_LOG, load_event_log
    from src.discovery import completion_projection
    source_hash = sha256(DEFAULT_LOG)
    manifest = json.loads((ROOT / "results/tables/discovery_manifest.json").read_text(encoding="utf-8"))
    # Check against the discovery input, not against a hard-coded expected count.
    if source_hash != manifest["input"]["sha256"]:
        raise ValueError("Raw log SHA256 does not match the discovery manifest.")
    log, summary = completion_projection(load_event_log())
    traces = [{"case_id": t.attributes["concept:name"],
               "activities": [e["concept:name"] for e in t]} for t in log]
    write_json(CACHE, {"raw_sha256": source_hash, "projection": summary, "traces": traces})
    print(f"Prepared {len(traces)} cases / {summary['discovery_events']} events", flush=True)


def read_log():
    from pm4py.objects.log.obj import Event, EventLog, Trace
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    log = EventLog([Trace([Event({"concept:name": a}) for a in t["activities"]],
                         attributes={"concept:name": t["case_id"]}) for t in data["traces"]])
    assert len(log) == data["projection"]["discovery_cases"]
    assert sum(map(len, log)) == data["projection"]["discovery_events"]
    return log, data


def worker(model, job, force=False, alignment_workers=None, alignment_trace_timeout=None):
    started = perf_counter()
    path = ROOT / f"results/models/{model}.pnml"
    discovery = json.loads((ROOT / "results/tables/discovery_manifest.json").read_text(encoding="utf-8"))
    expected = discovery["models"][model]["artifacts"][path.relative_to(ROOT).as_posix()]["sha256"]
    if sha256(path) != expected:
        raise ValueError("Saved PNML no longer matches the discovery manifest.")
    net, initial, final = pm4py.read_pnml(str(path))
    result = {"model": model, "job": job, "model_sha256": sha256(path),
              "pm4py_version": version("pm4py"), "parameters": PARAMETERS,
              "numeric_threads": {key: os.environ[key] for key in
                                  ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "implementation_sha256": {p: sha256(ROOT / p) for p in
                  ("scripts/evaluate_models.py", "src/simplicity.py", "src/discovery.py", "src/quality.py", "src/alignment.py")}}
    output = TABLES / f"{model}_{job}.json"
    if output.exists() and not force:
        previous = json.loads(output.read_text(encoding="utf-8"))
        same_code = previous.get("implementation_sha256") == result["implementation_sha256"]
        same_model = previous.get("model_sha256") == result["model_sha256"]
        same_input = job == "structure" or previous.get("input_cache_sha256") == sha256(CACHE)
        same_version = previous.get("pm4py_version") == result["pm4py_version"]
        if previous.get("status") == "ok" and same_code and same_model and same_input and same_version:
            print(f"REUSE verified result: {model} / {job}", flush=True)
            return
    try:
        if job == "structure":
            from pm4py.algo.evaluation.simplicity.variants import arc_degree, extended_cardoso as reference
            from pm4py.objects.petri_net.utils.check_soundness import check_wfnet
            own = extended_cardoso(net)
            builtin = reference.apply(net)
            if own != builtin:
                raise ValueError("Independent Cardoso implementation disagrees with PM4Py.")
            reachability = reachability_complexity(net, initial, final)
            result.update(status="ok", size_own=model_size(net), cardoso_own=own,
                          cardoso_pm4py=builtin, simplicity_arc_degree=arc_degree.apply(net, {"k": 2}),
                          workflow_net=check_wfnet(net), reachability=reachability)
            if reachability["status"] == "ok":
                from pm4py.algo.evaluation.simplicity.variants import extended_cyclomatic
                from pm4py.objects.petri_net.utils import reachability_graph
                import networkx as nx
                rg = reachability_graph.construct_reachability_graph(net, initial)
                graph = nx.DiGraph()
                graph.add_nodes_from(rg.states)
                graph.add_edges_from((s, edge.to_state) for s in rg.states for edge in s.outgoing)
                correct = graph.number_of_edges() - len(graph) + nx.number_strongly_connected_components(graph)
                if correct != reachability["value"] or len(graph) != reachability["states_seen"]:
                    raise ValueError("State-space computation disagrees with PM4Py's actual marking graph.")
                result["reachability_crosscheck_pm4py"] = True
                value = extended_cyclomatic.apply(net, initial)
                result["cyclomatic_pm4py"] = value
                result["cyclomatic_matches_pm4py"] = value == reachability["value"]
        else:
            log, data = read_log()
            variants = Counter(tuple(e["concept:name"] for e in t) for t in log)
            result.update(cases=len(log), events=sum(map(len, log)), variants=len(variants),
                          input_cache_sha256=sha256(CACHE), raw_sha256=data["raw_sha256"])
            if job == "token":
                from pm4py.algo.conformance.tokenreplay import algorithm as tbr
                from pm4py.algo.evaluation.replay_fitness.variants import token_replay as fitness
                from pm4py.algo.evaluation.generalization.variants.token_based import get_generalization
                replay = tbr.apply(log, net, initial, final, parameters={
                    **PARAMETERS, "consider_remaining_in_fitness": True})
                if len(replay) != len(log) or any(r is None for r in replay):
                    raise ValueError("Token replay did not cover every case.")
                result.update(status="ok", fitness=fitness.evaluate(replay),
                              generalization=get_generalization(net, replay),
                              evaluated_cases=len(replay),
                              fitting_cases=sum(r["trace_is_fit"] for r in replay))
            elif job == "token_precision":
                from pm4py.algo.evaluation.precision.variants import etconformance_token
                result.update(status="ok", precision=etconformance_token.apply(
                    log, net, initial, final, parameters=dict(PARAMETERS)))
            elif job == "alignment":
                from src.alignment import align_variants
                from pm4py.algo.evaluation.replay_fitness.variants import alignment_based as fitness
                cores = alignment_workers if alignment_workers is not None else (
                    min(8, max(1, (os.cpu_count() or 2) // 2)) if model == "heuristics_miner" else 1)
                params = {**PARAMETERS, "multiprocessing": cores > 1, "cores": cores,
                          "show_progress_bar": False}
                if alignment_trace_timeout is not None:
                    if alignment_trace_timeout <= 0:
                        raise ValueError("Explicit trace timeout must be positive")
                    params["max_align_time_trace"] = alignment_trace_timeout
                result["parameters"] = params
                result["variant"] = "VERSION_STATE_EQUATION_A_STAR"
                result["time_limit_seconds"] = alignment_trace_timeout
                identity = {"model_sha256": result["model_sha256"],
                            "input_cache_sha256": result["input_cache_sha256"],
                            "pm4py_version": result["pm4py_version"],
                            "cvxopt_version": version("cvxopt"),
                            "variant": result["variant"], "cost_profile": "PM4Py standard: visible=10000, tau=1, sync=0"}
                result["checkpoint_identity"] = identity
                replay, reused = align_variants(log, path,
                    ROOT / f"tmp/evaluation/{model}_variants", identity,
                    params, workers=cores, force=force)
                result["reused_case_alignments"] = reused
                complete = sum(r is not None for r in replay)
                result["evaluated_cases"] = complete
                if len(replay) != len(log) or complete != len(log):
                    # PM4Py's evaluator otherwise silently omits None entries.
                    result.update(status="incomplete", fitness=None,
                                  reason="Missing alignments; no subset average reported.")
                else:
                    result.update(status="ok", fitness=fitness.evaluate(replay),
                                  fitting_cases=sum(r["fitness"] == 1 for r in replay))
            else:
                from src.quality import alignment_precision_batched
                result.update(status="ok", **alignment_precision_batched(
                    log, net, initial, final, parameters=PARAMETERS, progress=True))
    except Exception as error:
        result.update(status="error", error_type=type(error).__name__, reason=str(error))
    result["seconds"] = round(perf_counter() - started, 3)
    write_json(TABLES / f"{model}_{job}.json", result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def run_jobs(force=False):
    from src.event_log import DEFAULT_LOG
    cached = json.loads(CACHE.read_text(encoding="utf-8"))
    if cached["raw_sha256"] != sha256(DEFAULT_LOG):
        raise ValueError("Stale evaluation cache; use --prepare.")
    for model in MODELS:
        for job in JOBS:
            path = TABLES / f"{model}_{job}.json"
            print(f"START {model}: {job}", flush=True)
            logfile = ROOT / f"tmp/evaluation/{model}_{job}.log"
            timeout = 180 if job == "structure" else (None if job == "alignment" else 1500)
            with logfile.open("w", encoding="utf-8") as stream:
                try:
                    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                        "--model", model, "--job", job] + (["--force"] if force else []), cwd=ROOT, stdout=stream,
                        stderr=subprocess.STDOUT, timeout=timeout)
                    if proc.returncode:
                        write_json(path, {"model": model, "job": job, "status": "error",
                            "reason": f"Worker exit code {proc.returncode}; see {logfile.relative_to(ROOT)}"})
                except subprocess.TimeoutExpired:
                    write_json(path, {"model": model, "job": job, "status": "timeout",
                                      "timeout_seconds": timeout,
                                      "reason": "Worker time limit; no partial score reported."})
            value = json.loads(path.read_text(encoding="utf-8"))
            print(f"DONE {model}: {job}: {value['status']}", flush=True)
    summarize()


def summarize():
    results = {m: {j: json.loads((TABLES / f"{m}_{j}.json").read_text(encoding="utf-8"))
                   for j in JOBS} for m in MODELS}
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    output = {"created_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "pm4py": version("pm4py"), "raw_sha256": data["raw_sha256"],
              "input_cache_sha256": sha256(CACHE), "projection": data["projection"],
              "all_cases_retained": True, "threading": False,
              "multiprocessing": any(
                  results[m]["alignment"].get("parameters", {}).get("multiprocessing", False)
                  or any(a.get("alignment_workers", 1) > 1 for a in results[m]["alignment"].get("additional_attempts", []))
                  for m in MODELS),
              "token_based_quality_dimensions_complete": all(
                  results[m][j]["status"] == "ok" for m in MODELS for j in ("structure", "token", "token_precision")),
              "alignment_fitness_complete": all(results[m]["alignment"]["status"] == "ok" for m in MODELS),
              "random_seed": None, "models": results}
    write_json(ROOT / "results/tables/quality_metrics.json", output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Rebuild the local full-log sequence cache.")
    parser.add_argument("--job", choices=JOBS)
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument("--summarize", action="store_true")
    parser.add_argument("--run", action="store_true", help="Run all jobs using the prepared local cache.")
    parser.add_argument("--force", action="store_true", help="Recompute even if code, model and input hashes match a successful result.")
    parser.add_argument("--alignment-workers", type=int, choices=(1, 2, 4, 8), help="Default: IM=1; HM up to half the logical CPUs, capped at 8.")
    parser.add_argument("--alignment-trace-timeout", type=float, default=None, help="Optional seconds per variant; default: no time limit.")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.job:
        if not args.model:
            parser.error("--job requires --model")
        worker(args.model, args.job, force=args.force, alignment_workers=args.alignment_workers,
               alignment_trace_timeout=args.alignment_trace_timeout)
    elif args.summarize:
        summarize()
    elif args.run:
        run_jobs(force=args.force)
    else:
        prepare()
        run_jobs(force=args.force)


if __name__ == "__main__":
    main()
