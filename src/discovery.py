"""Comparable discovery baselines on the completion projection of an EventLog."""

from collections import Counter
from copy import copy

from src.runtime import configure_runtime

configure_runtime()
import pm4py
from pm4py.algo.discovery.heuristics import algorithm as heuristics_miner
from pm4py.objects.log.obj import Event, EventLog, Trace


INDUCTIVE_PARAMETERS = {
    "noise_threshold": 0.0,
    "multi_processing": False,
    "disable_fallthroughs": False,
    "activity_key": "concept:name",
    "timestamp_key": "time:timestamp",
    "case_id_key": "case:concept:name",
}
HEURISTICS_PARAMETERS = {
    "dependency_thresh": 0.5,
    "and_measure_thresh": 0.65,
    "loop_length_two_thresh": 0.5,
    "min_act_count": 1,
    "min_dfg_occurrences": 1,
    "dfg_pre_cleaning_noise_thresh": 0.05,
    "pm4py:param:activity_key": "concept:name",
    "pm4py:param:timestamp_key": "time:timestamp",
    "pm4py:param:case_id_key": "case:concept:name",
}


def completion_projection(log):
    """Keep completed events in their XES order; fail rather than drop cases."""
    case_ids = [trace.attributes.get("concept:name") for trace in log]
    if not case_ids or any(case_id is None for case_id in case_ids):
        raise ValueError("The log is empty or a case identifier is missing.")
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Case identifiers must be unique.")
    lifecycle = Counter()
    raw_activities = set()
    # The PM4Py event-level filter converts through an EventStream and can
    # inject case attributes into the input events. Build independent events
    # directly to keep both the raw file and the in-memory raw log unchanged.
    projected = EventLog(attributes=copy(log.attributes), extensions=copy(log.extensions),
                         classifiers=copy(log.classifiers), omni_present=copy(log.omni_present),
                         properties=copy(log.properties))
    for trace in log:
        completed = Trace(attributes=copy(trace.attributes))
        for event in trace:
            for key in ("concept:name", "time:timestamp", "lifecycle:transition"):
                if event.get(key) is None:
                    raise ValueError(f"Missing {key} in case {trace.attributes['concept:name']}")
            lifecycle[event["lifecycle:transition"]] += 1
            raw_activities.add(event["concept:name"])
            if event["lifecycle:transition"] == "complete":
                completed.append(Event(dict(event)))
        if not completed:
            raise ValueError("Completion filtering removed/reordered cases; a case has no completed events.")
        projected.append(completed)
    if [trace.attributes["concept:name"] for trace in projected] != case_ids:
        raise ValueError("Completion filtering removed/reordered cases; review preprocessing.")
    if any(not trace for trace in projected):
        raise ValueError("Completion projection contains an empty trace.")
    activities = Counter(event["concept:name"] for trace in projected for event in trace)
    summary = {
        "raw_cases": len(log),
        "raw_events": sum(lifecycle.values()),
        "raw_distinct_activities": len(raw_activities),
        "raw_lifecycle_counts": dict(sorted(lifecycle.items())),
        "discovery_cases": len(projected),
        "discovery_events": sum(activities.values()),
        "discovery_distinct_activities": len(activities),
        "discovery_activity_counts": dict(sorted(activities.items())),
        "activities_absent_after_projection": sorted(raw_activities - activities.keys()),
        "excluded_events": sum(lifecycle.values()) - sum(activities.values()),
        "case_identifiers_and_order_preserved": True,
        "event_order": "Original XES order within each trace; no timestamp sorting.",
        "filter": {"attribute": "lifecycle:transition", "values": ["complete"], "level": "event"},
        "other_preprocessing": "None; no case, outcome, date, activity or frequency filtering; no sampling or label changes.",
    }
    return projected, summary


def discover_inductive(log):
    return pm4py.discover_petri_net_inductive(log, **INDUCTIVE_PARAMETERS)


def discover_heuristics(log):
    return heuristics_miner.apply(
        log, parameters=HEURISTICS_PARAMETERS, variant=heuristics_miner.Variants.CLASSIC
    )


def structure_summary(net, initial_marking, final_marking):
    """Structural counts only, not fitness/precision/simplicity quality scores."""
    return {
        "places": len(net.places),
        "transitions": len(net.transitions),
        "visible_transitions": sum(t.label is not None for t in net.transitions),
        "silent_transitions": sum(t.label is None for t in net.transitions),
        "arcs": len(net.arcs),
        "activity_labels": sorted({t.label for t in net.transitions if t.label is not None}),
        "initial_tokens": sum(initial_marking.values()),
        "final_tokens": sum(final_marking.values()),
    }
