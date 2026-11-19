"""Event abstraction of the raw log: remove logging artefacts, keep every business step.

Applied per case to the raw events in their original XES order, before
refinement discovery. Application (A_) and offer (O_) events enter as
completion events; workflow (W_) work items enter as one event per started
work-item instance. Evidence for every rule is recomputed by
scripts/abstract_log.py (results/abstraction/abstraction_audit.json).

Rules
-----
MIRROR (drop): one system action recorded on two objects. ``O_Created`` always
directly follows ``O_Create Offer``; ``O_Accepted`` always directly precedes
``A_Pending`` (same second).

SIMULTANEOUS (collapse): a direct repetition of ``O_Cancelled``,
``O_Refused`` or one of the two ``O_Sent`` labels within ``SIMULTANEITY_SECONDS``
of the previous kept A_/O_ event with that label is one application-level
action recorded once per open offer; only the first event is kept. Repetitions
that are further apart are kept.

WORK_ITEM (one event per started instance; since 2026-11-19): every W_ work item
is a real piece of work (an employee handles it, which matters for resources and
timing), but its life cycle is logged as schedule/start/suspend/resume and ends
in ``complete``, ``ate_abort`` or ``withdraw``. Most instances never log a
``complete`` (e.g. ``W_Call after offers``: 342 completions for 31,000+ started
instances), so the completion projection loses almost all work items. Each
instance is therefore represented by its first ``start`` event (label kept);
suspend/resume cycles and the terminal event are not separate steps, and
instances withdrawn before any start (no work done) produce no event. All eight
W_ activities are covered, including the fraud check.

Before 2026-11-19 the five frequent W_ completion events were dropped and only
``W_Assess potential fraud`` (completion) was kept; that version is archived in
results/before_workitems/.
"""
from collections import Counter

MIRROR = ("O_Created", "O_Accepted")
WORK_ITEM_PREFIX = "W_"
TERMINAL = ("complete", "ate_abort", "withdraw")
KEPT_EDGE_CASES = ("O_Sent (online only)",)
SIMULTANEOUS = ("O_Cancelled", "O_Refused", "O_Sent (mail and online)", "O_Sent (online only)")
SIMULTANEITY_SECONDS = 1.0

RULES = {
    "MIRROR": {"action": "drop", "labels": list(MIRROR),
               "reason": "same system action as the neighbouring event on the other object"},
    "SIMULTANEOUS": {"action": "collapse direct repetition", "labels": list(SIMULTANEOUS),
                     "max_seconds": SIMULTANEITY_SECONDS,
                     "reason": "one application-level action recorded once per open offer"},
    "WORK_ITEM": {"action": "one event per started work-item instance (first start)", "labels": "all W_ activities",
                  "reason": "real work, but its life cycle rarely ends in complete; suspend/resume and the "
                            "terminal event are not separate business steps"},
    "KEPT": {"action": "keep", "labels": list(KEPT_EDGE_CASES),
             "reason": "rare but real behaviour (edge case), not a logging artefact"},
}


def is_work_item(label):
    return label.startswith(WORK_ITEM_PREFIX)


def abstract_events(events, timestamp_key="time:timestamp", activity_key="concept:name"):
    """Completion-level rules for one case: (kept events, Counter of applied rules).

    ``events``: completion events in log order; each a mapping with the activity
    and a numeric timestamp in seconds. W_ completion events are dropped here
    (work items enter through :func:`work_item_instances`); mirrors are dropped
    and simultaneous repetitions collapsed. Event objects are returned unchanged.
    """
    kept, applied = [], Counter()
    for event in events:
        label = event[activity_key]
        if label in MIRROR:
            applied["MIRROR"] += 1
            continue
        if is_work_item(label):
            applied["WORK_ITEM_COMPLETION"] += 1
            continue
        if label in SIMULTANEOUS and kept and kept[-1][activity_key] == label:
            previous, current = kept[-1].get(timestamp_key), event.get(timestamp_key)
            if previous is None or current is None:
                raise ValueError(f"Missing timestamp for simultaneous-repetition check of {label!r}")
            if abs(current - previous) <= SIMULTANEITY_SECONDS:
                applied["SIMULTANEOUS"] += 1
                continue
        kept.append(event)
    return kept, applied


def work_item_instances(events, activity_key="concept:name", lifecycle_key="lifecycle:transition"):
    """Return (first start event of every W_ work-item instance, Counter) for one case, in log order.

    An instance opens with ``schedule`` or ``start`` and closes with a terminal
    transition; a later ``start`` of the same activity opens a new instance.
    ``resume`` never opens an instance.
    """
    state, starts, applied = {}, [], Counter()
    for event in events:
        label = event[activity_key]
        if not is_work_item(label):
            continue
        transition = event[lifecycle_key]
        if transition == "start" and state.get(label) != "started":
            state[label] = "started"
            starts.append(event)
            continue
        if transition == "schedule" and state.get(label) != "started":
            state[label] = "scheduled"
        elif transition in TERMINAL:
            state.pop(label, None)
        applied["WORK_ITEM_LIFECYCLE"] += 1
    return starts, applied


def abstract_case(events, timestamp_key="time:timestamp", activity_key="concept:name",
                  lifecycle_key="lifecycle:transition"):
    """Full abstraction of one case from its raw events (all life-cycle transitions, XES order).

    A_/O_ completion events pass the completion-level rules; W_ work items enter
    once per started instance. The result keeps the original event order.
    """
    completions = [e for e in events if e[lifecycle_key] == "complete" and not is_work_item(e[activity_key])]
    kept, applied = abstract_events(completions, timestamp_key, activity_key)
    starts, work = work_item_instances(events, activity_key, lifecycle_key)
    applied.update(work)
    applied["WORK_ITEM_COMPLETION"] = sum(1 for e in events
                                          if is_work_item(e[activity_key]) and e[lifecycle_key] == "complete")
    selected = {id(e) for e in kept} | {id(e) for e in starts}
    result = [e for e in events if id(e) in selected]
    if not result:
        raise ValueError("Event abstraction removed every event of a case.")
    return result, applied


def abstract_labels(labels, timestamps, lifecycles=None):
    """Sequence form of :func:`abstract_case` (or of :func:`abstract_events` without life cycles)."""
    if len(labels) != len(timestamps) or (lifecycles is not None and len(lifecycles) != len(labels)):
        raise ValueError("labels, timestamps and life cycles differ in length")
    if lifecycles is None:
        events = [{"concept:name": a, "time:timestamp": t} for a, t in zip(labels, timestamps)]
        kept, applied = abstract_events(events)
        if not kept:
            raise ValueError("Event abstraction removed every event of a case.")
    else:
        events = [{"concept:name": a, "time:timestamp": t, "lifecycle:transition": l}
                  for a, t, l in zip(labels, timestamps, lifecycles)]
        kept, applied = abstract_case(events)
    return [e["concept:name"] for e in kept], applied
