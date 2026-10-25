"""Independently audit the persisted Genetic trial and its corrected export."""
import sys,json,re,hashlib,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import pm4py
 from scripts.verify_evaluation import verify_unboundedness
 folder=ROOT/'results/genetic/seed_20261025'
 record=json.loads((folder/'manifest.json').read_text());assert record['status']=='ok'
 checks=json.loads((folder/'artifacts.json').read_text())
 assert checks['source_sha256']==sha(folder/'manifest.json')
 for name,digest in checks['artifacts'].items():assert sha(folder/name)==digest,name
 cache=ROOT/'tmp/evaluation/projected_sequences.json'
 assert sha(cache)==record['input']['identity']['input_cache_sha256']
 assert record['input']['cases']==record['metrics']['cases']==31509
 assert record['input']['events']==record['metrics']['events']==475306
 with (folder/'evolution.csv').open(newline='') as stream:history=list(csv.DictReader(stream))
 assert len(history)==record['evaluated_generations']==2
 assert float(history[-1]['fitness0'])==record['native_best_objective']
 net,im,fm=pm4py.read_pnml(str(folder/'models/genetic_miner.pnml'))
 nodes=[*net.places,*net.transitions];assert len({n.name for n in nodes})==len(nodes)==76
 assert all(a.weight==1 for a in net.arcs)
 original=(folder/'audit/original_graph.gv').read_text()
 edges=set(re.findall(r'^\s*(\d+) -> (\d+) \[label="" ',original,re.M))
 restored={(a.source.name[2:],a.target.name[2:]) for a in net.arcs}
 assert restored==edges and len(edges)==87
 labels={};initial=[];final=[];places=set()
 for key,label,attrs in re.findall(r'^\s*(\d+) \[label=("(?:\\.|[^"\\])*"|<[^>]*>|[^\s\]]+) (.*)\]$',original,re.M):
  if 'shape=circle' in attrs or 'shape=doublecircle' in attrs:
   places.add(key)
   if '&#9679;' in label:initial.append(key)
   if '&#9632;' in label:final.append(key)
  else:
   label=json.loads(label) if label.startswith('"') else label
   labels[key]=label or None
 assert {t.name[2:]:t.label for t in net.transitions}==labels
 assert {p.name[2:] for p in net.places}==places
 assert {p.name[2:] for p in im}==set(initial) and sum(im.values())==1
 assert {p.name[2:] for p in fm}==set(final) and sum(fm.values())==1
 metrics=record['metrics'];fitness=metrics['token_fitness']
 objective=.4*fitness['average_trace_fitness']+.6*fitness['perc_fit_traces']/100
 assert objective==record['native_best_objective']
 assert metrics['reachability']['status']=='unbounded'
 witness=json.loads(json.dumps(metrics['reachability']['witness']))
 proof=verify_unboundedness(net,im,witness)
 result={'status':'ok','cases':31509,'events':475306,'artifact_hashes_checked':len(checks['artifacts']),
  'source_graph_to_corrected_pnml':{'nodes':76,'arcs':87,'labels_and_markings_equal':True},
  'native_objective_reproduced':objective,'unboundedness':proof,
  'exact_case_coverage':'not enumerated; no exact 0% claim',
  'manifest_sha256':sha(folder/'manifest.json'),'verifier_sha256':sha(Path(__file__))}
 (ROOT/'docs/genetic_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
