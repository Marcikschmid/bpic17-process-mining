"""Named manual edits of the refined IMf process tree (frequent_0.60_imf_0.03).

Each edit replaces one block of the tree. Edits act on disjoint blocks or on
explicitly combined slots, so every subset is a valid process tree; process
trees are sound and block-structured by construction, and the edited net is
derived with PM4Py's tree-to-net conversion. Restricting edits (R*) remove
behaviour never or rarely observed; generalizing edits (G*) add observed
behaviour. Evidence numbers refer to the completion projection, all 31,509
cases (scripts/manual_edits.py recomputes them).
"""
from itertools import product

EDITS = {
    "R1": {"title": "A_Complete only after the first offer was sent",
           "region": "offer phase",
           "change": "+(A_Complete, offer-loop) -> ->(first offer, +(A_Complete, optional further offers))",
           "petri_net": "first offer iteration moved before the AND-split; offer transitions duplicated for later offers"},
    "R2": {"title": "No direct repetition of O_Sent (mail and online)",
           "region": "offer phase",
           "change": "*(O_Sent (mail and online), tau) -> O_Sent once per offer iteration",
           "petri_net": "silent redo transition of the O_Sent self-loop removed"},
    "R3": {"title": "Validation phase as observed sequence",
           "region": "validation phase",
           "change": "+(W_Validate loop, O_Returned, ->(+(A_Validating/W_Call loop, A_Incomplete loop), outcome)) -> "
                     "+(W_Validate loop, ->(A_Validating, O_Returned, *(tau, ->(A_Incomplete, [W_Call incomplete files], [A_Validating])), outcome))",
           "petri_net": "O_Returned and A_Incomplete leave the AND-block; A_Validating self-loop and W_Call/A_Validating loop replaced by one incomplete-files loop"},
    "R4": {"title": "O_Cancelled scoped to cancelled and pending applications",
           "region": "end phase",
           "change": "trailing X(tau, *(O_Cancelled, tau)) -> mandatory O_Cancelled after A_Cancelled, optional after A_Pending, none after A_Denied/O_Refused",
           "petri_net": "global O_Cancelled loop removed; O_Cancelled transitions inside the outcome branches"},
    "G1": {"title": "Offer sent via either channel",
           "region": "offer phase",
           "change": "O_Sent (mail and online) -> X(O_Sent (mail and online), O_Sent (online only))",
           "petri_net": "one visible transition O_Sent (online only) added in parallel to O_Sent (mail and online)"},
    "G2": {"title": "Late cancellation during validation",
           "region": "validation phase",
           "change": "outcome X(accept, deny) -> X(accept, deny, A_Cancelled)",
           "petri_net": "third outcome branch with A_Cancelled after validation"},
    "G3": {"title": "Several refused offers",
           "region": "end phase",
           "change": "O_Refused -> *(O_Refused, tau)",
           "petri_net": "silent redo transition for O_Refused added"},
}


def build_tree(active):
    """Return the process-tree string with the given set of edit ids applied."""
    unknown = set(active) - set(EDITS)
    if unknown:
        raise ValueError(f"Unknown edits: {sorted(unknown)}")
    sent = {(False, False): "*( 'O_Sent (mail and online)', tau )",
            (True, False): "*( X( 'O_Sent (mail and online)', 'O_Sent (online only)' ), tau )",
            (False, True): "'O_Sent (mail and online)'",
            (True, True): "X( 'O_Sent (mail and online)', 'O_Sent (online only)' )"}["G1" in active, "R2" in active]
    body = f"->( *( ->( 'O_Create Offer', 'O_Created' ), tau ), {sent}, X( tau, 'W_Complete application' ) )"
    offer = (f"->( {body}, +( 'A_Complete', X( tau, *( {body}, tau ) ) ) )" if "R1" in active
             else f"+( 'A_Complete', *( {body}, tau ) )")
    scoped = "R4" in active
    cancelled = "->( 'A_Cancelled', *( 'O_Cancelled', tau ) )" if scoped else "'A_Cancelled'"
    pending = "->( 'O_Accepted', 'A_Pending', X( tau, *( 'O_Cancelled', tau ) ) )" if scoped else "->( 'O_Accepted', 'A_Pending' )"
    refused = "*( 'O_Refused', tau )" if "G3" in active else "'O_Refused'"
    outcome = f"X( {pending}, ->( 'A_Denied', {refused} )" + (f", {cancelled} )" if "G2" in active else " )")
    validate = "X( tau, *( 'W_Validate application', tau ) )"
    if "R3" in active:
        incomplete = "*( tau, ->( 'A_Incomplete', X( tau, 'W_Call incomplete files' ), X( tau, 'A_Validating' ) ) )"
        validation = f"+( {validate}, ->( 'A_Validating', 'O_Returned', {incomplete}, {outcome} ) )"
    else:
        validation = (f"+( {validate}, 'O_Returned', ->( +( *( *( 'A_Validating', tau ), 'W_Call incomplete files' ), "
                      f"X( tau, *( 'A_Incomplete', tau ) ) ), {outcome} ) )")
    tail = "" if scoped else ", X( tau, *( 'O_Cancelled', tau ) )"
    return (f"->( 'A_Create Application', X( tau, ->( 'A_Submitted', X( tau, 'W_Handle leads' ) ) ), 'A_Concept', "
            f"'A_Accepted', {offer}, X( {cancelled}, {validation} ){tail} )")


def all_combinations():
    ids = sorted(EDITS)
    for mask in product((False, True), repeat=len(ids)):
        yield tuple(i for i, on in zip(ids, mask) if on)


def parse(tree_string):
    from pm4py.objects.process_tree.utils.generic import parse as pm4py_parse
    return pm4py_parse(tree_string)
