"""Discover the classic Alpha Miner net on the full completion projection and export it.

Input: tmp/evaluation/projected_sequences.json, the completion projection used by
the other miners (31,509 cases, completion events in original XES order). Classic
Alpha reads only the directly-follows order and start/end activities, so the
EventLog holds activity labels only. Alpha has no tuning parameters. PM4Py's
pair-merging loop and place names follow set iteration order, hence a fixed
PYTHONHASHSEED. A textbook enumeration of the maximal pairs Y_L cross-checks the
PM4Py places; the WF-net property is also checked on directed paths.
--audit (after scripts/assess_model.py) adds exact dead-transition certificates
(src.validation), a final-marking unreachability certificate and deterministic
whole-case replay (src.net_certificates); certificates are sufficient tests only.
"""
import argparse,hashlib,json,os,platform,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
HASH_SEED='20261029'
CACHE=ROOT/'tmp/evaluation/projected_sequences.json'
RAW=ROOT/'data/raw/BPI Challenge 2017.xes.gz'
OUT=ROOT/'results/alpha';NAME='alpha_miner'
ASSESSMENT=ROOT/f'results/assessment/{NAME}.json'
EXPECTED={'cases':31509,'events':475306,'activities':24}
KEYS={'activity_key':'concept:name','timestamp_key':'time:timestamp','case_id_key':'case:concept:name'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
def rel(p):return Path(p).relative_to(ROOT).as_posix()

def verified_input():
    data=json.loads(CACHE.read_text(encoding='utf-8'))
    source=json.loads((ROOT/'data/manifest.json').read_text(encoding='utf-8'))
    pinned=next(f['sha256'] for f in source['files'] if f['path']==rel(RAW))
    if not sha(RAW)==pinned==data['raw_sha256']:raise ValueError('Raw log hash differs from data manifest or cache')
    baseline=json.loads((ROOT/'results/tables/discovery_manifest.json').read_text(encoding='utf-8'))['preprocessing']
    if data['projection']!=baseline:raise ValueError('Cache projection summary differs from the IM/HM discovery input')
    traces=data['traces'];sequences=[tuple(t['activities']) for t in traces]
    counts={}
    for s in sequences:
        for a in s:counts[a]=counts.get(a,0)+1
    found={'cases':len(traces),'events':sum(map(len,sequences)),'activities':len(counts)}
    if found!=EXPECTED or len({t['case_id'] for t in traces})!=len(traces):raise ValueError(f'Input counts {found} differ from {EXPECTED}')
    if (found['cases'],found['events'],found['activities'],dict(sorted(counts.items())))!=(baseline['discovery_cases'],
        baseline['discovery_events'],baseline['discovery_distinct_activities'],baseline['discovery_activity_counts']):
        raise ValueError('Per-activity counts differ from the discovery manifest')
    record={'path':rel(CACHE),'sha256':sha(CACHE),'raw_log':rel(RAW),'raw_sha256':data['raw_sha256'],
        **found,'variants':len(set(sequences)),'case_ids_unique':True,'empty_cases':sum(not s for s in sequences),
        'projection':'lifecycle:transition = complete, original XES order within each case (cache summary identical to results/tables/discovery_manifest.json preprocessing)',
        'event_log_construction':'PM4Py EventLog built from the cached activity sequences (src.model_assessment.event_log): trace attribute concept:name = case id, events carry concept:name only; no timestamps, no re-parsing of the raw XES',
        'why_sufficient':'Classic Alpha uses only the directly-follows relation and start/end activities, i.e. only the event order within each case'}
    return data,sequences,record

def footprint(sequences):
    variants=set(sequences)
    activities=sorted({a for s in variants for a in s})
    follows={(s[i],s[i+1]) for s in variants for i in range(len(s)-1)}
    causal={(a,b) for a,b in follows if (b,a) not in follows}
    parallel={(a,b) for a,b in follows if a<b and (b,a) in follows}
    choice={(a,b) for a in activities for b in activities if a<b and (a,b) not in follows and (b,a) not in follows}
    loop_two=sorted({tuple(sorted((s[i],s[i+1]))) for s in variants for i in range(len(s)-2) if s[i]==s[i+2]!=s[i+1]})
    return {'activities':activities,'follows':follows,'causal':causal,'parallel':parallel,'choice':choice,
            'start':sorted({s[0] for s in variants}),'end':sorted({s[-1] for s in variants}),
            'loop_one':[a for a in activities if (a,a) in follows],'loop_two':loop_two}

def maximal_pairs(fp):
    """Y_L: (A,B) is maximal iff B is a maximal #-clique in Succ(A) and A a maximal #-clique in Pred(B)."""
    follows,causal=fp['follows'],fp['causal']
    free=[a for a in fp['activities'] if (a,a) not in follows]
    choice={a:{b for b in free if b!=a and (a,b) not in follows and (b,a) not in follows} for a in free}
    succ={a:{b for b in free if (a,b) in causal} for a in free}
    pred={b:{a for a in free if (a,b) in causal} for b in free}
    def cliques(nodes):
        out=[]
        def bk(r,p,x):
            if not p and not x:out.append(frozenset(r));return
            for v in sorted(p):bk(r|{v},p&choice[v],x&choice[v]);p=p-{v};x=x|{v}
        bk(set(),set(nodes),set());return out
    found=set()
    def grow(A,S,rest):
        for B in cliques(S):
            P=set.intersection(*(pred[b] for b in B))-A
            if not any(A<=choice[c] for c in P):found.add((A,B))
        for i,c in enumerate(rest):
            if succ[c]&S:grow(A|{c},S&succ[c],[d for d in rest[i+1:] if d in choice[c]])
    for i,a in enumerate(free):
        if succ[a]:grow(frozenset({a}),succ[a],[d for d in free[i+1:] if d in choice[a]])
    return found

def signature(model):
    n,im,fm=model
    return (sorted((p.name,im.get(p,0),fm.get(p,0)) for p in n.places),sorted((t.name,t.label) for t in n.transitions),
            sorted((a.source.name,a.target.name,a.weight) for a in n.arcs))

def export(model):
    import pm4py
    from pm4py.visualization.petri_net import visualizer
    from src.discovery import structure_summary
    net,initial,final=model
    if len({n.name for n in [*net.places,*net.transitions]})!=len(net.places)+len(net.transitions):raise ValueError('Node names not unique')
    pnml=OUT/f'{NAME}.pnml';pm4py.write_pnml(net,initial,final,str(pnml))
    if signature(model)!=signature(pm4py.read_pnml(str(pnml))):raise ValueError('PNML round-trip changed topology/markings')
    graph=visualizer.apply(net,initial,final,parameters={'set_rankdir':'TB','font_size':'14','bgcolor':'white'})
    graph.attr('graph',nodesep='0.10',ranksep='0.10',pad='0.08');graph.attr('edge',arrowsize='0.55')
    for p in net.places:graph.node(str(id(p)),width='0.20',height='0.20',fontsize='10',fixedsize='true')
    for t in net.transitions:graph.node(str(id(t)),height='0.25',width='0.4',margin='0.04,0.02')
    paths=[pnml,OUT/f'{NAME}.gv'];paths[1].write_text(graph.source,encoding='utf-8',newline='\n')
    for fmt in ('pdf','svg','png'):
        path=OUT/f'{NAME}.{fmt}';path.write_bytes(graph.pipe(format=fmt));paths.append(path)
    return {**structure_summary(*model),'pnml_round_trip_verified':True,
            'artifacts':{rel(p):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths}}

def structure(net,fp,pairs):
    from pm4py.objects.petri_net.utils.check_soundness import check_wfnet
    from src.net_certificates import workflow_paths
    internal={(frozenset(a.source.label for a in p.in_arcs),frozenset(a.target.label for a in p.out_arcs))
              for p in net.places if p.name not in ('start','end')}
    def show(items):return sorted([sorted(a),sorted(b)] for a,b in items)
    def boundary(t):return {a.source.name for a in t.in_arcs}|{a.target.name for a in t.out_arcs}
    return {'workflow_net_directed_definition':workflow_paths(net),
            'pm4py_check_wfnet':{'value':bool(check_wfnet(net)),'note':'PM4Py tests source/sink connectivity on the UNDIRECTED graph only'},
            'internal_places':len(internal),'textbook_maximal_pairs':len(pairs),'pm4py_places_equal_textbook_Y_L':internal==pairs,
            'pairs_missing_in_pm4py':show(pairs-internal),'places_not_in_textbook_Y_L':show(internal-pairs),
            'transitions_without_input_place':sorted(t.label for t in net.transitions if not t.in_arcs),
            'transitions_without_output_place':sorted(t.label for t in net.transitions if not t.out_arcs),
            'isolated_transitions':sorted(t.label for t in net.transitions if not t.in_arcs and not t.out_arcs),
            'transitions_only_connected_to_start_or_end':sorted(t.label for t in net.transitions if boundary(t) and boundary(t)<={'start','end'}),
            'self_loop_activities_in_any_internal_place':sorted({x for a,b in internal for x in a|b}&set(fp['loop_one']))}

def discover():
    from importlib.metadata import version
    import pm4py
    from src.runtime import configure_runtime
    from src.model_assessment import event_log
    dot=configure_runtime()
    if not dot:raise RuntimeError('Graphviz not found; run scripts/setup_graphviz.py first.')
    started=perf_counter()
    data,sequences,source=verified_input()
    log=event_log(data);del data
    print(f"Discovery input: {source['cases']:,} cases, {source['events']:,} events, {source['activities']} activities.",flush=True)
    before=perf_counter();model=pm4py.discover_petri_net_alpha(log,**KEYS);seconds=perf_counter()-before
    model[0].name=NAME
    fp=footprint(sequences);pairs=maximal_pairs(fp)
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'algorithm':'Alpha Miner (classic), pm4py.discover_petri_net_alpha -> Variants.ALPHA_VERSION_CLASSIC',
        'reference':'van der Aalst, Weijters, Maruster (2004), IEEE TKDE 16(9), doi:10.1109/TKDE.2004.47',
        'input':source,
        'parameters':KEYS,
        'tuning_parameters':{'count':0,'note':'Classic Alpha exposes no thresholds, noise filter or frequency cut-off; only the attribute keys above. '
            'With EventLog input timestamp_key and case_id_key are not read (no sorting); every observed directly-follows pair counts, irrespective of frequency.'},
        'versions':{'python':platform.python_version(),'pm4py':version('pm4py'),'graphviz_python':version('graphviz'),
            'graphviz_executable':subprocess.run([dot,'-V'],capture_output=True,text=True,check=True).stderr.strip()},
        'randomness':{'random_seed':None,'python_hash_seed':os.environ['PYTHONHASHSEED'],
            'reason':'No stochastic step; the hash seed fixes set iteration order, on which PM4Py place names and its single-pass pair-merging loop depend.',
            'normalization':'Only the net name (PM4Py: alpha_classic_net_<time>) is set to alpha_miner; no node, arc or label changed.',
            'byte_reproducibility':'PNML arc ids and Graphviz node ids derive from object hashes; behaviour, not bytes, is reproducible.'},
        'footprint':{'activities':len(fp['activities']),'directly_follows_pairs':len(fp['follows']),
            'causal_pairs':len(fp['causal']),'parallel_pairs_unordered':len(fp['parallel']),'choice_pairs_unordered':len(fp['choice']),
            'start_activities':fp['start'],'end_activities':fp['end'],
            'length_one_loop_activities':fp['loop_one'],'length_two_loop_pairs':[list(p) for p in fp['loop_two']],
            'length_two_loop_pairs_classified_parallel':sum(p in fp['parallel'] for p in fp['loop_two']),
            'method':f'own computation on the {source["variants"]:,} distinct variants; a>b observed directly-follows, a->b iff a>b and not b>a, a||b iff a>b and b>a, a#b iff neither'},
        'discovery_seconds':round(seconds,3),
        'visualization':{'rankdir':'TB','font_size':14,'nodesep':0.10,'ranksep':0.10,'place_diameter_inches':0.20,
            'note':'Same layout settings as scripts/discover_models.py; all nodes, arcs and labels retained.'},
        'implementation_sha256':{p:sha(ROOT/p) for p in ('scripts/discover_alpha.py','src/discovery.py','src/model_assessment.py','src/net_certificates.py')}}
    print('Exporting PNML and figures...',flush=True)
    manifest['model']=export(model)
    manifest['structure']=structure(model[0],fp,pairs)
    manifest['quality_evaluation']=f'scripts/assess_model.py results/alpha/{NAME}.pnml --name {NAME} -> results/assessment/{NAME}.json'
    manifest['total_seconds']=round(perf_counter()-started,3)
    write(OUT/'manifest.json',manifest)
    m=manifest['model'];print(f"Exported {NAME}: {m['places']} places, {m['transitions']} transitions, {m['arcs']} arcs ({seconds:.2f}s); "
        f"PM4Py places equal textbook Y_L: {manifest['structure']['pm4py_places_equal_textbook_Y_L']}",flush=True)

def audit():
    from importlib.metadata import version
    import pm4py
    from src.net_certificates import deterministic_replay,final_marking_certificate
    from src.validation import dead_transition_certificates
    path=OUT/f'{NAME}.pnml';net,initial,final=pm4py.read_pnml(str(path))
    assessed=json.loads(ASSESSMENT.read_text(encoding='utf-8'));sound=assessed['soundness']
    if assessed['pnml_sha256']!=sha(path):raise ValueError('Assessment belongs to another PNML; re-run scripts/assess_model.py')
    trigger={'assessment':rel(ASSESSMENT),'assessment_sha256':sha(ASSESSMENT),'classical_status':sound['classical']['status'],
             'easy_sound':sound['behavioural']['easy_sound'],'final_marking_reachable':sound['classical'].get('final_reachable')}
    if trigger['classical_status']!='unbounded' and trigger['easy_sound'] is not False:raise SystemExit('Net bounded with reachable final marking; no audit needed.')
    traces=json.loads(CACHE.read_text(encoding='utf-8'))['traces']
    implementation={p:sha(ROOT/p) for p in ('src/net_certificates.py','scripts/discover_alpha.py')}
    write(OUT/'completion_audit.json',{'model':rel(path),'model_sha256':sha(path),'input_cache_sha256':sha(CACHE),'trigger':trigger,
        'final_marking':final_marking_certificate(net,initial,final),
        'exact_replay':deterministic_replay(net,initial,final,[tuple(t['activities']) for t in traces]),
        'scipy':version('scipy'),'implementation_sha256':implementation})
    proofs=dead_transition_certificates(net,initial)
    labels={t.label for t in net.transitions if t.label is not None}
    unreachable=sorted(l for l in labels if all(t.name in proofs for t in net.transitions if t.label==l))
    affected=sum(any(a in unreachable for a in t['activities']) for t in traces)
    record={'model_sha256':sha(path),'certified_dead_count_lower_bound':len(proofs),'complete_dead_transition_enumeration':False,
        'activity_labels':sorted(t.label for t in net.transitions if t.name in proofs and t.label is not None),'certificates':proofs,
        'unreachable_activity_labels':unreachable,
        'case_replay_upper_bound':{'cases':len(traces),'provably_unfit_cases':affected,'maximum_fitting_cases':len(traces)-affected,
            'maximum_fitting_percentage':100*(len(traces)-affected)/len(traces),'input_cache_sha256':sha(CACHE)}}
    write(OUT/'dead_transition_certificates.json',{'method':'Nonnegative place subinvariants; exact rational verification of all inequalities',
        'scipy':version('scipy'),'trigger':trigger,'models':{NAME:record},
        'implementation_sha256':{p:sha(ROOT/p) for p in ('src/validation.py','scripts/discover_alpha.py')}})
    print(NAME,'certified unreachable:',len(proofs),flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',action='store_true',help='Only audit the exported net (needs results/assessment/alpha_miner.json).')
    args=parser.parse_args()
    if os.environ.get('PYTHONHASHSEED')!=HASH_SEED:
        env=dict(os.environ,PYTHONHASHSEED=HASH_SEED)
        raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],env=env,cwd=ROOT))
    os.environ['PM4PY_DEFAULT_IS_THREADING_MANAGEMENT_ENABLED']='False';os.environ['PM4PY_SHOW_PROGRESS_BAR']='False'
    audit() if args.audit else discover()

if __name__=='__main__':main()
