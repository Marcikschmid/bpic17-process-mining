"""Event abstraction of the completion projection: remove logging artefacts, keep edge cases.

Applied per case to the completion events in their original XES order, before
refinement discovery. Only events that carry no control-flow information of
their own are touched; rare but real behaviour (fraud checks, the online-only
send channel, late cancellations, denied applications) stays in the log.
Evidence for every rule is recomputed by scripts/abstract_log.py
(results/abstraction/abstraction_audit.json).

Rules
-----
MIRROR (drop): one system action recorded on two objects. ``O_Created`` always
directly follows ``O_Create Offer``; ``O_Accepted`` always directly precedes
``A_Pending`` (same second).

WORK_ITEM (drop): completion events of five workflow work items. Their raw
events are mostly schedule/start/suspend/resume/abort; whether a ``complete``
is logged depends on the work-item life cycle, and when it is logged it
mostly coincides (<= 1 s) with an application state change (``A_Complete``,
``A_Incomplete``, ``A_Validating``, ``A_Concept``). ``W_Assess potential
fraud`` is kept: a fraud check is a real exceptional path, not a mirror.

SIMULTANEOUS (collapse): a direct repetition of ``O_Cancelled``,
``O_Refused`` or one of the two ``O_Sent`` labels within ``SIMULTANEITY_SECONDS``
of the previous kept event with that label is one application-level action
recorded once per open offer; only the first event is kept. Repetitions that
are further apart are kept. The online-only send channel itself stays (edge
case); only its simultaneous per-offer repetitions are collapsed.
"""
from collections import Counter

MIRROR = ("O_Created", "O_Accepted")
WORK_ITEM = ("W_Complete application", "W_Validate application", "W_Call incomplete files",
             "W_Handle leads", "W_Call after offers")
KEPT_EDGE_CASES = ("W_Assess potential fraud", "O_Sent (online only)")
SIMULTANEOUS = ("O_Cancelled", "O_Refused", "O_Sent (mail and online)", "O_Sent (online only)")
SIMULTANEITY_SECONDS = 1.0
DROPPED = frozenset(MIRROR + WORK_ITEM)

RULES = {
    "MIRROR": {"action": "drop", "labels": list(MIRROR),
               "reason": "same system action as the neighbouring event on the other object"},
    "WORK_ITEM": {"action": "drop", "labels": list(WORK_ITEM),
                  "reason": "presence of the complete event depends on the work-item life cycle; "
                            "logged together with an application state change"},
    "SIMULTANEOUS": {"action": "collapse direct repetition", "labels": list(SIMULTANEOUS),
                     "max_seconds": SIMULTANEITY_SECONDS,
                     "reason": "one application-level action recorded once per open offer"},
    "KEPT": {"action": "keep", "labels": list(KEPT_EDGE_CASES),
             "reason": "rare but real behaviour (edge cases), not a logging artefact"},
}


def abstract_events(events, timestamp_key="time:timestamp", activity_key="concept:name"):
    """Return (kept events, Counter of applied rules) for one case.

    ``events``: completion events in log order; each a mapping with the activity
    and a numeric timestamp in seconds. Event objects are returned unchanged
    (no copies, no relabelling); dropped and collapsed events are counted.
    """
    kept, applied = [], Counter()
    for event in events:
        label = event[activity_key]
        if label in DROPPED:
            applied["MIRROR" if label in MIRROR else "WORK_ITEM"] += 1
            continue
        if label in SIMULTANEOUS and kept and kept[-1][activity_key] == label:
            previous, current = kept[-1].get(timestamp_key), event.get(timestamp_key)
            if previous is None or current is None:
                raise ValueError(f"Missing timestamp for simultaneous-repetition check of {label!r}")
            if abs(current - previous) <= SIMULTANEITY_SECONDS:
                applied["SIMULTANEOUS"] += 1
                continue
        kept.append(event)
    if not kept:
        raise ValueError("Event abstraction removed every event of a case.")
    return kept, applied


def abstract_labels(labels, timestamps):
    """Sequence form of :func:`abstract_events` for parallel label/timestamp lists."""
    if len(labels) != len(timestamps):
        raise ValueError("labels and timestamps differ in length")
    events = [{"concept:name": a, "time:timestamp": t} for a, t in zip(labels, timestamps)]
    kept, applied = abstract_events(events)
    return [e["concept:name"] for e in kept], applied
