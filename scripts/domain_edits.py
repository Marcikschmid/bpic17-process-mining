"""Domain-knowledge revision of the abstracted base (src/tree_edits_domain.py).

Stage 1 (domain): the domain edits R1, D1, G1, D2, D4 and D5 are applied as a group.
Every subset is also evaluated, only to report what each rule costs or gains.
Stage 2 (screened): all subsets of R2, G2 and D3 on top of the domain model,
selected with the rule of scripts/manual_edits_abstracted.py:
0. the model keeps every business rule of src/domain_rules.py (checked on the full
   state space; added 2026-11-19 after R2 was found to allow approval without a
   returned offer);
1. sound and exact whole-case replay >= 80 %;
2. maximize Align-ET precision;
3. guard rails, walking down the ranking until the first candidate passes:
   alignment-generalization drop <= 0.01, arc-degree drop <= 0.05,
   node increase <= 25 %, all measured against the domain model;
4. tie (precision equal to 4 decimals): fewer nodes.
The same guards measured against the abstracted IMf base are reported, not used.

All metrics on the abstracted log, all 31,509 cases.
Writes results/domain/{evidence.json,screen.json,screen.csv,selected/}.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_model import sha, write_json
from scripts.manual_edits import GUARDS, key, net_profile, screen
import pm4py
from src.domain_rules import log_counterexamples, model_violations
from src.model_assessment import ABSTRACTED_CACHE, alignment_fitness, duplicate_labels, event_log, load_sequences, token_metrics
from src.tree_edits_domain import BASE, DOMAIN, EDITS, SCREENED, build_tree, combinations, parse

OUT = ROOT / "results/domain"
FLOOR = 80.0
FRAUD = "W_Assess potential fraud"
SHORTENED = "W_Shortened completion "
COLLECTION = "W_Personal Loan collection"
BASE_SELECTION = ROOT / "results/abstraction/base/selection.json"
SENT = ("O_Sent (mail and online)", "O_Sent (online only)")
OUTCOMES = ("A_Pending", "A_Denied", "A_Cancelled")


def evidence(sequences):
    """Log evidence for the domain rules (cases, all 31,509 abstracted cases)."""
    def first(s, a):
        return s.index(a) if a in s else None

    def before_first(s, label, anchor):
        i, j = first(s, label), first(s, anchor)
        return i is not None and (j is None or i < j)

    def outcome(s):
        return next((o for o in OUTCOMES if o in s), "open")

    fraud = [s for s in sequences if FRAUD in s]
    phase = Counter()
    for s in fraud:
        validation = first(s, "A_Validating")
        end = next((k for k, a in enumerate(s) if a in OUTCOMES), None)
        for i, a in enumerate(s):
            if a != FRAUD:
                continue
            if not any(x in SENT for x in s[:i]):
                phase["before_first_sent_offer"] += 1
            elif validation is None or i < validation:
                phase["before_validation"] += 1
            elif end is not None and i > end:
                phase["after_outcome"] += 1
            else:
                phase["during_validation"] += 1
    all_outcomes = Counter(map(outcome, sequences))
    return {
        "cases": len(sequences),
        "business_rule_counterexamples": log_counterexamples(sequences),
        "R1": {"cases_with_A_Complete": sum("A_Complete" in s for s in sequences),
               "A_Complete_before_first_sent_offer": sum(
                   "A_Complete" in s and not any(a in SENT for a in s[:s.index("A_Complete")]) for s in sequences)},
        "D1": {label: {"cases": sum(label in s for s in sequences),
                       "without_prior_A_Validating": sum(before_first(s, label, "A_Validating") for s in sequences),
                       "without_prior_O_Returned": sum(before_first(s, label, "O_Returned") for s in sequences)}
               for label in OUTCOMES},
        "G1": {"cases_with_O_Sent_online_only": sum(SENT[1] in s for s in sequences),
               "cases_online_only_never_mail": sum(SENT[1] in s and SENT[0] not in s for s in sequences)},
        "D2_D3": {"fraud_cases": len(fraud), "fraud_events_by_phase": dict(phase),
                  "outcome_with_fraud_check": dict(Counter(map(outcome, fraud))),
                  "outcome_all_cases": dict(all_outcomes)},
        "D4": {"cases": sum(SHORTENED in s for s in sequences),
               "cases_without_W_Complete_application": sum(SHORTENED in s and "W_Complete application" not in s
                                                           for s in sequences),
               "before_A_Accepted": sum(SHORTENED in s and "A_Accepted" in s
                                        and s.index(SHORTENED) < s.index("A_Accepted") for s in sequences)},
        "D5": {"cases": sum(COLLECTION in s for s in sequences),
               "after_A_Pending": sum(COLLECTION in s and "A_Pending" in s
                                      and s.index(COLLECTION) > s.index("A_Pending") for s in sequences)},
        "work_items_cases": {label: sum(label in s for s in sequences)
                             for label in sorted({a for s in sequences for a in s if a.startswith("W_")})},
        "G2": {"cases_with_O_Create_Offer_after_first_A_Validating": sum(
            "A_Validating" in s and "O_Create Offer" in s[s.index("A_Validating"):] for s in sequences)},
        "decision_level_rules": {
            "O_Cancelled_after_A_Pending_cases": sum(
                "A_Pending" in s and "O_Cancelled" in s[s.index("A_Pending"):] for s in sequences),
            "of_which_single_offer": sum("A_Pending" in s and "O_Cancelled" in s[s.index("A_Pending"):]
                                         and s.count("O_Create Offer") == 1 for s in sequences),
            "O_Cancelled_before_outcome_cases": sum(
                any(a == "O_Cancelled" and (next((k for k, x in enumerate(s) if x in OUTCOMES), None) is None
                                            or i < next(k for k, x in enumerate(s) if x in OUTCOMES))
                    for i, a in enumerate(s)) for s in sequences),
            "A_Denied_without_O_Refused": sum("A_Denied" in s and "O_Refused" not in s for s in sequences)}}


def main():
    data, sequences = load_sequences(ABSTRACTED_CACHE)
    log = event_log(data)
    selection = json.loads(BASE_SELECTION.read_text(encoding="utf-8"))
    if build_tree(()) != BASE or BASE != selection["tree"]:
        raise ValueError("Domain template does not reproduce the abstracted base tree (results/abstraction/base)")
    base_profile = net_profile(pm4py.convert_to_petri_net(parse(BASE))[0])
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "evidence.json", evidence(sequences))
    path = OUT / "screen.json"
    identity = {"input_cache_sha256": sha(ABSTRACTED_CACHE), "tree_edits_sha256": sha(ROOT / "src/tree_edits_domain.py"),
                "model_assessment_sha256": sha(ROOT / "src/model_assessment.py")}
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if result.get("identity") != identity:
        result = {"identity": identity, "edits": EDITS, "domain": list(DOMAIN), "screened": list(SCREENED),
                  "floor_pct": FLOOR, "guards": GUARDS, "candidates": {}, "full_assessment": {}}
    names = [c for c in combinations(DOMAIN)] + [tuple(sorted(DOMAIN + c)) for c in combinations(SCREENED) if c]
    for combination in names:
        name = key(combination)
        if name in result["candidates"]:
            continue
        tree = build_tree(combination)
        result["candidates"][name] = {"edits": list(combination), **screen(tree, sequences, log, base_profile),
                                      "business_rule_violations": model_violations(*pm4py.convert_to_petri_net(parse(tree)))}
        record = result["candidates"][name]
        print(f"{name:24s} {record['coverage']['fitting_percentage']:8.4f} {record['align_et_precision']:.4f} "
              f"{record['size']['nodes']:4d} violations={sorted(record['business_rule_violations'])}", flush=True)
        write_json(path, result)

    def full(name):
        if name not in result["full_assessment"]:
            net, initial, final = pm4py.convert_to_petri_net(parse(result["candidates"][name]["tree"]))
            aligned = alignment_fitness(net, initial, final, sequences)
            token = token_metrics(log, net, initial, final)
            result["full_assessment"][name] = {
                "alignment_generalization": aligned["alignment_generalization"],
                "alignment_fitness": aligned["log_fitness"], "duplicate_visible_labels": duplicate_labels(net),
                "token_generalization": token["generalization"], "token_fitness": token["fitness"]["log_fitness"],
                "token_precision": token["precision"]}
            write_json(path, result)
        return result["full_assessment"][name]

    def guards(name, reference):
        record, ref = result["candidates"][name], result["candidates"][reference]
        values, ref_values = full(name), full(reference)
        return {"generalization_drop": ref_values["alignment_generalization"] - values["alignment_generalization"],
                "arc_degree_drop": ref["arc_degree"] - record["arc_degree"],
                "node_increase": record["size"]["nodes"] / ref["size"]["nodes"] - 1}

    def passes(g):
        return (g["generalization_drop"] <= GUARDS["generalization"] and g["arc_degree_drop"] <= GUARDS["arc_degree"]
                and g["node_increase"] <= GUARDS["node_increase"])

    domain = key(tuple(sorted(DOMAIN)))
    stage2 = [key(tuple(sorted(DOMAIN + c))) for c in combinations(SCREENED)]
    excluded_by_rules = [n for n in stage2 if result["candidates"][n]["business_rule_violations"]]
    eligible = sorted((n for n in stage2 if result["candidates"][n]["sound"] and n not in excluded_by_rules
                       and result["candidates"][n]["coverage"]["fitting_percentage"] >= FLOOR),
                      key=lambda n: (-round(result["candidates"][n]["align_et_precision"], 4),
                                     result["candidates"][n]["size"]["nodes"]))
    checked, selected = [], None
    for name in eligible:
        g = guards(name, domain)
        checked.append({"candidate": name, **full(name), "guards_vs_domain_model": g, "passes": passes(g)})
        print("GUARD", checked[-1], flush=True)
        if passes(g):
            selected = name
            break
    for name in ("base", "R1", domain):
        full(name)
    result["selection"] = {
        "rule": __doc__.split("selected with the rule of scripts/manual_edits_abstracted.py:")[1].split("The same")[0].strip(),
        "eligible": len(eligible), "excluded_by_business_rules": excluded_by_rules, "checked": checked, "selected": selected,
        "selected_vs_abstracted_base": guards(selected, "base") if selected else None,
        "selected_vs_abstracted_base_passes": passes(guards(selected, "base")) if selected else None,
        "previous_final_R1_vs_abstracted_base": guards("R1", "base")}
    write_json(path, result)
    rows = [(n, r["coverage"]["fitting_cases"], round(r["coverage"]["fitting_percentage"], 4),
             round(r["align_et_precision"], 6), r["size"]["nodes"], r["size"]["arcs"], r["extended_cardoso"],
             r["extended_cyclomatic"], round(r["arc_degree"], 6), r["sound"],
             round(result["full_assessment"][n]["alignment_generalization"], 6) if n in result["full_assessment"] else "")
            for n, r in result["candidates"].items()]
    with (OUT / "screen.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["candidate", "fitting_cases", "exact_replay_pct", "align_et_precision", "nodes", "arcs",
                         "extended_cardoso", "extended_cyclomatic", "arc_degree", "sound", "alignment_generalization"])
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
