"""Evaluate every combination of the named manual tree edits (src/tree_edits.py).

Base: the refined model frequent_0.60_imf_0.03 (results/refinement/final_model.*),
reconstructed exactly and checked for complete language equivalence first.

Selection rule, fixed before any combination was evaluated:
1. sound and 78% <= exact whole-case replay <= 82% (same band as refinement);
2. maximize Align-ET precision (exact finite-state solver);
3. guard rails on the full assessment of the best candidates: generalization drop
   <= 0.01, arc-degree simplicity drop <= 0.05, node increase <= 25% (vs base);
4. tie: fewer nodes.
Screening uses all 31,509 cases; no case is removed.

Generalization is measured alignment-based (PM4Py formula, transition counts
from exact optimal alignments). Correction after the first run: PM4Py token
replay maps each label to ONE transition, so token generalization is invalid
for edits that duplicate labels (R1); token values are kept for information.

Correction after the second run: step 3 first checked only the ten best
candidates; all ten contain R1 and fail the generalization guard. The guard
stage now walks down the same ranking until the first candidate passes (rule
unchanged, --top only as an optional cap). Full assessments are cached per
candidate name, keyed by the hashes of src/tree_edits.py and src/model_assessment.py.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
import pm4py
from pm4py.algo.evaluation.simplicity.variants import arc_degree
from src.finite_precision import finite_alignment_precision
from src.model_assessment import CACHE, alignment_fitness, duplicate_labels, event_log, load_sequences, token_metrics
from src.replay_coverage import ExactReplay
from src.simplicity import extended_cardoso, model_size, reachability_complexity
from src.tree_edits import EDITS, all_combinations, build_tree, parse

OUT = ROOT / "results/manual_edits"
BASE = ROOT / "results/refinement"
BAND = (78.0, 82.0)
GUARDS = {"generalization": 0.01, "arc_degree": 0.05, "node_increase": 0.25}


def key(combination):
    return "+".join(combination) or "base"


def net_profile(net):
    return {"places": len(net.places), "transitions": len(net.transitions),
            "silent": sum(t.label is None for t in net.transitions), "arcs": len(net.arcs),
            "labels": Counter(t.label for t in net.transitions if t.label is not None)}


def delta(profile, base):
    labels = profile["labels"] - base["labels"], base["labels"] - profile["labels"]
    return {**{k: profile[k] - base[k] for k in ("places", "transitions", "silent", "arcs")},
            "visible_added": sorted(labels[0].elements()), "visible_removed": sorted(labels[1].elements())}


def screen(tree_string, sequences, log, base_profile):
    started = perf_counter()
    net, initial, final = pm4py.convert_to_petri_net(parse(tree_string))
    machine = ExactReplay(net, initial, final)
    coverage, _ = machine.evaluate(sequences)
    precision, _ = finite_alignment_precision(log, net, initial, final)
    reachability = reachability_complexity(net, initial, final)
    profile = net_profile(net)
    return {"tree": tree_string, "coverage": coverage, "align_et_precision": precision["precision"],
            "weighted_unfit_prefixes": precision["weighted_unfit_prefixes"], "size": model_size(net),
            "extended_cardoso": extended_cardoso(net), "extended_cyclomatic": reachability.get("value"),
            "arc_degree": arc_degree.apply(net, {"k": 2}), "sound": coverage["sound"] and reachability.get("sound"),
            "petri_net_delta": delta(profile, base_profile), "seconds": round(perf_counter() - started, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=None, help="optional cap on guard checks (default: until first pass)")
    args = parser.parse_args()
    data, sequences = load_sequences()
    log = event_log(data)
    final_metrics = json.loads((BASE / "final_metrics.json").read_text(encoding="utf-8"))
    base_tree = build_tree(())
    if base_tree != final_metrics["selected_candidate"]["tree"]:
        raise ValueError("Edit template does not reproduce the refined tree string")
    base_net = pm4py.read_pnml(str(BASE / "final_model.pnml"))
    rebuilt = pm4py.convert_to_petri_net(parse(base_tree))
    equivalence = ExactReplay(*base_net).language_equivalent(ExactReplay(*rebuilt))
    if not equivalence["equivalent"]:
        raise ValueError(f"Rebuilt base differs in language: {equivalence}")
    base_profile = net_profile(rebuilt[0])
    path = OUT / "screen.json"
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if result.get("input_cache_sha256") != sha(CACHE) or result.get("tree_edits_sha256") != sha(ROOT / "src/tree_edits.py"):
        result = {"input_cache_sha256": sha(CACHE), "tree_edits_sha256": sha(ROOT / "src/tree_edits.py"),
                  "base": "frequent_0.60_imf_0.03", "base_language_equivalence": equivalence,
                  "band_pct": BAND, "guards": GUARDS, "edits": EDITS, "candidates": {}}
    for combination in all_combinations():
        name = key(combination)
        if name in result["candidates"]:
            continue
        result["candidates"][name] = {"edits": list(combination), **screen(build_tree(combination), sequences, log, base_profile)}
        record = result["candidates"][name]
        print(f"{name:28s} {record['coverage']['fitting_percentage']:8.4f} {record['align_et_precision']:.4f} "
              f"{record['size']['nodes']:4d} {record['seconds']:.1f}s", flush=True)
        write_json(path, result)
    base = result["candidates"]["base"]
    eligible = sorted((r for r in result["candidates"].values()
                       if r["sound"] and BAND[0] <= r["coverage"]["fitting_percentage"] <= BAND[1]),
                      key=lambda r: (-r["align_et_precision"], r["size"]["nodes"]))
    def full(record):
        net, initial, final = pm4py.convert_to_petri_net(parse(record["tree"]))
        aligned = alignment_fitness(net, initial, final, sequences)
        token = token_metrics(log, net, initial, final)
        return {"alignment_generalization": aligned["alignment_generalization"],
                "alignment_fitness": aligned["log_fitness"], "duplicate_visible_labels": duplicate_labels(net),
                "token_generalization": token["generalization"], "token_fitness": token["fitness"]["log_fitness"],
                "token_precision": token["precision"]}
    identity = {"tree_edits_sha256": sha(ROOT / "src/tree_edits.py"),
                "model_assessment_sha256": sha(ROOT / "src/model_assessment.py")}
    cache = result.get("full_assessment", {})
    if cache.get("identity") != identity:
        # Seed once from the earlier guard run of this screen (same edit and assessment code).
        previous = result.get("selection", {})
        seeded = {c["candidate"]: {k: c[k] for k in ("alignment_generalization", "alignment_fitness",
                                                     "duplicate_visible_labels", "token_generalization",
                                                     "token_fitness", "token_precision")}
                  for c in previous.get("checked", [])}
        if "base" in previous:
            seeded["base"] = previous["base"]
        cache = {"identity": identity, "values": seeded if cache.get("identity") is None else {}}
    result["full_assessment"] = cache

    def cached_full(name, record):
        if name not in cache["values"]:
            cache["values"][name] = full(record)
            write_json(path, result)
        return cache["values"][name]

    base_full = cached_full("base", base)
    checked, selected = [], None
    for record in eligible[:args.top]:
        name = key(record["edits"])
        values = cached_full(name, record)
        guard = {"generalization": base_full["alignment_generalization"] - values["alignment_generalization"]
                                   <= GUARDS["generalization"],
                 "arc_degree": base["arc_degree"] - record["arc_degree"] <= GUARDS["arc_degree"],
                 "node_increase": record["size"]["nodes"] <= (1 + GUARDS["node_increase"]) * base["size"]["nodes"]}
        checked.append({"candidate": name, **values, "guards": guard, "passes": all(guard.values())})
        print("GUARD", checked[-1], flush=True)
        if all(guard.values()):
            selected = name
            break
    result["selection"] = {"rule": __doc__.split("Selection rule, fixed before any combination was evaluated:")[1].strip(),
                           "eligible": len(eligible), "base": base_full, "checked": checked, "selected": selected}
    write_json(path, result)
    rows = [(key(r["edits"]), r["coverage"]["fitting_cases"], round(r["coverage"]["fitting_percentage"], 4),
             round(r["align_et_precision"], 6), r["size"]["nodes"], r["size"]["arcs"], r["extended_cardoso"],
             r["extended_cyclomatic"], round(r["arc_degree"], 6), r["sound"]) for r in result["candidates"].values()]
    with (OUT / "screen.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["candidate", "fitting_cases", "exact_replay_pct", "align_et_precision", "nodes", "arcs",
                         "extended_cardoso", "extended_cyclomatic", "arc_degree", "sound"])
        writer.writerows(sorted(rows, key=lambda r: (len(r[0]), r[0])))
    if selected:
        folder = OUT / "selected"
        folder.mkdir(parents=True, exist_ok=True)
        tree = parse(result["candidates"][selected]["tree"])
        pm4py.write_ptml(tree, str(folder / "model.ptml"))
        pm4py.write_pnml(*pm4py.convert_to_petri_net(tree), str(folder / "model.pnml"))
    print("SELECTED", selected, flush=True)


if __name__ == "__main__":
    main()
