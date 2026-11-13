"""Named manual edits of the abstracted base tree (abstracted_0.70_imf_0.00).

Same principle as src/tree_edits.py: each edit replaces one block of the
process tree, edits act on disjoint blocks, so all 2^5 subsets are valid
process trees (sound and block-structured by construction). Edits were derived
from the conformance diagnostics of the base model
(results/assessment/abstracted_base_diagnostics/) before any combination was
screened. Evidence numbers refer to the abstracted log, all 31,509 cases
(scripts/manual_edits_abstracted.py recomputes them).
"""
from itertools import product

EDITS = {
    "R1": {"title": "A_Complete only after the first sent offer",
           "region": "offer phase", "kind": "restricting",
           "diagnostic": "escaping O_Create Offer -> A_Complete and A_Accepted -> A_Complete",
           "change": "+(A_Complete, offer-loop) -> ->(first offer, +(A_Complete, optional further offers))",
           "petri_net": "first offer moved before the AND-split; offer transitions duplicated for later offers"},
    "R2": {"title": "Each validation round starts with A_Validating",
           "region": "validation phase", "kind": "restricting",
           "diagnostic": "escaping A_Complete -> O_Returned, A_Validating -> A_Validating",
           "change": "+(O_Returned, *(->(A_Validating, [A_Incomplete]), tau)) -> "
                     "*(->(A_Validating, [O_Returned], [A_Incomplete]), tau)",
           "petri_net": "AND-block around O_Returned removed; O_Returned inside the validation round"},
    "R3": {"title": "Pending and denial only after validation",
           "region": "end phase", "kind": "restricting",
           "diagnostic": "escaping A_Complete -> A_Pending and O_Sent -> A_Pending",
           "change": "->(X(tau, validation), outcome) -> X(early cancellation, ->(validation, outcome))",
           "petri_net": "validation skip replaced by an early-cancellation branch; A_Cancelled and O_Cancelled duplicated"},
    "G1": {"title": "Offer sent via either channel",
           "region": "offer phase", "kind": "generalizing",
           "diagnostic": "log moves O_Sent (online only)",
           "change": "O_Sent (mail and online) -> X(O_Sent (mail and online), O_Sent (online only))",
           "petri_net": "one visible transition O_Sent (online only) per send position"},
    "G2": {"title": "New offer between validation rounds",
           "region": "validation phase", "kind": "generalizing",
           "diagnostic": "log moves O_Create Offer (largest fitness leak)",
           "change": "validation loop redo tau -> X(tau, offer)",
           "petri_net": "offer transitions duplicated inside the validation loop"},
}

BASE = ("->( 'A_Create Application', X( tau, 'A_Submitted' ), 'A_Concept', 'A_Accepted', "
        "+( 'A_Complete', *( ->( *( 'O_Create Offer', tau ), 'O_Sent (mail and online)' ), tau ) ), "
        "X( tau, +( 'O_Returned', *( ->( 'A_Validating', X( tau, 'A_Incomplete' ) ), tau ) ) ), "
        "X( ->( X( 'A_Cancelled', 'A_Pending' ), X( tau, 'O_Cancelled' ) ), ->( 'A_Denied', 'O_Refused' ) ) )")


def build_tree(active):
    """Return the process-tree string with the given set of edit ids applied."""
    unknown = set(active) - set(EDITS)
    if unknown:
        raise ValueError(f"Unknown edits: {sorted(unknown)}")
    sent = "X( 'O_Sent (mail and online)', 'O_Sent (online only)' )" if "G1" in active else "'O_Sent (mail and online)'"
    body = f"->( *( 'O_Create Offer', tau ), {sent} )"
    offer = (f"->( {body}, +( 'A_Complete', X( tau, *( {body}, tau ) ) ) )" if "R1" in active
             else f"+( 'A_Complete', *( {body}, tau ) )")
    redo = f"X( tau, {body} )" if "G2" in active else "tau"
    if "R2" in active:
        validation = f"*( ->( 'A_Validating', X( tau, 'O_Returned' ), X( tau, 'A_Incomplete' ) ), {redo} )"
    else:
        validation = f"+( 'O_Returned', *( ->( 'A_Validating', X( tau, 'A_Incomplete' ) ), {redo} ) )"
    outcome = "X( ->( X( 'A_Cancelled', 'A_Pending' ), X( tau, 'O_Cancelled' ) ), ->( 'A_Denied', 'O_Refused' ) )"
    if "R3" in active:
        tail = f"X( ->( 'A_Cancelled', X( tau, 'O_Cancelled' ) ), ->( {validation}, {outcome} ) )"
    else:
        tail = f"X( tau, {validation} ), {outcome}"
    return (f"->( 'A_Create Application', X( tau, 'A_Submitted' ), 'A_Concept', 'A_Accepted', "
            f"{offer}, {tail} )")


def all_combinations():
    ids = sorted(EDITS)
    for mask in product((False, True), repeat=len(ids)):
        yield tuple(i for i, on in zip(ids, mask) if on)


def parse(tree_string):
    from pm4py.objects.process_tree.utils.generic import parse as pm4py_parse
    return pm4py_parse(tree_string)
