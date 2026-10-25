"""Select, validate, assess and export the refined BPMN without changing baselines."""
import argparse
import csv
import json
import shutil
from collections import Counter
from importlib.metadata import version
from scripts.refine_model import ROOT, OUT, CACHE, sha, write
import pm4py
from pm4py.objects.log.obj import EventLog, Event, Trace
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.algo.evaluation.replay_fitness.variants import token_replay as token_fitness
from pm4py.algo.evaluation.generalization.variants.token_based import get_generalization
from pm4py.algo.evaluation.precision.variants import etconformance_token
from pm4py.algo.evaluation.simplicity.variants import arc_degree
from pm4py.visualization.bpmn import visualizer
from pm4py.objects.bpmn.obj import BPMN
from src.replay_coverage import ExactReplay
from src.quality import alignment_precision_batched
from src.simplicity import model_size, extended_cardoso, reachability_complexity

PARAMS={'pm4py:param:activity_key':'concept:name','show_progress_bar':False,
        'multiprocessing':False,'cleaning_token_flood':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true',help='Export and verify model; defer expensive quality jobs.')
    args=parser.parse_args()
    data=json.loads(CACHE.read_text(encoding='utf-8'))
    candidates={}
    for filename in ('candidates.json','focused_candidates.json'):
        manifest=json.loads((OUT/filename).read_text(encoding='utf-8'))
        assert manifest['input_cache_sha256']==sha(CACHE)
        candidates.update(manifest['candidates'])
    eligible=[(key,v) for key,v in candidates.items() if v['coverage']['sound'] and 78<=v['coverage']['fitting_percentage']<=82]
    if not eligible:raise ValueError('No sound candidate in the declared 78-82% exact replay band')
    selected,record=max(eligible,key=lambda item:(item[1]['exact_prefix_precision']['value'],-item[1]['size']['nodes']))
    folder=OUT/'candidates'/selected
    assert sha(folder/'model.pnml')==record['pnml_sha256']
    shutil.copyfile(folder/'model.pnml',OUT/'final_model.pnml')
    shutil.copyfile(folder/'tree.ptml',OUT/'final_model.ptml')
    net,initial,final=pm4py.read_pnml(str(OUT/'final_model.pnml'))
    machine=ExactReplay(net,initial,final)
    sequences=[t['activities'] for t in data['traces']]
    coverage,fits=machine.evaluate(sequences)
    assert coverage==record['coverage'] and coverage['sound']
    tree=pm4py.read_ptml(str(OUT/'final_model.ptml'))
    bpmn=pm4py.convert_to_bpmn(tree)
    pm4py.write_bpmn(bpmn,str(OUT/'final_model.bpmn'),auto_layout=True)
    imported=pm4py.read_bpmn(str(OUT/'final_model.bpmn'))
    roundtrip=pm4py.convert_to_petri_net(imported)
    bpmn_machine=ExactReplay(*roundtrip)
    equivalence=machine.language_equivalent(bpmn_machine)
    if not equivalence['equivalent']:raise ValueError(f'BPMN changed the model language: {equivalence}')
    assert bpmn_machine.evaluate(sequences)[1]==fits
    pm4py.write_pnml(*roundtrip,str(OUT/'bpmn_roundtrip.pnml'))
    print('BPMN roundtrip: complete language equivalence verified',flush=True)
    path=OUT/'final_metrics.json'
    result=json.loads(path.read_text()) if path.exists() else {}
    if result.get('model_sha256')!=sha(OUT/'final_model.pnml') or result.get('input_cache_sha256')!=sha(CACHE): result={}
    result.update(selected=selected,model_sha256=sha(OUT/'final_model.pnml'),
        input_cache_sha256=sha(CACHE),raw_sha256=data['raw_sha256'],coverage=coverage,
        selected_candidate=record,selection_rule='78-82% exact replay; highest exact prefix precision, tie fewer nodes',
        pm4py=version('pm4py'),bpmn_language_equivalence=equivalence,
        bpmn_sha256=sha(OUT/'final_model.bpmn'),metrics=result.get('metrics',{}),
        implementation_sha256={p:sha(ROOT/p) for p in ('src/replay_coverage.py','src/quality.py','src/finite_precision.py','src/simplicity.py','scripts/export_refined_model.py')})
    write(path,result)
    if args.prepare_only:
        print('Model prepared; run accelerate_refinement, then export without --prepare-only',flush=True)
        return
    log=EventLog([Trace([Event({'concept:name':a}) for a in t['activities']],attributes={'concept:name':t['case_id']}) for t in data['traces']])
    metrics=result['metrics']
    if 'token_fitness' not in metrics:
        print('START token fitness and generalization',flush=True)
        replay=token_replay.apply(log,net,initial,final,parameters={**PARAMS,'consider_remaining_in_fitness':True})
        assert len(replay)==len(log) and all(r is not None for r in replay)
        metrics.update(token_fitness=token_fitness.evaluate(replay),generalization=get_generalization(net,replay),
                       token_fitting_cases=sum(r['trace_is_fit'] for r in replay))
        write(path,result)
    if 'token_precision' not in metrics:
        print('START token precision',flush=True)
        metrics['token_precision']=etconformance_token.apply(log,net,initial,final,parameters=dict(PARAMS))
        write(path,result)
    if 'alignment_precision' not in metrics:
        fast_path=OUT/'fast_alignment_precision.json'
        if fast_path.exists():
            fast=json.loads(fast_path.read_text())
            audit=fast['reference_crosscheck']
            assert audit['status']=='ok' and audit['model_sha256']==sha(OUT/'final_model.pnml')
            assert audit['input_cache_sha256']==sha(CACHE)
            assert audit['implementation_sha256']==sha(ROOT/'src/finite_precision.py')
            metrics['alignment_precision']=fast
            print('REUSE complete finite-state Align-ET; independent PM4Py prefix crosschecks passed',flush=True)
        else:
            print('START full PM4Py alignment precision',flush=True)
            metrics['alignment_precision']=alignment_precision_batched(log,net,initial,final,parameters=PARAMS,progress=True)
        write(path,result)
    metrics.update(simplicity_arc_degree=arc_degree.apply(net,{'k':2}),size_own=model_size(net),
                   cardoso_own=extended_cardoso(net),reachability=reachability_complexity(net,initial,final))
    assert metrics['reachability']['status']=='ok' and metrics['reachability']['sound']
    result['bpmn_structure']={'tasks':sum(isinstance(n,BPMN.Task) for n in imported.get_nodes()),
        'exclusive_gateways':sum(isinstance(n,BPMN.ExclusiveGateway) for n in imported.get_nodes()),
        'parallel_gateways':sum(isinstance(n,BPMN.ParallelGateway) for n in imported.get_nodes())}
    represented={t.label for t in net.transitions if t.label is not None}
    result['omitted_activity_labels']=sorted(set(data['projection']['discovery_activity_counts'])-represented)
    groups={}
    for trace,fit in zip(data['traces'],fits):
        outcomes=[a for a in ('A_Pending','A_Cancelled','A_Denied') if a in trace['activities']]
        group='+'.join(outcomes) or 'No terminal application state'
        g=groups.setdefault(group,{'cases':0,'fitting_cases':0});g['cases']+=1;g['fitting_cases']+=fit
    result['coverage_by_outcome']={k:{**v,'fitting_percentage':100*v['fitting_cases']/v['cases']} for k,v in groups.items()}
    result['status']='ok'
    write(path,result)
    with (OUT/'case_replay.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(['case_id','exact_replay'])
        writer.writerows((t['case_id'],int(fit)) for t,fit in zip(data['traces'],fits))
    graph=visualizer.apply(imported,parameters={'rankdir':'TB','font_size':'13','bgcolor':'white'})
    graph.attr('graph',nodesep='.15',ranksep='.25',pad='.15')
    for node in imported.get_nodes():
        if isinstance(node,BPMN.Task):graph.node(str(id(node)),style='rounded',margin='.07,.04')
    for extension in ('pdf','svg','png'):
        (OUT/f'final_bpmn.{extension}').write_bytes(graph.pipe(format=extension))
    template=(ROOT/'src/bpmn_viewer.html').read_text(encoding='utf-8')
    (OUT/'index.html').write_text(template.replace('MODEL_DATA',json.dumps(result).replace('</','<\\/')),encoding='utf-8',newline='\n')
    write(OUT/'delivery_manifest.json',{'source_sha256':sha(path),'artifacts':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name in (
        'final_model.pnml','final_model.ptml','final_model.bpmn','bpmn_roundtrip.pnml','case_replay.csv','final_bpmn.pdf','final_bpmn.svg','final_bpmn.png','index.html')}})
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
