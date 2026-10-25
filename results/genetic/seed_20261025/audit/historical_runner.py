"""Run an explicitly budgeted, full-log PM4Py Genetic Miner experiment.

No baseline or existing report files are overwritten. Python hash/random/numpy
seeds are fixed; the native objective is logged, not replaced by our recommendation.
"""
import argparse,csv,gzip,hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from time import perf_counter
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
os.environ['PM4PY_DEFAULT_IS_THREADING_MANAGEMENT_ENABLED']='False'
os.environ['PM4PY_SHOW_PROGRESS_BAR']='False';os.environ['TQDM_DISABLE']='1'
from src.genetic_miner import GENETIC_PARAMETERS,DEFAULT_SEED,discover_genetic
CACHE=ROOT/'tmp/evaluation/projected_sequences.json'
RAW=ROOT/'data/raw/BPI Challenge 2017.xes.gz'
INPUT=ROOT/'tmp/genetic/input.csv';META=INPUT.with_suffix('.json')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8',newline='\n');temp.replace(p)

def prepare_input():
    import pandas as pd
    data=json.loads(CACHE.read_text(encoding='utf-8'))
    if sha(RAW)!=data['raw_sha256']:raise ValueError('Raw data hash changed')
    identity={'raw_sha256':data['raw_sha256'],'input_cache_sha256':sha(CACHE)}
    if META.exists() and INPUT.exists():
        saved=json.loads(META.read_text())
        if saved.get('identity')==identity and saved.get('csv_sha256')==sha(INPUT):
            frame=pd.read_csv(INPUT);frame['time:timestamp']=pd.to_datetime(frame['time:timestamp'],utc=True,format='ISO8601')
            return frame,saved
    rows=[];index=0
    with gzip.open(RAW,'rb') as stream:
        for _,element in ET.iterparse(stream,events=('end',)):
            if element.tag.split('}')[-1]!='trace':continue
            case=next(e.attrib['value'] for e in element if e.attrib.get('key')=='concept:name')
            sequence=[]
            for event in element:
                if event.tag.split('}')[-1]!='event':continue
                attrs={e.attrib.get('key'):e.attrib.get('value') for e in event}
                if attrs.get('lifecycle:transition')!='complete':continue
                label=attrs['concept:name'];sequence.append(label)
                rows.append((case,label,attrs['time:timestamp']))
            expected=data['traces'][index]
            if case!=expected['case_id'] or sequence!=expected['activities']:raise ValueError('Completion projection differs from baselines')
            index+=1;element.clear()
    if index!=len(data['traces']):raise ValueError('Missing cases')
    frame=pd.DataFrame(rows,columns=['case:concept:name','concept:name','time:timestamp'])
    frame['time:timestamp']=pd.to_datetime(frame['time:timestamp'],utc=True,format='ISO8601')
    expected={t['case_id']:tuple(t['activities']) for t in data['traces']}
    native_order=frame.sort_values('time:timestamp',ascending=True).groupby('case:concept:name',sort=False)['concept:name'].agg(tuple)
    mismatch=[case for case,sequence in native_order.items() if sequence!=expected[case]]
    if mismatch:raise ValueError(f'Native timestamp sorting changes event order for {len(mismatch)} cases: {mismatch[:5]}')
    INPUT.parent.mkdir(parents=True,exist_ok=True);frame.to_csv(INPUT,index=False)
    result={'identity':identity,'cases':index,'events':len(frame),'activities':frame['concept:name'].nunique(),
        'native_timestamp_sort_preserves_all_case_sequences':True,'csv_sha256':sha(INPUT)}
    write(META,result);return frame,result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=DEFAULT_SEED)
    parser.add_argument('--population-size',type=int,default=GENETIC_PARAMETERS['population_size'])
    parser.add_argument('--generations',type=int,default=GENETIC_PARAMETERS['generations'])
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    if os.environ.get('PYTHONHASHSEED')!=str(args.seed):
        env=dict(os.environ,PYTHONHASHSEED=str(args.seed))
        raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],env=env,cwd=ROOT))
    from importlib.metadata import version
    import pm4py
    from scripts.discover_models import export_model
    from src.simplicity import model_size,extended_cardoso,reachability_complexity
    from pm4py.objects.log.obj import EventLog,Trace,Event
    from pm4py.algo.conformance.tokenreplay import algorithm as tbr
    from pm4py.algo.evaluation.replay_fitness.variants import token_replay as fitness
    from pm4py.algo.evaluation.generalization.variants.token_based import get_generalization
    from pm4py.algo.evaluation.precision.variants import etconformance_token
    from pm4py.algo.evaluation.simplicity.variants import arc_degree
    output=ROOT/f'results/genetic/seed_{args.seed}';output.mkdir(parents=True,exist_ok=True)
    record={'status':'running','seed':args.seed,'python_hash_seed':os.environ['PYTHONHASHSEED'],
        'started_utc':datetime.now(timezone.utc).isoformat(),'pm4py':version('pm4py'),
        'parameters':{**GENETIC_PARAMETERS,'population_size':args.population_size,'generations':args.generations},
        'method':'Unmodified PM4Py Genetic Miner CLASSIC; exploratory fixed evaluation budget',
        'native_objective':'0.4 * average_trace_fitness + 0.6 * percentage_of_fitting_traces / 100',
        'implementation_sha256':{p:sha(ROOT/p) for p in ('src/genetic_miner.py','scripts/discover_genetic.py')}}
    path=output/'manifest.json';write(path,record);started=perf_counter()
    try:
        print('PREPARE same full completion projection',flush=True)
        frame,input_record=prepare_input();record['input']=input_record;write(path,record)
        print(json.dumps(input_record),flush=True)
        if args.prepare_only:record['status']='input_verified';write(path,record);return
        print('START native Genetic Miner '+json.dumps(record['parameters']),flush=True)
        with (output/'evolution.csv').open('w',newline='',encoding='utf-8') as stream:
            model=discover_genetic(frame,seed=args.seed,log_csv=stream,population_size=args.population_size,generations=args.generations)
        record['discovery_seconds']=round(perf_counter()-started,3)
        print('EXPORT native result',flush=True)
        record['model']=export_model('genetic_miner',model,output)
        with (output/'evolution.csv').open(newline='',encoding='utf-8') as stream:history=list(csv.DictReader(stream))
        record['evaluated_generations']=len(history)
        record['native_best_objective']=float(history[-1]['fitness0'])
        write(path,record)
        net,im,fm=pm4py.read_pnml(str(output/'models/genetic_miner.pnml'))
        data=json.loads(CACHE.read_text(encoding='utf-8'))
        log=EventLog([Trace([Event({'concept:name':a}) for a in t['activities']],attributes={'concept:name':t['case_id']}) for t in data['traces']])
        params={'pm4py:param:activity_key':'concept:name','show_progress_bar':False,'multiprocessing':False,'cleaning_token_flood':False,'consider_remaining_in_fitness':True}
        print('QUALITY full-log token replay',flush=True)
        replay=tbr.apply(log,net,im,fm,parameters=params)
        metrics={'cases':len(log),'events':sum(len(t) for t in log),'token_fitness':fitness.evaluate(replay),
            'token_fitting_cases':sum(r['trace_is_fit'] for r in replay),'generalization':get_generalization(net,replay),
            'arc_degree_simplicity':arc_degree.apply(net),'size':model_size(net),'extended_cardoso':extended_cardoso(net)}
        record['metrics']=metrics;write(path,record)
        print('QUALITY full-log token precision',flush=True)
        metrics['token_precision']=etconformance_token.apply(log,net,im,fm,parameters=params)
        print('STRUCTURE boundedness and exact replay eligibility',flush=True)
        metrics['reachability']=reachability_complexity(net,im,fm,max_states=30000,timeout=90)
        if metrics['reachability']['status']=='ok':
            from src.replay_coverage import ExactReplay
            metrics['exact_coverage']=ExactReplay(net,im,fm).evaluate([t['activities'] for t in data['traces']])[0]
        else:metrics['exact_coverage']={'status':'not_enumerated','reason':metrics['reachability']['status']}
        if metrics['reachability']['status']=='unbounded':
            from scripts.verify_evaluation import verify_unboundedness
            witness=json.loads(json.dumps(metrics['reachability']['witness']))
            metrics['unboundedness_crosscheck']=verify_unboundedness(net,im,witness)
        record['status']='ok';record['total_seconds']=round(perf_counter()-started,3);write(path,record)
        artifacts={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name not in ('manifest.json','artifacts.json')}
        write(output/'artifacts.json',{'source_sha256':sha(path),'artifacts':artifacts})
        print('DONE '+json.dumps({'seed':args.seed,'generations':len(history),'native_objective':record['native_best_objective'],**{k:v for k,v in metrics.items() if k not in ('reachability',)}}),flush=True)
    except Exception as error:
        record.update(status='failed',error=f'{type(error).__name__}: {error}',seconds=round(perf_counter()-started,3));write(path,record)
        traceback.print_exc();raise

if __name__=='__main__':main()
