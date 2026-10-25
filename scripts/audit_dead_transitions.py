"""Find and export exact unreachable-transition certificates; models stay unchanged."""

import json
import sys
from pathlib import Path
from importlib.metadata import version

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate_models import MODELS, CACHE, sha256, write_json
from src.validation import dead_transition_certificates
import pm4py


def main():
    records = {}
    cached = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else None
    for model in MODELS:
        path = ROOT / f"results/models/{model}.pnml"
        net, initial, _ = pm4py.read_pnml(str(path))
        proofs = dead_transition_certificates(net, initial)
        records[model] = {"model_sha256": sha256(path),
                          "certified_dead_count_lower_bound": len(proofs),
                          "complete_dead_transition_enumeration": False,
                          "activity_labels": sorted(t.label for t in net.transitions if t.name in proofs and t.label is not None),
                          "certificates": proofs}
        # A label is unreachable only if EVERY transition carrying it is dead.
        labels = {t.label for t in net.transitions if t.label is not None}
        unreachable = sorted(label for label in labels if all(
            t.name in proofs for t in net.transitions if t.label == label))
        records[model]["unreachable_activity_labels"] = unreachable
        if cached is not None:
            traces = cached["traces"]
            affected = sum(any(a in unreachable for a in t["activities"]) for t in traces)
            records[model]["case_replay_upper_bound"] = {
                "cases": len(traces), "provably_unfit_cases": affected,
                "maximum_fitting_cases": len(traces) - affected,
                "maximum_fitting_percentage": 100 * (len(traces) - affected) / len(traces),
                "input_cache_sha256": sha256(CACHE)}
        print(model, "certified unreachable:", len(proofs), flush=True)
    write_json(ROOT / "results/tables/dead_transition_audit.json", {
        "method": "Nonnegative place subinvariants; exact rational verification of all inequalities",
        "scipy": version("scipy"), "models": records,
        "implementation_sha256": {p: sha256(ROOT / p) for p in
                                  ("src/validation.py", "scripts/audit_dead_transitions.py")}})


if __name__ == "__main__":
    main()
