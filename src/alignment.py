"""Exact PM4Py A* alignments with durable checkpoints after every variant.

Workers receive activity sequences, never a sampled log. The parent expands each
result to all original case indices before PM4Py computes aggregate fitness.
"""

import hashlib
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter

_MODEL = None


def _initialize(model_path, parameters):
    import pm4py
    global _MODEL
    _MODEL = (*pm4py.read_pnml(str(model_path)), parameters)


def _compute(activities):
    from pm4py.algo.conformance.alignments.petri_net import algorithm
    from pm4py.objects.log.obj import Event, Trace
    net, initial, final, parameters = _MODEL
    started = perf_counter()
    value = algorithm.apply_trace(
        Trace([Event({"concept:name": a}) for a in activities]),
        net, initial, final, parameters=dict(parameters),
        variant=algorithm.Variants.VERSION_STATE_EQUATION_A_STAR)
    if value is None:
        return None
    return {**{key: value[key] for key in ("fitness", "cost", "bwc")},
            "seconds": round(perf_counter() - started, 6)}


def _valid(value):
    return (isinstance(value, dict)
            and all(isinstance(value.get(k), (int, float))
                    and math.isfinite(value[k]) for k in ("fitness", "cost", "bwc"))
            and 0 <= value["fitness"] <= 1 and 0 <= value["cost"] <= value["bwc"])


def align_variants(log, model_path, checkpoint_dir, identity, parameters,
                   workers=8, force=False, progress=True):
    """Return case-expanded exact results; persist only completed alignments.

    Without an explicit max_align_time_trace parameter PM4Py uses sys.maxsize.
    There is no parent deadline. Existing checkpoints are reused only if their
    complete input/model/version/cost identity and activity sequence match.
    """
    groups = {}
    for i, trace in enumerate(log):
        groups.setdefault(tuple(e["concept:name"] for e in trace), []).append(i)
    directory = Path(checkpoint_dir)
    directory.mkdir(parents=True, exist_ok=True)
    replay = [None] * len(log)
    pending = []
    reused = 0
    completed_variants = 0
    started = last_message = perf_counter()

    def destination(activities):
        digest = hashlib.sha256(json.dumps(activities, ensure_ascii=False,
                                          separators=(",", ":")).encode("utf-8")).hexdigest()
        return directory / f"{digest}.json"

    def accept(activities, value, persist):
        nonlocal completed_variants, last_message
        if value is None:
            return
        if not _valid(value):
            raise ValueError("Invalid alignment checkpoint/result")
        if persist:
            path = destination(activities)
            temporary = path.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(json.dumps({"identity": identity,
                "activities": activities, "alignment": value}, ensure_ascii=False,
                allow_nan=False) + "\n", encoding="utf-8", newline="\n")
            temporary.replace(path)
        for index in groups[activities]:
            replay[index] = value
        completed_variants += 1
        now = perf_counter()
        if progress and (now - last_message >= 30 or completed_variants == len(groups)):
            print(f"ALIGNMENT {completed_variants}/{len(groups)} variants; "
                  f"{sum(v is not None for v in replay)}/{len(log)} cases; "
                  f"elapsed {now - started:.1f}s", flush=True)
            last_message = now

    for activities, indices in groups.items():
        path = destination(activities)
        saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() and not force else None
        if (saved is not None and saved.get("identity") == identity
                and saved.get("activities") == list(activities) and _valid(saved.get("alignment"))):
            accept(activities, saved["alignment"], False)
            reused += len(indices)
        else:
            pending.append(activities)
    if progress:
        print(f"REUSE {completed_variants}/{len(groups)} variants ({reused} cases); "
              f"START {len(pending)} variants with {workers} workers; "
              f"trace timeout={parameters.get('max_align_time_trace', 'unlimited')}", flush=True)
    if pending and workers == 1:
        _initialize(model_path, parameters)
        for activities in pending:
            accept(activities, _compute(activities), True)
    elif pending:
        with ProcessPoolExecutor(max_workers=workers, initializer=_initialize,
                                 initargs=(str(model_path), parameters)) as pool:
            futures = {pool.submit(_compute, a): a for a in pending}
            for future in as_completed(futures):
                accept(futures.pop(future), future.result(), True)
    return replay, reused
