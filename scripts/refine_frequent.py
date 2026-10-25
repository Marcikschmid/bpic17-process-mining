"""Second refinement family: discover on frequent variants, evaluate ALL cases.

Training variants are ranked solely by observed frequency (stable tie-break).
The training subset and its actual coverage are explicit; evaluation always
uses the same 31,509 cases and 475,306 complete events as both baselines.
"""
import argparse
import json
from collections import Counter
from time import perf_counter
from scripts.refine_model import ROOT, CACHE, OUT, sha, write
import pm4py
from pm4py.objects.log.obj import EventLog, Event, Trace
from src.replay_coverage import ExactReplay
from src.simplicity import model_size, extended_cardoso


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-coverage', type=float, nargs='+', default=[.65,.70,.75,.80])
    parser.add_argument('--thresholds', type=float, nargs='+', default=[0,.05,.1])
    args = parser.parse_args()
    data = json.loads(CACHE.read_text(encoding='utf-8'))
    sequences = [t['activities'] for t in data['traces']]
    frequencies = Counter(tuple(t) for t in sequences)
    ranked = sorted(frequencies, key=lambda t: (-frequencies[t], t))
    log = EventLog([Trace([Event({'concept:name':a}) for a in t['activities']],
                         attributes={'concept:name':t['case_id']}) for t in data['traces']])
    path = OUT / 'focused_candidates.json'
    result = json.loads(path.read_text()) if path.exists() else {
        'input_cache_sha256':sha(CACHE), 'raw_sha256':data['raw_sha256'],
        'evaluation_cases':len(log), 'training_rule':'Most frequent variants; stable lexicographic tie break; no outcome-based selection',
        'candidates':{}}
    assert result['input_cache_sha256'] == sha(CACHE)
    for coverage in args.training_coverage:
        selected, count = set(), 0
        for sequence in ranked:
            selected.add(sequence)
            count += frequencies[sequence]
            if count >= coverage*len(log): break
        training = EventLog([t for t in log if tuple(e['concept:name'] for e in t) in selected])
        for noise in args.thresholds:
            key = f'frequent_{coverage:.2f}_imf_{noise:.2f}'
            if key in result['candidates']: continue
            started = perf_counter()
            print('START',key,flush=True)
            tree = pm4py.discover_process_tree_inductive(training, noise_threshold=noise, multi_processing=False)
            net, initial, final = pm4py.convert_to_petri_net(tree)
            replay = ExactReplay(net, initial, final)
            evaluation, _ = replay.evaluate(sequences)
            precision = replay.prefix_precision(sequences)
            folder = OUT/'candidates'/key
            folder.mkdir(parents=True,exist_ok=True)
            pm4py.write_pnml(net,initial,final,str(folder/'model.pnml'))
            pm4py.write_ptml(tree,str(folder/'tree.ptml'))
            record = {'noise_threshold':noise,'training_cases':len(training),
                'training_variants':len(selected),'training_case_percentage':100*len(training)/len(log),
                'coverage':evaluation,'exact_prefix_precision':precision,
                'size':model_size(net),'cardoso':extended_cardoso(net),'tree':str(tree),
                'pnml_sha256':sha(folder/'model.pnml'),'seconds':round(perf_counter()-started,3)}
            result['candidates'][key] = record
            write(path,result)
            print(key, evaluation['fitting_percentage'],precision['value'],flush=True)


if __name__ == '__main__': main()
