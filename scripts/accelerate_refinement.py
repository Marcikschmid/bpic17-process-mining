"""Compute full finite-state Align-ET; cross-check original PM4Py prefix search."""
import json
import random
from scripts.refine_model import OUT,CACHE,ROOT,sha,write
import pm4py
from pm4py.objects.log.obj import EventLog,Trace,Event
from pm4py.algo.evaluation.precision import utils
from pm4py.algo.evaluation.precision.variants import align_etconformance as reference
from pm4py.objects.petri_net.utils.align_utils import get_visible_transitions_eventually_enabled_by_marking
from src.finite_precision import finite_alignment_precision


def main():
    data=json.loads(CACHE.read_text())
    log=EventLog([Trace([Event({'concept:name':a}) for a in t['activities']]) for t in data['traces']])
    net,im,fm=pm4py.read_pnml(str(OUT/'final_model.pnml'))
    result,labels=finite_alignment_precision(log,net,im,fm)
    keys=list(labels)
    rng=random.Random(20261018)
    selected=list(dict.fromkeys(keys[:32]+rng.sample(keys,128)+sorted(keys,key=len,reverse=True)[:32]))
    for start in range(0,len(selected),32):
        batch=selected[start:start+32]
        fake=utils.form_fake_log(batch,activity_key='concept:name')
        aligned=reference.align_fake_log_stop_marking(fake,net,im,fm,parameters={'show_progress_bar':False,'multiprocessing':False})
        reached=reference.transform_markings_from_sync_to_original_net(aligned,net)
        for key,markings in zip(batch,reached):
            expected=None if markings is None else sorted({t.label for m in markings
                for t in get_visible_transitions_eventually_enabled_by_marking(net,m) if t.label is not None})
            assert labels[key]==expected,(key,labels[key],expected)
    audit={'status':'ok','model_sha256':sha(OUT/'final_model.pnml'),'input_cache_sha256':sha(CACHE),
        'all_prefixes_computed':len(keys),'pm4py_reference_prefixes_checked':len(selected),
        'reference_selection':'first 32, longest 32, 128 fixed-seed random; scores use ALL prefixes',
        'reference_seed':20261018,'implementation_sha256':sha(ROOT/'src/finite_precision.py')}
    result['reference_crosscheck']=audit
    write(OUT/'fast_alignment_precision.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
