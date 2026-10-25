"""Recover the native Genetic net losslessly from its pre-import Graphviz graph.

One-off correction for the native converter's repeated empty transition IDs.
The graph contains distinct object IDs, all arcs, visible labels and markings.
Original broken PNML/evaluation are retained ONLY under audit/, not used as scores.
"""
import sys,json,hashlib,re,shutil,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.runtime import configure_runtime
configure_runtime()
OUT=ROOT/'results/genetic/seed_20261025'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
def main():
 import pm4py
 from pm4py.objects.petri_net.obj import PetriNet,Marking
 from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to
 from pm4py.objects.log.obj import EventLog,Trace,Event
 from pm4py.algo.conformance.tokenreplay import algorithm as tbr
 from pm4py.algo.evaluation.replay_fitness.variants import token_replay as fitness
 from pm4py.algo.evaluation.generalization.variants.token_based import get_generalization
 from pm4py.algo.evaluation.precision.variants import etconformance_token
 from pm4py.algo.evaluation.simplicity.variants import arc_degree
 from scripts.discover_models import export_model
 from src.simplicity import model_size,extended_cardoso,reachability_complexity
 from src.replay_coverage import ExactReplay
 audit=OUT/'audit';audit.mkdir(exist_ok=True)
 if not (audit/'original_graph.gv').exists():
  shutil.copyfile(OUT/'figures/genetic_miner.gv',audit/'original_graph.gv')
  shutil.copyfile(OUT/'models/genetic_miner.pnml',audit/'INVALID_duplicate_ids.pnml')
  shutil.copyfile(OUT/'manifest.json',audit/'INVALID_export_evaluation.json')
 record=json.loads((audit/'INVALID_export_evaluation.json').read_text())
 original=audit/'original_graph.gv'
 assert sha(original)==record['model']['artifacts']['results/genetic/seed_20261025/figures/genetic_miner.gv']['sha256']
 net=PetriNet('native_genetic_recovered');im=Marking();fm=Marking();nodes={};edges=[]
 for line in original.read_text().splitlines():
  edge=re.match(r'^\s*(\d+) -> (\d+) \[label="" ',line)
  if edge:edges.append(edge.groups());continue
  node=re.match(r'^\s*(\d+) \[label=("(?:\\.|[^"\\])*"|<[^>]*>|[^\s\]]+) (.*)\]$',line)
  if not node:continue
  key,label,attrs=node.groups();assert key not in nodes
  if 'shape=circle' in attrs or 'shape=doublecircle' in attrs:
   item=PetriNet.Place('p_'+key);net.places.add(item)
   if '&#9679;' in label:im[item]=1
   if '&#9632;' in label:fm[item]=1
  else:
   label=json.loads(label) if label.startswith('"') else label
   item=PetriNet.Transition('t_'+key,label=label or None);net.transitions.add(item)
  nodes[key]=item
 assert len(net.places)==37 and len(net.transitions)==39 and len(edges)==87
 assert len(set(edges))==87 and len(im)==len(fm)==1
 for a,b in edges:
  assert isinstance(nodes[a],PetriNet.Place)!=isinstance(nodes[b],PetriNet.Place)
  add_arc_from_to(nodes[a],nodes[b],net)
 record['export_correction']={'cause':'Native Genetic converter assigned the same empty name to 15 silent transitions. PNML repeated IDs merged arc endpoints on import. Previous name-only signature failed to detect it.',
  'source_graph':'audit/original_graph.gv','source_graph_sha256':sha(original),
  'method':'Lossless reconstruction from unique Graphviz object IDs, all 87 unit-weight arcs, 24 labels and initial/final marking symbols. Only identifiers changed.',
  'script_sha256':sha(Path(__file__)),'corrected_exporter_sha256':sha(ROOT/'scripts/discover_models.py'),
  'invalid_evaluation':'audit/INVALID_export_evaluation.json','invalid_scores_excluded':True}
 record['status']='reevaluating_corrected_export';write(OUT/'manifest.json',record)
 record['model']=export_model('genetic_miner',(net,im,fm),OUT)
 net,im,fm=pm4py.read_pnml(str(OUT/'models/genetic_miner.pnml'))
 cache=ROOT/'tmp/evaluation/projected_sequences.json';assert sha(cache)==record['input']['identity']['input_cache_sha256']
 data=json.loads(cache.read_text());sequences=[t['activities'] for t in data['traces']]
 log=EventLog([Trace([Event({'concept:name':a}) for a in t['activities']],attributes={'concept:name':t['case_id']}) for t in data['traces']])
 params={'pm4py:param:activity_key':'concept:name','show_progress_bar':False,'multiprocessing':False,'cleaning_token_flood':False,'consider_remaining_in_fitness':True}
 print('Full-log corrected token replay',flush=True)
 replay=tbr.apply(log,net,im,fm,parameters=params)
 metrics={'cases':len(log),'events':sum(map(len,log)),'token_fitness':fitness.evaluate(replay),
  'token_fitting_cases':sum(r['trace_is_fit'] for r in replay),'generalization':get_generalization(net,replay),
  'arc_degree_simplicity':arc_degree.apply(net),'size':model_size(net),'extended_cardoso':extended_cardoso(net)}
 common_objective=.4*metrics['token_fitness']['average_trace_fitness']+.6*metrics['token_fitness']['perc_fit_traces']/100
 record['export_correction']['objective_after_reload']=common_objective
 record['export_correction']['objective_difference']=common_objective-record['native_best_objective']
 print('OBJECTIVE CROSSCHECK '+json.dumps(record['export_correction']),flush=True)
 record['metrics']=metrics;write(OUT/'manifest.json',record)
 print('Full-log corrected precision',flush=True)
 metrics['token_precision']=etconformance_token.apply(log,net,im,fm,parameters=params)
 print('Corrected state-space verification',flush=True)
 metrics['reachability']=reachability_complexity(net,im,fm,max_states=30000,timeout=90)
 if metrics['reachability']['status']=='ok':metrics['exact_coverage']=ExactReplay(net,im,fm).evaluate(sequences)[0]
 else:metrics['exact_coverage']={'status':'not_enumerated','reason':metrics['reachability']['status']}
 if metrics['reachability']['status']=='unbounded':
  from scripts.verify_evaluation import verify_unboundedness
  metrics['unboundedness_crosscheck']=verify_unboundedness(net,im,json.loads(json.dumps(metrics['reachability']['witness'])))
 record['status']='ok';write(OUT/'manifest.json',record)
 artifacts={str(p.relative_to(OUT)).replace('\\','/'):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('manifest.json','artifacts.json')}
 write(OUT/'artifacts.json',{'source_sha256':sha(OUT/'manifest.json'),'artifacts':artifacts})
 print('DONE '+json.dumps(metrics),flush=True)
if __name__=='__main__':main()
