"""Descriptive statistics of the unchanged raw log (Assignment 3.2).

Variants use exact activity names in stored event order. Case duration is the
UTC elapsed time between minimum and maximum event timestamps. Population
standard deviations describe the complete supplied log; sample SDs are exported
separately. No lifecycle filtering, sorting, trimming, or imputation is performed.
"""

import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from statistics import fmean, pstdev, stdev

IDENTIFIERS = {"EventID", "OfferID"}


def quantile(values, probability):
    """Linear interpolation, equivalent to numpy.quantile(method='linear')."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def describe(values):
    if not values:
        raise ValueError("Cannot describe an empty population")
    return {"n": len(values), "mean": fmean(values), "std_population": pstdev(values),
            "std_sample": stdev(values) if len(values) > 1 else None,
            "min": min(values), "q25": quantile(values, .25),
            "median": quantile(values, .5), "q75": quantile(values, .75),
            "p95": quantile(values, .95), "max": max(values)}


def _kind(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "numeric"
    if isinstance(value, datetime):
        return "timestamp"
    if isinstance(value, str):
        return "string"
    raise TypeError(f"Unsupported XES attribute value: {type(value).__name__}")


def _collect(profiles, attributes):
    for name, value in attributes.items():
        profile = profiles.setdefault(name, {"present": 0, "null": 0, "kinds": Counter(), "values": set()})
        profile["present"] += 1
        if value is None:
            profile["null"] += 1
        else:
            kind = _kind(value)
            profile["kinds"][kind] += 1
            # Booleans must not collapse into numeric values through True == 1.
            profile["values"].add((kind, value))


def _profiles(profiles, total, case=False):
    output = {}
    for name, profile in sorted(profiles.items()):
        kinds = set(profile["kinds"])
        if kinds <= {"string", "boolean"} and kinds:
            category = "categorical"
        elif kinds == {"numeric"}:
            category = "numeric"
        elif kinds == {"timestamp"}:
            category = "timestamp"
        else:
            category = "mixed_or_empty"
        output[name] = {"classification": category,
            "identifier": name in IDENTIFIERS or (case and name == "concept:name"),
            "present": profile["present"], "absent": total - profile["present"],
            "null": profile["null"], "missing": total - profile["present"] + profile["null"],
            "missing_percentage": 100 * (total - profile["present"] + profile["null"]) / total,
            "distinct_non_null": len(profile["values"]), "value_types": dict(sorted(profile["kinds"].items()))}
    return output


def variant_id(activities):
    return hashlib.sha256(json.dumps(activities, ensure_ascii=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def compute_statistics(log):
    """Return summary plus row-oriented exports, retaining every supplied case."""
    case_profiles, event_profiles = {}, {}
    variants, lifecycle_variants = Counter(), Counter()
    activities, lifecycles, resources, months = Counter(), Counter(), Counter(), Counter()
    cases, seen_ids = [], set()
    events = missing_resource = descending_pairs = unsorted_cases = 0
    earliest = latest = None
    for trace in log:
        case_id = trace.attributes.get("concept:name")
        if case_id is None or case_id in seen_ids:
            raise ValueError("Every case must have a unique, non-null case ID")
        seen_ids.add(case_id)
        if not trace:
            raise ValueError("Empty cases require an explicit duration policy")
        _collect(case_profiles, trace.attributes)
        labels, lifecycle_sequence, times = [], [], []
        for event in trace:
            if event.get("concept:name") is None or event.get("time:timestamp") is None:
                raise ValueError("Activity and timestamp are required on every event")
            timestamp = event["time:timestamp"]
            if not isinstance(timestamp, datetime) or timestamp.utcoffset() is None:
                raise ValueError("Event timestamps must be timezone-aware datetimes")
            timestamp = timestamp.astimezone(timezone.utc)
            times.append(timestamp)
            label, lifecycle = event["concept:name"], event.get("lifecycle:transition")
            labels.append(label)
            lifecycle_sequence.append((label, lifecycle))
            activities[label] += 1
            lifecycles[lifecycle] += 1
            resource = event.get("org:resource")
            if resource is None:
                missing_resource += 1
            else:
                resources[str(resource)] += 1
            _collect(event_profiles, event)
        first, last = min(times), max(times)
        backwards = sum(b < a for a, b in zip(times, times[1:]))
        descending_pairs += backwards
        unsorted_cases += backwards > 0
        earliest = first if earliest is None else min(first, earliest)
        latest = last if latest is None else max(last, latest)
        months[first.strftime("%Y-%m")] += 1
        events += len(trace)
        variants[tuple(labels)] += 1
        lifecycle_variants[tuple(lifecycle_sequence)] += 1
        cases.append({"case_id": case_id, "events": len(trace),
            "duration_seconds": (last - first).total_seconds(),
            "start_utc": first.isoformat(), "end_utc": last.isoformat(),
            "variant_id": variant_id(labels), "descending_timestamp_pairs": backwards})
    if not cases:
        raise ValueError("The log is empty")
    lengths = describe([c["events"] for c in cases])
    seconds = describe([c["duration_seconds"] for c in cases])
    duration = {}
    for unit, divisor in (("seconds", 1), ("minutes", 60), ("days", 86400)):
        duration[unit] = {k: v if k == "n" or v is None else v / divisor for k, v in seconds.items()}
    ordered_variants = sorted(variants.items(), key=lambda item: (-item[1], item[0]))
    variant_rows = [{"rank": rank, "variant_id": variant_id(sequence),
        "events": len(sequence), "cases": count, "case_percentage": 100 * count / len(cases)}
        for rank, (sequence, count) in enumerate(ordered_variants, 1)]
    event_attributes = _profiles(event_profiles, events)
    categorical = [name for name, item in event_attributes.items() if item["classification"] == "categorical"]
    summary = {"cases": len(cases), "events": events, "variants": len(variants),
        "activity_lifecycle_variants": len(lifecycle_variants),
        "distinct_activities": len(activities), "case_attribute_count": len(case_profiles),
        "event_attribute_count": len(event_profiles),
        "case_length": lengths, "case_duration": duration,
        "categorical_event_attributes": categorical, "categorical_event_attribute_count": len(categorical),
        "categorical_event_attributes_excluding_event_offer_ids": [a for a in categorical if a not in IDENTIFIERS],
        "case_attributes": _profiles(case_profiles, len(cases), case=True), "event_attributes": event_attributes,
        "activity_counts": dict(sorted(activities.items())),
        "lifecycle_counts": {str(k) if k is not None else "<missing>": v for k, v in sorted(lifecycles.items(), key=lambda x: str(x[0]))},
        "resource_count": len(resources), "resource_event_counts": dict(sorted(resources.items())),
        "events_without_resource": missing_resource,
        "case_start_month_counts_utc": dict(sorted(months.items())),
        "first_event_utc": earliest.isoformat(), "last_event_utc": latest.isoformat(),
        "variant_concentration": {f"top_{k}_case_percentage": 100 * sum(c for _, c in ordered_variants[:k]) / len(cases) for k in (1, 5, 10)},
        "singleton_variants": sum(c == 1 for c in variants.values()),
        "quality_checks": {"unique_case_ids": len(seen_ids), "empty_cases": 0,
            "events_missing_activity_or_timestamp": 0, "cases_with_descending_timestamps": unsorted_cases,
            "descending_timestamp_pairs": descending_pairs},
        "definitions": {"input": "Unchanged raw log; all lifecycle states retained",
            "variant": "Exact concept:name sequence in original XES order; no trimming or sorting",
            "alternative_variant": "Exact (concept:name, lifecycle:transition) sequence in original XES order",
            "duration": "max(event timestamp) - min(event timestamp), elapsed UTC wall-clock time; not working time",
            "standard_deviation": "Population SD, ddof=0, complete supplied log; sample SD ddof=1 also exported",
            "quantiles": "Linear interpolation (Hyndman-Fan type 7)",
            "attribute_names": "Union over all cases/events; scope kept separate; identifiers included",
            "categorical": "Non-null observed types are strings/booleans; includes EventID and OfferID nominal identifiers",
            "numeric": "Integer/float quantities, including NumberOfTerms and CreditScore; low cardinality does not make them categorical",
            "missing": "Absent attribute or explicit null; blank strings are retained as actual values",
            "resource_count": "Distinct non-null org:resource values, including system resource identifiers"}}
    assert sum(c["cases"] for c in variant_rows) == len(cases)
    assert sum(c["cases"] * c["events"] for c in variant_rows) == events
    return summary, cases, variant_rows
