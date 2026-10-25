"""Independently check evaluation coverage, provenance, exports and HM witness."""

import hashlib
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.runtime import configure_runtime
configure_runtime()
import pm4py
from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking
from src.validation import verify_dead_transition_certificate


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_unboundedness(net, initial, witness):
    """Replay the reported prefix and pump twice with PM4Py firing semantics."""
    by_name = {t.name: t for t in net.transitions}
    places = {p.name: p for p in net.places}
    def fire(marking, names):
        marking = Marking(marking)
        for name in names:
            transition = by_name[name]
            assert semantics.is_enabled(transition, net, marking), name
            marking = semantics.execute(transition, net, marking)
        return marking
    def vector(marking):
        return [marking.get(places[p], 0) for p in witness["place_order"]]
    ancestor = fire(initial, witness["prefix"])
    first = fire(ancestor, witness["pump_sequence"])
    second = fire(first, witness["pump_sequence"])
    a, b, c = vector(ancestor), vector(first), vector(second)
    assert a == witness["ancestor_marking"] and b == witness["covering_marking"]
    assert all(x <= y for x, y in zip(a, b)) and a != b
    assert [y - x for x, y in zip(a, b)] == [z - y for y, z in zip(b, c)]
    return {"unboundedness_witness_verified_with_pm4py": True, "pump_repetitions_checked": 2}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-incomplete-alignment", action="store_true",
                        help="Verify reported scores while explicitly recording incomplete alignment fitness.")
    args = parser.parse_args()
    source = ROOT / "results/tables/quality_metrics.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    discovery = json.loads((ROOT / "results/tables/discovery_manifest.json").read_text(encoding="utf-8"))
    assert data["raw_sha256"] == discovery["input"]["sha256"]
    assert data["projection"] == discovery["preprocessing"]
    checks = {}
    incomplete_metrics = []
    for model, jobs in data["models"].items():
        model_path = ROOT / f"results/models/{model}.pnml"
        expected = discovery["models"][model]["artifacts"][model_path.relative_to(ROOT).as_posix()]["sha256"]
        assert sha256(model_path) == expected
        for job, record in jobs.items():
            if record["status"] != "ok":
                assert args.allow_incomplete_alignment and job == "alignment" and record["status"] == "incomplete", (
                    model, job, record["status"], record.get("reason"))
                assert record.get("fitness") is None and record.get("fitting_cases") is None
                assert 0 <= record["evaluated_cases"] < data["projection"]["discovery_cases"]
                incomplete_metrics.append({"model": model, "metric": "alignment_fitness",
                                           "evaluated_cases": record["evaluated_cases"],
                                           "total_cases": data["projection"]["discovery_cases"]})
            if "model_sha256" in record:
                assert record["model_sha256"] == expected
            if "input_cache_sha256" in record:
                assert record["input_cache_sha256"] == data["input_cache_sha256"]
                assert record["cases"] == data["projection"]["discovery_cases"]
                assert record["events"] == data["projection"]["discovery_events"]
            if job in ("token", "alignment") and record["status"] == "ok":
                assert record["evaluated_cases"] == data["projection"]["discovery_cases"]
                fitting = record["fitting_cases"] / record["evaluated_cases"] * 100
                key = "perc_fit_traces" if job == "token" else "percFitTraces"
                assert abs(fitting - record["fitness"][key]) < 1e-8
        structure = jobs["structure"]
        assert structure["cardoso_own"] == structure["cardoso_pm4py"]
        reach = structure["reachability"]
        if reach["status"] == "unbounded":
            net, initial, _ = pm4py.read_pnml(str(model_path))
            checks[model] = verify_unboundedness(net, initial, reach["witness"])
        else:
            assert reach["status"] == "ok" and structure["reachability_crosscheck_pm4py"]
            checks[model] = {"complete_state_space_crosschecked": True,
                             "states": reach["states_seen"], "sound": reach["sound"]}
    artifacts = json.loads((ROOT / "results/tables/quality_artifacts.json").read_text(encoding="utf-8"))
    assert artifacts["source_sha256"] == sha256(source)
    for path, expected in artifacts["artifacts"].items():
        assert sha256(ROOT / path) == expected, path
    for path, expected in artifacts.get("additional_sources", {}).items():
        assert sha256(ROOT / path) == expected, path
    audit_path = ROOT / "results/tables/dead_transition_audit.json"
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        for model, record in audit["models"].items():
            path = ROOT / f"results/models/{model}.pnml"
            assert record["model_sha256"] == sha256(path)
            net, initial, _ = pm4py.read_pnml(str(path))
            assert record["certified_dead_count_lower_bound"] == len(record["certificates"])
            assert record["activity_labels"] == sorted(t.label for t in net.transitions
                if t.name in record["certificates"] and t.label is not None)
            for transition, certificate in record["certificates"].items():
                assert verify_dead_transition_certificate(net, initial, transition, certificate)
            labels = {t.label for t in net.transitions if t.label is not None}
            unreachable = sorted(label for label in labels if all(
                t.name in record["certificates"] for t in net.transitions if t.label == label))
            assert record["unreachable_activity_labels"] == unreachable
            if "case_replay_upper_bound" in record:
                bound = record["case_replay_upper_bound"]
                assert bound["input_cache_sha256"] == data["input_cache_sha256"]
                cache = ROOT / "tmp/evaluation/projected_sequences.json"
                if cache.exists():
                    assert sha256(cache) == bound["input_cache_sha256"]
                    traces = json.loads(cache.read_text(encoding="utf-8"))["traces"]
                    affected = sum(any(a in unreachable for a in t["activities"]) for t in traces)
                    assert bound["cases"] == len(traces) and bound["provably_unfit_cases"] == affected
                    assert bound["maximum_fitting_cases"] == len(traces) - affected
                    assert abs(bound["maximum_fitting_percentage"] - 100 * (len(traces) - affected) / len(traces)) < 1e-10
            checks[model]["dead_transition_certificates_verified"] = len(record["certificates"])
    checks["reported_numeric_scores_and_artifact_hashes_verified"] = True
    checks["all_alignment_fitness_values_available"] = not incomplete_metrics
    checks["incomplete_metrics"] = incomplete_metrics
    checks["quality_metrics_sha256"] = sha256(source)
    output = ROOT / "results/tables/quality_verification.json"
    output.write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
