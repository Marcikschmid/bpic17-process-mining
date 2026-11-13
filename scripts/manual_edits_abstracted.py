"""Screen every combination of the manual edits of the abstracted base (src/tree_edits_abstracted.py).

Base: results/abstraction/base/ (scripts/refine_abstracted.py), reconstructed
exactly and checked for complete language equivalence first. All metrics on
the abstracted log, all 31,509 cases.

Selection rule, fixed before any combination was evaluated:
1. sound and exact whole-case replay >= 80 % (lecture of 2026-10-29, slide 36);
2. maximize Align-ET precision (exact finite-state solver);
3. guard rails on the full assessment, walking down the ranking until the first
   candidate passes: alignment-generalization drop <= 0.01, arc-degree drop <= 0.05,
   node increase <= 25 % (all vs. base) - unchanged from scripts/manual_edits.py;
4. tie: fewer nodes.

Writes results/abstraction/manual_edits/{screen.json,screen.csv,evidence.json,selected/}.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
from scripts.manual_edits import GUARDS, delta, key, net_profile, screen
import pm4py
from src.model_assessment import ABSTRACTED_CACHE, alignment_fitness, duplicate_labels, event_log, load_sequences, token_metrics
from src.replay_coverage import ExactReplay
from src.tree_edits_abstracted import BASE, EDITS, all_combinations, build_tree, parse

OUT = ROOT / "results/abstraction/manual_edits"
BASE_DIR = ROOT / "results/abstraction/base"
FLOOR = 80.0
SENT = ("O_Sent (mail and online)", "O_Sent (online only)")


def evidence(sequences):
    """Log evidence for each edit (cases, all 31,509 abstracted cases)."""
    def first(s, a):
        return s.index(a) if a in s else None
    def before_first_validation(s, label):
        v = first(s, "A_Validating")
        return label in s and (v is None or s.index(label) < v)
    cases = len(sequences)
    return {
        "R1": {"cases_with_A_Complete": sum("A_Complete" in s for s in sequences),
               "A_Complete_before_first_sent_offer": sum(
                   "A_Complete" in s and not any(a in SENT for a in s[:s.index("A_Complete")]) for s in sequences)},
        "R2": {"O_Returned_before_first_A_Validating": sum(before_first_validation(s, "O_Returned") for s in sequences),
               "A_Incomplete_before_first_A_Validating": sum(before_first_validation(s, "A_Incomplete") for s in sequences),
               "direct_A_Validating_repetition_cases": sum(any(a == b == "A_Validating" for a, b in zip(s, s[1:]))
                                                           for s in sequences),
               "A_Incomplete_directly_followed_by_O_Returned_cases": sum(
                   any(a == "A_Incomplete" and b == "O_Returned" for a, b in zip(s, s[1:])) for s in sequences)},
        "R3": {label: {"cases": sum(label in s for s in sequences),
                       "without_prior_A_Validating": sum(before_first_validation(s, label) for s in sequences)}
               for label in ("A_Pending", "A_Denied", "A_Cancelled")},
        "G1": {"cases_with_O_Sent_online_only": sum("O_Sent (online only)" in s for s in sequences)},
        "G2": {"cases_with_O_Create_Offer_after_first_A_Validating": sum(
            "A_Validating" in s and "O_Create Offer" in s[s.index("A_Validating"):] for s in sequences)},
        "cases": cases}


def main():
    data, sequences = load_sequences(ABSTRACTED_CACHE)
    log = event_log(data)
    selection = json.loads((BASE_DIR / "selection.json").read_text(encoding="utf-8"))
    if build_tree(()) != BASE or BASE != selection["tree"]:
        raise ValueError("Edit template does not reproduce the abstracted base tree string")
    base_net = pm4py.read_pnml(str(BASE_DIR / "model.pnml"))
    rebuilt = pm4py.convert_to_petri_net(parse(BASE))
    equivalence = ExactReplay(*base_net).language_equivalent(ExactReplay(*rebuilt))
    if not equivalence["equivalent"]:
        raise ValueError(f"Rebuilt base differs in language: {equivalence}")
    base_profile = net_profile(rebuilt[0])
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "evidence.json", evidence(sequences))
    path = OUT / "screen.json"
    identity = {"input_cache_sha256": sha(ABSTRACTED_CACHE), "tree_edits_sha256": sha(ROOT / "src/tree_edits_abstracted.py"),
                "model_assessment_sha256": sha(ROOT / "src/model_assessment.py")}
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if result.get("identity") != identity:
        result = {"identity": identity, "base": selection["candidate"], "base_language_equivalence": equivalence,
                  "floor_pct": FLOOR, "guards": GUARDS, "edits": EDITS, "candidates": {}, "full_assessment": {}}
    for combination in all_combinations():
        name = key(combination)
        if name in result["candidates"]:
            continue
        result["candidates"][name] = {"edits": list(combination),
                                      **screen(build_tree(combination), sequences, log, base_profile)}
        record = result["candidates"][name]
        print(f"{name:20s} {record['coverage']['fitting_percentage']:8.4f} {record['align_et_precision']:.4f} "
              f"{record['size']['nodes']:4d} {record['seconds']:.1f}s", flush=True)
        write_json(path, result)
    base = result["candidates"]["base"]
    eligible = sorted((r for r in result["candidates"].values()
                       if r["sound"] and r["coverage"]["fitting_percentage"] >= FLOOR),
                      key=lambda r: (-r["align_et_precision"], r["size"]["nodes"]))

    def full(name, record):
        if name not in result["full_assessment"]:
            net, initial, final = pm4py.convert_to_petri_net(parse(record["tree"]))
            aligned = alignment_fitness(net, initial, final, sequences)
            token = token_metrics(log, net, initial, final)
            result["full_assessment"][name] = {
                "alignment_generalization": aligned["alignment_generalization"],
                "alignment_fitness": aligned["log_fitness"], "duplicate_visible_labels": duplicate_labels(net),
                "token_generalization": token["generalization"], "token_fitness": token["fitness"]["log_fitness"],
                "token_precision": token["precision"]}
            write_json(path, result)
        return result["full_assessment"][name]

    base_full = full("base", base)
    checked, selected = [], None
    for record in eligible:
        name = key(record["edits"])
        values = full(name, record)
        guard = {"generalization": base_full["alignment_generalization"] - values["alignment_generalization"]
                                   <= GUARDS["generalization"],
                 "arc_degree": base["arc_degree"] - record["arc_degree"] <= GUARDS["arc_degree"],
                 "node_increase": record["size"]["nodes"] <= (1 + GUARDS["node_increase"]) * base["size"]["nodes"]}
        checked.append({"candidate": name, **values, "guards": guard, "passes": all(guard.values())})
        print("GUARD", checked[-1], flush=True)
        if all(guard.values()):
            selected = name
            break
    result["selection"] = {"rule": __doc__.split("Selection rule, fixed before any combination was evaluated:")[1]
                           .split("Writes")[0].strip(), "eligible": len(eligible), "base": base_full,
                           "checked": checked, "selected": selected}
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
