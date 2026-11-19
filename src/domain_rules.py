"""Business rules of the loan process that the final model must not violate.

Each rule holds in every case of the abstracted log (zero counterexamples,
scripts/domain_edits.py recomputes the counts). A model violates a rule if some
complete or partial run fires the target activity before any of the required
activities, or fires two outcome activities. The check explores the full
reachability graph of the (bounded, sound) Petri net, extended by the set of
required labels already fired, so it covers the whole model language, not only
the observed traces.
"""
from collections import deque

SENT = ("O_Sent (mail and online)", "O_Sent (online only)")
PRECEDENCE = (
    ("A_Pending", ("O_Returned",), "approval only after the signed offer is returned"),
    ("A_Pending", ("A_Validating",), "approval only after the documents are validated"),
    ("A_Complete", SENT, "application complete only after an offer was sent"),
    ("W_Call after offers", SENT, "call after offers only after an offer was sent"),
    ("O_Returned", SENT, "an offer can only be returned after it was sent"),
    ("A_Validating", SENT, "validation only after an offer was sent"),
    ("A_Incomplete", ("A_Validating",), "incompleteness is found during validation"),
    ("W_Call incomplete files", ("A_Validating",), "calls about missing files follow validation"),
    ("O_Refused", ("A_Denied",), "offers are refused because the application is denied"),
    ("O_Create Offer", ("A_Accepted",), "offers are created only for accepted applications"),
)
OUTCOMES = ("A_Pending", "A_Denied", "A_Cancelled")


def rule_name(target, required):
    return f"{target} after {' or '.join(required)}"


def log_counterexamples(sequences):
    """Counterexamples per rule in the log (all must be 0 for a rule to be used)."""
    result = {}
    for target, required, _ in PRECEDENCE:
        bad = 0
        for s in sequences:
            if target in s and not any(r in s[:s.index(target)] for r in required):
                bad += 1
        result[rule_name(target, required)] = bad
    result["at most one outcome"] = sum(len({a for a in s if a in OUTCOMES}) > 1 for s in sequences)
    return result


def model_violations(net, initial, final=None, max_states=200000):
    """Rules the model can violate: {rule: example firing sequence (visible labels)}."""
    from pm4py.objects.petri_net import semantics
    tracked = sorted({r for _, req, _ in PRECEDENCE for r in req} | set(OUTCOMES))
    start = (initial, frozenset())
    seen, queue, found = {start}, deque([(initial, frozenset(), ())]), {}
    while queue:
        marking, fired, path = queue.popleft()
        for transition in semantics.enabled_transitions(net, marking):
            label = transition.label
            if label is not None:
                for target, required, _ in PRECEDENCE:
                    name = rule_name(target, required)
                    if label == target and not fired & set(required) and name not in found:
                        found[name] = list(path) + [label]
                if label in OUTCOMES and fired & (set(OUTCOMES) - {label}) and "at most one outcome" not in found:
                    found["at most one outcome"] = list(path) + [label]
            following = semantics.execute(transition, net, marking)
            now = fired | ({label} if label in tracked else set())
            state = (following, now)
            if state not in seen:
                if len(seen) >= max_states:
                    raise ValueError("State limit reached in the domain-rule check")
                seen.add(state)
                queue.append((following, now, path + ((label,) if label is not None else ())))
    return found
