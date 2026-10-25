"""Memory-bounded orchestration of PM4Py Align-ETConformance.

Same global prefixes, weights, PM4Py alignments and escaping-edge formula as
pm4py.algo.evaluation.precision.variants.align_etconformance.apply (2.7.23.11).
Batching avoids retaining all synchronous-product nets simultaneously.
"""

import gc
from functools import lru_cache

from src.runtime import configure_runtime
configure_runtime()
from pm4py.algo.evaluation.precision import utils as precision_utils
from pm4py.algo.evaluation.precision.variants import align_etconformance as pm_precision
from pm4py.objects.petri_net.obj import Marking
from pm4py.objects.petri_net.utils import check_soundness
from pm4py.objects.petri_net.utils.align_utils import get_visible_transitions_eventually_enabled_by_marking


def alignment_precision_batched(log, net, initial, final, parameters=None, batch_size=128, progress=False):
    """Exact PM4Py Align-ET score; batch prefixes, never partition the log metric.

    Averaging precision values of log batches would be incorrect: observed next
    activities must be taken from the entire log. Build that global map ONCE.
    Only the independent prefix-alignment jobs are split into batches.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    parameters = dict(parameters or {})
    if not check_soundness.check_easy_soundness_net_in_fin_marking(net, initial, final):
        raise ValueError("Align-ET requires a reachable final marking (PM4Py easy-soundness check).")
    prefixes, counts = precision_utils.get_log_prefixes(log, activity_key="concept:name")
    keys = list(prefixes)
    sum_enabled = sum_escaping = unfit = 0

    @lru_cache(maxsize=50000)
    def enabled(marking_items):
        marking = Marking(dict(marking_items))
        return frozenset(t.label for t in get_visible_transitions_eventually_enabled_by_marking(net, marking)
                         if t.label is not None)

    for offset in range(0, len(keys), batch_size):
        batch_keys = keys[offset:offset + batch_size]
        fake_log = precision_utils.form_fake_log(batch_keys, activity_key="concept:name")
        aligned = pm_precision.align_fake_log_stop_marking(fake_log, net, initial, final, parameters=dict(parameters))
        markings = pm_precision.transform_markings_from_sync_to_original_net(aligned, net, parameters=dict(parameters))
        if len(markings) != len(batch_keys):
            raise ValueError("PM4Py returned an incomplete prefix batch.")
        for key, reached in zip(batch_keys, markings):
            if reached is None:
                unfit += counts[key]
                continue
            labels = set()
            for marking in reached:
                labels.update(enabled(frozenset((p, n) for p, n in marking.items() if n)))
            sum_enabled += len(labels) * counts[key]
            sum_escaping += len(labels.difference(prefixes[key])) * counts[key]
        del fake_log, aligned, markings
        gc.collect()
        if progress:
            print(f"Aligned prefixes: {min(offset + batch_size, len(keys))}/{len(keys)}", flush=True)
    # PM4Py includes the empty prefix, weighted by the ORIGINAL case count.
    start_activities = {trace[0]["concept:name"] for trace in log if trace}
    initial_labels = enabled(frozenset((p, n) for p, n in initial.items() if n))
    sum_enabled += len(log) * len(initial_labels)
    sum_escaping += len(log) * len(initial_labels.difference(start_activities))
    value = 1 - sum_escaping / sum_enabled if sum_enabled else 1.0
    return {"precision": value, "prefixes": len(keys), "weighted_unfit_prefixes": unfit,
            "weighted_enabled": sum_enabled, "weighted_escaping": sum_escaping,
            "prefix_batch_size": batch_size, "method": "PM4Py Align-ET, global prefixes, batched alignment jobs"}
