"""Domain-knowledge edits of the abstracted base tree (work-item log, abstracted_0.65_imf_0.00).

The abstracted log (src/event_abstraction.py) contains every W_ work item as one
event per started instance. Frequent-variant discovery keeps the five frequent
work items; the domain edits add the rest and encode business rules.

Two stages (scripts/domain_edits.py):

1. DOMAIN edits encode business rules of the loan process that the log confirms
   but frequent-variant discovery cannot see or cannot express:
   - ordering rules without a single counterexample in the log (R1, D1);
   - behaviour that matters for simulation but is too rare to survive the
     frequent-variant filter (G1 second send channel, D2 fraud check, D4
     shortened completion, D5 personal-loan collection), so that every W_
     activity of the log is part of the model.
   They are applied as a group, not optimized for precision.
2. SCREENED edits are data-driven candidates (R2, G2, D3). All subsets are
   screened on top of the domain model with the unchanged selection rule and
   guard rails, measured against the domain model.

Every edit replaces one block, so all subsets are sound, block-structured
process trees. Edit codes continue those of src/tree_edits_abstracted.py
(previous base without work items, archived in results/before_workitems/).
"""
from itertools import product

FRAUD = "'W_Assess potential fraud'"
SHORTENED = "'W_Shortened completion '"  # trailing space is part of the original label
COLLECTION = "'W_Personal Loan collection'"

EDITS = {
    "R1": {"stage": "domain", "kind": "restricting",
           "title": "A_Complete only after the first sent offer",
           "rule": "an application is complete only once an offer has been sent",
           "change": "+(A_Complete, W_Call after offers, offer-loop) -> "
                     "->(first offer, +(A_Complete, W_Call after offers, optional further offers))"},
    "D1": {"stage": "domain", "kind": "restricting",
           "title": "A_Pending only after validation",
           "rule": "a loan is approved only after the offer is returned and the documents are validated",
           "change": "->(X(tau, validation), outcome) -> X(early cancellation, early denial, ->(validation, outcome))"},
    "G1": {"stage": "domain", "kind": "generalizing",
           "title": "Offer sent via either channel",
           "rule": "sending online only is the same business step as sending by mail and online",
           "change": "O_Sent (mail and online) -> X(O_Sent (mail and online), O_Sent (online only))"},
    "D2": {"stage": "domain", "kind": "generalizing",
           "title": "Optional fraud check in each validation round",
           "rule": "a fraud assessment can be triggered while documents are validated and affects the decision",
           "change": "->(W_Validate application, A_Validating, X(tau, incomplete)) -> "
                     "->(W_Validate application, A_Validating, X(tau, fraud), X(tau, incomplete))"},
    "D4": {"stage": "domain", "kind": "generalizing",
           "title": "Shortened completion as alternative completion work item",
           "rule": "the application is completed either by the normal or by the shortened completion work item",
           "change": "X(tau, W_Complete application) -> X(tau, W_Complete application, W_Shortened completion)"},
    "D5": {"stage": "domain", "kind": "generalizing",
           "title": "Optional personal-loan collection after approval",
           "rule": "collection of a personal loan follows its approval",
           "change": "A_Pending -> ->(A_Pending, X(tau, W_Personal Loan collection))"},
    "R2": {"stage": "screened", "kind": "restricting",
           "title": "Each validation round starts with W_Validate application",
           "rule": "data-driven (O_Returned inside the validation round instead of concurrent)",
           "change": "+(O_Returned, *(round, tau)) -> *(round with optional O_Returned, tau)"},
    "G2": {"stage": "screened", "kind": "generalizing",
           "title": "New offer between validation rounds",
           "rule": "data-driven (offers created after the first validation)",
           "change": "validation loop redo tau -> X(tau, offer)"},
    "D3": {"stage": "screened", "kind": "generalizing",
           "title": "Optional fraud check after a refusal",
           "rule": "post-decision fraud check; no routing effect",
           "change": "->(A_Denied, O_Refused) -> ->(A_Denied, O_Refused, X(tau, fraud))"},
}
DOMAIN = ("D1", "D2", "D4", "D5", "G1", "R1")
SCREENED = ("D3", "G2", "R2")

BASE = ("->( 'A_Create Application', X( tau, ->( 'A_Submitted', X( tau, 'W_Handle leads' ) ) ), "
        "+( X( tau, 'W_Complete application' ), 'A_Concept' ), 'A_Accepted', "
        "+( 'A_Complete', 'W_Call after offers', *( ->( *( 'O_Create Offer', tau ), 'O_Sent (mail and online)' ), tau ) ), "
        "X( tau, +( 'O_Returned', *( ->( 'W_Validate application', 'A_Validating', "
        "X( tau, ->( 'W_Call incomplete files', 'A_Incomplete' ) ) ), tau ) ) ), "
        "X( ->( X( 'A_Cancelled', 'A_Pending' ), X( tau, 'O_Cancelled' ) ), ->( 'A_Denied', 'O_Refused' ) ) )")


def build_tree(active):
    """Return the process-tree string with the given set of edit ids applied."""
    unknown = set(active) - set(EDITS)
    if unknown:
        raise ValueError(f"Unknown edits: {sorted(unknown)}")
    completion = (f"X( tau, 'W_Complete application', {SHORTENED} )" if "D4" in active
                  else "X( tau, 'W_Complete application' )")
    sent = "X( 'O_Sent (mail and online)', 'O_Sent (online only)' )" if "G1" in active else "'O_Sent (mail and online)'"
    body = f"->( *( 'O_Create Offer', tau ), {sent} )"
    offer = (f"->( {body}, +( 'A_Complete', 'W_Call after offers', X( tau, *( {body}, tau ) ) ) )" if "R1" in active
             else f"+( 'A_Complete', 'W_Call after offers', *( {body}, tau ) )")
    redo = f"X( tau, {body} )" if "G2" in active else "tau"
    fraud = f"X( tau, {FRAUD} ), " if "D2" in active else ""
    incomplete = "X( tau, ->( 'W_Call incomplete files', 'A_Incomplete' ) )"
    if "R2" in active:
        validation = (f"*( ->( 'W_Validate application', 'A_Validating', {fraud}X( tau, 'O_Returned' ), {incomplete} ), "
                      f"{redo} )")
    else:
        validation = f"+( 'O_Returned', *( ->( 'W_Validate application', 'A_Validating', {fraud}{incomplete} ), {redo} ) )"
    denial = f"->( 'A_Denied', 'O_Refused', X( tau, {FRAUD} ) )" if "D3" in active else "->( 'A_Denied', 'O_Refused' )"
    pending = f"->( 'A_Pending', X( tau, {COLLECTION} ) )" if "D5" in active else "'A_Pending'"
    outcome = f"X( ->( X( 'A_Cancelled', {pending} ), X( tau, 'O_Cancelled' ) ), {denial} )"
    if "D1" in active:
        tail = f"X( ->( 'A_Cancelled', X( tau, 'O_Cancelled' ) ), {denial}, ->( {validation}, {outcome} ) )"
    else:
        tail = f"X( tau, {validation} ), {outcome}"
    return (f"->( 'A_Create Application', X( tau, ->( 'A_Submitted', X( tau, 'W_Handle leads' ) ) ), "
            f"+( {completion}, 'A_Concept' ), 'A_Accepted', {offer}, {tail} )")


def combinations(ids):
    ids = sorted(ids)
    for mask in product((False, True), repeat=len(ids)):
        yield tuple(i for i, on in zip(ids, mask) if on)


def parse(tree_string):
    from pm4py.objects.process_tree.utils.generic import parse as pm4py_parse
    return pm4py_parse(tree_string)
