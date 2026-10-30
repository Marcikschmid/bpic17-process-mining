"""Measured Genetic Miner cost per fitness evaluation and the native early-stop rule; no rerun.

Inputs: results/genetic/seed_20261025/{manifest.json, evolution.csv},
tmp/genetic_seed_20261025.log and the installed PM4Py source. evolution.csv
holds naive local datetime.now() stamps written after each tournament; the UTC
offset follows from manifest started_utc + discovery_seconds versus the last
row. Cost per evaluation = generation-1 interval / population size: one interval
only (no variance), including selection, crossover, mutation and net conversion.
Extrapolations assume the same mean cost on the same full log and machine; they
are estimates, not a measured default run.
"""
import csv
import hashlib
import json
from datetime import datetime, timedelta
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/genetic/seed_20261025"
LOG = ROOT / "tmp/genetic_seed_20261025.log"
PM4PY = ROOT / ".venv/Lib/site-packages/pm4py"
CLASSIC = PM4PY / "algo/discovery/genetic/variants/classic.py"
WRAPPER = PM4PY / "discovery.py"
OUT = ROOT / "results/genetic/budget_notes.json"
DEFAULTS = {"population_size": 500, "generations": 100}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def source_line(path, snippet):
    """1-based line number and stripped text of the unique line containing snippet."""
    hits = [(n, line.strip()) for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if snippet in line]
    if len(hits) != 1:
        raise ValueError(f"{snippet!r} found {len(hits)} times in {rel(path)}")
    return {"file": rel(path), "line": hits[0][0], "code": hits[0][1]}


def native_stop(bests, generations):
    """Replay classic.py lines 155-179 on given per-tournament best values; return tournaments run."""
    history, tournaments = [], 1
    for _ in range(generations - 1):
        current = bests[tournaments - 1]
        if current == 1 or (history and all(f == current for f in history[-int(generations / 2):])):
            break
        history.append(current)
        tournaments += 1
    return tournaments


def main():
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    with (RUN / "evolution.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    population, generations = manifest["parameters"]["population_size"], manifest["parameters"]["generations"]
    stamps = [datetime.fromisoformat(r["timestamp"]) for r in rows]
    bests = [float(r["fitness0"]) for r in rows]
    started = datetime.fromisoformat(manifest["started_utc"]).replace(tzinfo=None)
    finished = started + timedelta(seconds=manifest["discovery_seconds"])
    raw_offset = (stamps[-1] - finished).total_seconds()
    offset = round(raw_offset / 900) * 900
    local_start = started + timedelta(seconds=offset)
    intervals = [(b - a).total_seconds() for a, b in zip([local_start, *stamps], stamps)]
    per_evaluation = intervals[1] / population
    evaluations = population * len(rows)
    overhead = intervals[0] - population * per_evaluation
    log = LOG.read_bytes().decode("utf-8", errors="replace").splitlines()
    start_line = next(l for l in log if l.startswith("START native Genetic Miner "))
    done_line = next(l for l in log if l.startswith("DONE "))
    logged_parameters = json.loads(start_line.removeprefix("START native Genetic Miner "))
    done = json.loads(done_line.removeprefix("DONE "))
    if logged_parameters != manifest["parameters"] or not done["generations"] == len(rows) == manifest["evaluated_generations"]:
        raise ValueError("Log, manifest and evolution.csv disagree")
    if done["native_objective"] != manifest["native_best_objective"] or bests[-1] != manifest["native_best_objective"]:
        raise ValueError("Native objective differs between log, manifest and evolution.csv")
    k = int(generations / 2)
    default_k = int(DEFAULTS["generations"] / 2)
    scenarios = {"best_unchanged_after_generation_1": [0.3, 0.3] + [0.3] * 98,
                 "improves_in_generation_1_then_stagnates": [0.3, 0.31] + [0.31] * 98,
                 "improves_every_generation": [0.3 + i / 1000 for i in range(100)]}
    stop_runs = {name: native_stop(values, DEFAULTS["generations"]) for name, values in scenarios.items()}
    if native_stop(bests + [bests[-1]] * generations, generations) != len(rows):
        raise ValueError("Stop-rule replay does not reproduce the recorded run")
    # Every improve/stagnate pattern of this budget; defaults: last improvement after generation g.
    possible = sorted({native_stop([0.3 + sum(p[:i]) / 100 for i in range(generations)], generations)
                       for p in product((0, 1), repeat=generations - 1)})
    default_counts = sorted({native_stop([0.3 + min(i, g) / 1000 for i in range(DEFAULTS["generations"])],
                                         DEFAULTS["generations"]) for g in range(DEFAULTS["generations"])})
    stop_line = source_line(CLASSIC, "if fitness[0] == 1 or (history and all(f == fitness[0]")
    if CLASSIC.read_text(encoding="utf-8").splitlines()[stop_line["line"]].strip() != "break":
        raise ValueError("Stop condition is not followed by break")

    def cost(n):
        return {"evaluations": n, "seconds": round(n * per_evaluation, 1), "hours": round(n * per_evaluation / 3600, 2),
                "days": round(n * per_evaluation / 86400, 2)}
    record = {
        "method": "Wall-clock derived from recorded artifacts of seed 20261025; no rerun. Per evaluation = "
                  "generation-1 interval / population size. Extrapolation assumes the same mean cost per evaluation.",
        "inputs": {rel(p): sha(p) for p in (RUN / "manifest.json", RUN / "evolution.csv", LOG, CLASSIC, WRAPPER)},
        "pm4py": manifest["pm4py"],
        "run": {"parameters": manifest["parameters"], "cases": manifest["input"]["cases"],
                "events": manifest["input"]["events"], "started_utc": manifest["started_utc"],
                "discovery_seconds": manifest["discovery_seconds"], "total_seconds": manifest["total_seconds"],
                "tournaments_run": len(rows), "maximum_tournaments": generations,
                "fitness_evaluations": evaluations, "maximum_fitness_evaluations": population * generations,
                "elite_reevaluations": (len(rows) - 1) * round(manifest["parameters"]["elitism_rate"] * population),
                "best_objective_per_tournament": bests,
                "stop_reason": "best objective of tournament 1 equals tournament 0; window history[-%d:] then holds "
                               "only one value, so one stagnant generation suffices" % k},
        "timing": {"evolution_csv_clock": "naive local time (datetime.now in classic.py)",
                   "derived_utc_offset_seconds": offset, "offset_residual_seconds": round(raw_offset - offset, 3),
                   "tournament_end_local": [s.isoformat() for s in stamps],
                   "start_to_tournament_0_seconds": round(intervals[0], 3),
                   "tournament_0_to_1_seconds": round(intervals[1], 3),
                   "seconds_per_fitness_evaluation": round(per_evaluation, 3),
                   "milliseconds_per_case": round(1000 * per_evaluation / manifest["input"]["cases"], 3),
                   "microseconds_per_event": round(1e6 * per_evaluation / manifest["input"]["events"], 1),
                   "fixed_overhead_seconds_estimate": round(overhead, 1),
                   "fixed_overhead_contents": "input preparation, DataFrame handling, causal-matrix counting, "
                                              "initial population; assumes tournament 0 costs as much as tournament 1",
                   "log_has_timestamps": False},
        "log_check": {"start_parameters_match_manifest": True, "done_generations": done["generations"],
                      "done_native_objective_matches": True,
                      "done_quality_metrics_used": False,
                      "reason": "DONE quality line scores the invalid duplicate-ID export (manifest export_correction)"},
        "extrapolation_pm4py_defaults": {
            "parameters": {**DEFAULTS, "elitism_rate": 0.01, "elitism_min_sample": 5},
            "per_tournament": cost(DEFAULTS["population_size"]),
            "maximum": cost(DEFAULTS["population_size"] * DEFAULTS["generations"]),
            "earliest_native_stop": cost(DEFAULTS["population_size"] * stop_runs["best_unchanged_after_generation_1"]),
            "earliest_stop_if_generation_1_improves": cost(
                DEFAULTS["population_size"] * stop_runs["improves_in_generation_1_then_stagnates"]),
            "ratio_maximum_to_this_budget": DEFAULTS["population_size"] * DEFAULTS["generations"] / (population * generations),
            "excludes": "fixed overhead; extra cost of building 500 initial individuals; token-replay cost variation"},
        "early_stop_rule": {
            "condition": stop_line,
            "action": {"file": rel(CLASSIC), "line": stop_line["line"] + 1, "code": "break"},
            "history_append": source_line(CLASSIC, "history.append(fitness[0])"),
            "generation_loop": source_line(CLASSIC, "for _ in tqdm(range(generations-1)"),
            "initial_tournament": source_line(CLASSIC, "population, fitness = tournament(tqdm(population,"),
            "next_tournament": source_line(CLASSIC, "population, fitness = tournament(tqdm(next_population,"),
            "elitism": source_line(CLASSIC, "next_population = population[:round(elitism_rate * population_size)]"),
            "evaluation_loop": source_line(CLASSIC, "for i,(I,O) in enumerate(population):"),
            "evaluation_call": source_line(CLASSIC, "metrics = pm4py.fitness_token_based_replay("),
            "objective": [source_line(CLASSIC, "0.4 * metrics['average_trace_fitness']"),
                          source_line(CLASSIC, "0.6 * metrics['percentage_of_fitting_traces']/100")],
            "window_this_run": k, "window_defaults": default_k,
            "possible_tournament_counts_this_run": possible,
            "possible_tournament_counts_defaults": {"stagnant_generation_1": default_counts[0],
                                                    "otherwise_from": default_counts[1], "to": default_counts[-1]},
            "default_scenarios_tournaments": stop_runs,
            "note": "Elite kept and re-evaluated deterministically, so the best never decreases. Before the history "
                    "reaches the window length the slice is shorter: at the first check one equal value stops. "
                    "fitness[0] == 1 stops at any check."},
        "defaults_in_source": {
            "classic_apply": [source_line(CLASSIC, f"Parameters.{key}, parameters,") for key in
                              ("POPULATION_SIZE", "ELITISM_RATE", "CROSSOVER_RATE", "MUTATION_RATE", "GENERATIONS",
                               "ELITISM_MIN_SAMPLE")],
            "discover_petri_net_genetic": [source_line(WRAPPER, snippet) for snippet in
                                           ("population_size: int = 500", "elitism_rate: float = 0.01",
                                            "generations: int = 100", "elitism_min_sample: int = 5")]},
        "implementation_sha256": {"scripts/genetic_budget.py": sha(ROOT / "scripts/genetic_budget.py")}}
    if record["extrapolation_pm4py_defaults"]["earliest_native_stop"]["evaluations"] != 1000:
        raise ValueError("Unexpected default stop replay")
    OUT.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"timing": record["timing"], "extrapolation": record["extrapolation_pm4py_defaults"],
                      "stop": record["early_stop_rule"]["condition"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
