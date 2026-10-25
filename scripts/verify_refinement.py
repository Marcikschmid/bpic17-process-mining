"""Verify refinement provenance, full case weights, BPMN semantics and PM samples."""
import csv
import json
import random
from scripts.refine_model import OUT,ROOT,CACHE,sha,write
import pm4py
import networkx as nx
from pm4py.objects.petri_net.utils import reachability_graph
from pm4py.objects.log.obj import Trace,Event
from pm4py.algo.conformance.alignments.petri_net import algorithm as alignment
from src.replay_coverage import ExactReplay


def main():
    record=json.loads((OUT/'final_metrics.json').read_text())
    assert record['status']=='ok' and record['input_cache_sha256']==sha(CACHE)
    assert record['model_sha256']==sha(OUT/'final_model.pnml')
    assert record['bpmn_sha256']==sha(OUT/'final_model.bpmn')
    data=json.loads(CACHE.read_text())
    net,im,fm=pm4py.read_pnml(str(OUT/'final_model.pnml'))
    machine=ExactReplay(net,im,fm)
    coverage,fits=machine.evaluate([t['activities'] for t in data['traces']])
    assert coverage==record['coverage'] and coverage['sound']
    assert 78<=coverage['fitting_percentage']<=82
    with (OUT/'case_replay.csv').open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==len(data['traces'])
    assert all(r['case_id']==t['case_id'] and int(r['exact_replay'])==fit for r,t,fit in zip(rows,data['traces'],fits))
    imported=pm4py.read_bpmn(str(OUT/'final_model.bpmn'))
    other=ExactReplay(*pm4py.convert_to_petri_net(imported))
    equivalent=machine.language_equivalent(other)
    assert equivalent['equivalent']
    reference=reachability_graph.construct_reachability_graph(net,im)
    graph=nx.DiGraph()
    graph.add_nodes_from(reference.states)
    graph.add_edges_from((s,e.to_state) for s in reference.states for e in s.outgoing)
    assert len(graph)==coverage['states']
    assert graph.number_of_edges()-len(graph)+nx.number_strongly_connected_components(graph)==record['metrics']['reachability']['value']
    # Actual fitting/nonfitting variants, including activities omitted by the model.
    unique={}
    for t,fit in zip(data['traces'],fits):unique.setdefault(tuple(t['activities']),fit)
    rng=random.Random(20261018)
    chosen=[]
    for fit in (True,False):
        candidates=[s for s,value in unique.items() if value==fit]
        chosen+=rng.sample(candidates,min(10,len(candidates)))
    for sequence in chosen:
        result=alignment.apply_trace(Trace([Event({'concept:name':a}) for a in sequence]),net,im,fm,
            parameters={'show_progress_bar':False},variant=alignment.Variants.VERSION_STATE_EQUATION_A_STAR)
        assert result is not None
        exactly_fit=all(a==b or (a=='>>' and b is None) for a,b in result['alignment'])
        assert exactly_fit==unique[sequence],(sequence,result['alignment'])
    for filename in ('delivery_manifest.json','presentation_manifest.json'):
        manifest=json.loads((OUT/filename).read_text())
        for name,digest in manifest['artifacts'].items():assert sha(OUT/name)==digest,name
    proof=record['metrics']['alignment_precision']['reference_crosscheck']
    assert proof['status']=='ok' and proof['model_sha256']==record['model_sha256']
    assert proof['input_cache_sha256']==sha(CACHE)
    audit={'status':'ok','all_cases_replayed':len(fits),'exact_fitting_cases':sum(fits),
        'bpmn_full_language_equivalence':equivalent,'pm4py_marking_graph_states':len(graph),
        'pm4py_optimal_alignment_variants_checked':len(chosen),
        'pm4py_prefix_reference_checks':proof['pm4py_reference_prefixes_checked'],
        'all_artifact_hashes_verified':True,'metrics_sha256':sha(OUT/'final_metrics.json'),
        'verifier_sha256':sha(ROOT/'scripts/verify_refinement.py')}
    write(OUT/'verification.json',audit)
    print(json.dumps(audit,indent=2),flush=True)


if __name__=='__main__':main()
