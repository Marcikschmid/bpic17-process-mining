"""PM4Py Align-ET on a COMPLETE finite marking graph, without product nets.

PM4Py's prefix search permits only synchronous moves (cost 0) and invisible
model moves (cost 1), then collects all minimum-cost stop markings. The trace
part is a linear chain, so dynamic programming plus weighted epsilon closure
computes exactly the same minimum-cost model markings. No log/model visible
moves are introduced; all original global prefix weights and empty-prefix
correction are preserved. Costs are normalized only by a shared offset.
"""
import heapq
from functools import lru_cache
from pm4py.algo.evaluation.precision import utils
from pm4py.util import constants
from src.replay_coverage import ExactReplay


def finite_alignment_precision(log, net, initial, final):
    machine = ExactReplay(net, initial, final)
    @lru_cache(maxsize=None)
    def advance(distribution, label):
        distances = dict(distribution)
        heap = [(cost,state) for state,cost in distribution]
        heapq.heapify(heap)
        while heap:
            cost,state = heapq.heappop(heap)
            if distances[state] != cost: continue
            for target in machine.edges[state].get(None, ()):
                if cost+1 < distances.get(target,float('inf')):
                    distances[target]=cost+1
                    heapq.heappush(heap,(cost+1,target))
        targets={}
        for state,cost in distances.items():
            for target in machine.edges[state].get(label, ()):
                targets[target]=min(targets.get(target,float('inf')),cost)
        if not targets:return ()
        minimum=min(targets.values())
        return tuple(sorted((state,cost-minimum) for state,cost in targets.items()))

    @lru_cache(maxsize=None)
    def reached(prefix):
        if not prefix:return ((0,0),)
        return advance(reached(prefix[:-1]),prefix[-1])

    @lru_cache(maxsize=None)
    def enabled(states):
        closure=machine.closure(frozenset(states))
        return frozenset(label for state in closure for label in machine.edges[state] if label is not None)

    prefixes, counts=utils.get_log_prefixes(log,activity_key='concept:name')
    enabled_sum=escaping_sum=excluded=0
    # Export per-prefix enabled sets for independent reference spot checks.
    labels_by_prefix={}
    for key,observed in prefixes.items():
        distribution=reached(tuple(key.split(constants.DEFAULT_VARIANT_SEP)))
        if not distribution:
            excluded+=counts[key];labels_by_prefix[key]=None
            continue
        labels=enabled(tuple(state for state,cost in distribution if cost==0))
        labels_by_prefix[key]=sorted(labels)
        enabled_sum+=counts[key]*len(labels)
        escaping_sum+=counts[key]*len(labels-observed)
    initial_labels=enabled((0,))
    starts={trace[0]['concept:name'] for trace in log if trace}
    enabled_sum+=len(log)*len(initial_labels)
    escaping_sum+=len(log)*len(initial_labels-starts)
    result={'precision':1-escaping_sum/enabled_sum if enabled_sum else 1.0,
        'prefixes':len(prefixes),'weighted_unfit_prefixes':excluded,
        'weighted_enabled':enabled_sum,'weighted_escaping':escaping_sum,
        'method':'PM4Py Align-ET formula; exact weighted finite-state prefix solver',
        'complete_model_states':machine.state_count,'silent_move_cost':1,'sync_move_cost':0}
    return result,labels_by_prefix
