"""Mine guards for every final BPMN XOR split; never overwrite baseline models."""
import os,sys,json,gzip,hashlib,csv,time
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
os.environ['PM4PY_DEFAULT_IS_THREADING_MANAGEMENT_ENABLED']='False'
from src.runtime import configure_runtime
configure_runtime()
from src.decision_mining import bpmn_net,observations,encode_features,tree_rules,predict_rules,guarded_accepts,CASE_FIELDS,EVENT_FIELDS
from src.finite_alignment import FiniteAligner

OUT=ROOT/'results/decision_mining';CACHE=ROOT/'tmp/decision_mining';SEED=20261018
# Final model after manual edits (scripts/export_final_model.py); the run of 2026-10-18 used results/refinement.
MODEL=ROOT/'results/final'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');temp.replace(p)

def data_rows():
    """Streaming original-order completion projection; parse only allowed inputs."""
    path=ROOT/'data/raw/BPI Challenge 2017.xes.gz'
    with gzip.open(path,'rb') as stream:
        for _,element in ET.iterparse(stream,events=('end',)):
            if element.tag.split('}')[-1]!='trace':continue
            attributes={};events=[]
            for child in element:
                if child.tag.split('}')[-1]=='event':
                    raw={e.attrib.get('key'):e for e in child}
                    if raw.get('lifecycle:transition') is None or raw['lifecycle:transition'].attrib.get('value')!='complete':continue
                    event={'concept:name':raw['concept:name'].attrib['value']}
                    for field in EVENT_FIELDS:
                        if field in raw:event[field]=float(raw[field].attrib['value'])
                    events.append(event)
                elif child.attrib.get('key') in (*CASE_FIELDS,'concept:name'):
                    key=child.attrib['key'];value=child.attrib['value']
                    attributes[key]=float(value) if key=='RequestedAmount' else value
            yield attributes['concept:name'],attributes,events
            element.clear()

def main():
    import pm4py,numpy as np
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.metrics import accuracy_score,balanced_accuracy_score,f1_score,confusion_matrix
    from sklearn.model_selection import train_test_split
    from src.replay_coverage import ExactReplay
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    bpmn=MODEL/'final_model.bpmn'
    net,im,fm,gateways,choices=bpmn_net(bpmn)
    # Full-language audit against the independently converted/exported net.
    original=ExactReplay(*pm4py.read_pnml(str(MODEL/'final_model.pnml')))
    machine=ExactReplay(net,im,fm)
    equivalence=original.language_equivalent(machine)
    if not equivalence['equivalent'] or not machine.sound:raise ValueError('BPMN decision net mismatch')
    print(f'Flow net: {machine.state_count} states; complete language equivalence {equivalence}',flush=True)
    aligner=FiniteAligner(net,im,fm)
    input_path=ROOT/'tmp/evaluation/projected_sequences.json';data=json.loads(input_path.read_text(encoding='utf-8'))
    if sha(ROOT/'data/raw/BPI Challenge 2017.xes.gz')!=data['raw_sha256']:raise ValueError('Raw source changed')
    identity={'bpmn_sha256':sha(bpmn),'input_cache_sha256':sha(input_path),
              'implementation_sha256':sha(ROOT/'src/finite_alignment.py'),'cost_profile':'sync=0,tau=1,visible/log=10000'}
    grouped=Counter(tuple(t['activities']) for t in data['traces']);alignments={}
    started=time.perf_counter()
    for i,sequence in enumerate(grouped):
        key=hashlib.sha256(json.dumps(sequence,ensure_ascii=False).encode()).hexdigest();path=CACHE/(key+'.json')
        saved=json.loads(path.read_text()) if path.exists() else None
        if saved and saved.get('identity')==identity:result=saved['result']
        else:
            result=aligner.align(sequence);write(path,{'identity':identity,'activities':sequence,'result':result})
        aligner.verify(sequence,result);alignments[sequence]=result
        if i%100==0 or i+1==len(grouped):print(f'ALIGN {i+1}/{len(grouped)} variants; {time.perf_counter()-started:.1f}s',flush=True)
    # Cross-check exact COSTS against unmodified PM4Py on fit/unfit/long/random variants.
    from pm4py.algo.conformance.alignments.petri_net import algorithm as ali
    from pm4py.objects.log.obj import Event,Trace
    sequences=list(grouped);rng=np.random.default_rng(SEED)
    selected=set(rng.choice(len(sequences),16,replace=False).tolist())
    selected.update(sorted(range(len(sequences)),key=lambda i:len(sequences[i]),reverse=True)[:4])
    selected.update(i for i in range(min(4,len(sequences))))
    reference=[]
    for i in sorted(selected):
        sequence=sequences[i];value=ali.apply_trace(Trace([Event({'concept:name':a}) for a in sequence]),net,im,fm,
              parameters={'show_progress_bar':False,'model_cost_function':{t:1 if t.label is None else 10000 for t in net.transitions}},
              variant=ali.Variants.VERSION_DIJKSTRA_LESS_MEMORY)
        if value['cost']!=alignments[sequence]['cost']:raise ValueError('PM4Py alignment cost mismatch')
        reference.append({'variant_index':i,'cost':value['cost']})
        print(f'PM4Py reference {len(reference)}/{len(selected)} passed',flush=True)
    print(f'PM4Py reference: {len(reference)} exact cost checks passed',flush=True)
    case_ids=[t['case_id'] for t in data['traces']]
    training,testing=train_test_split(case_ids,test_size=.30,random_state=SEED)
    training=set(training);testing=set(testing)
    tables=defaultdict(list);rows=0;replay_fits=0;alignment_cost=0
    activity_counts=Counter();field_counts=defaultdict(Counter)
    for index,(case_id,attributes,events) in enumerate(data_rows()):
        expected=data['traces'][index];sequence=tuple(e['concept:name'] for e in events)
        if case_id!=expected['case_id'] or sequence!=tuple(expected['activities']):raise ValueError('Projection/order mismatch')
        alignment=alignments[sequence]
        replay_fits+=original.accepts(sequence);alignment_cost+=alignment['cost']
        for event in events:
            label=event['concept:name'];activity_counts[label]+=1
            for field in EVENT_FIELDS:
                if field in event:field_counts[label][field]+=1
        for row in observations(events,attributes,alignment,choices):
            row['case_id']=case_id;row['split']='train' if case_id in training else 'test';tables[row['gateway']].append(row);rows+=1
    if index+1!=len(case_ids):raise ValueError('Missing cases')
    write(OUT/'case_split.json',{'seed':SEED,'train_cases':sorted(training),'test_cases':sorted(testing)})
    print(f'EXTRACT {rows} decisions across {len(tables)} splits, all {len(case_ids)} cases',flush=True)
    summaries=[]
    for gateway in gateways:
        if gateway['kind']=='merge':
            summaries.append({**gateway,'status':'merge_no_choice','reason':'One outgoing flow; pass-through, no classification target.'});continue
        key=gateway['id'];table=tables[key]
        if not table:raise ValueError(f'No aligned observations for {key}')
        write(OUT/'observations'/f'{key}.json',table)
        train=[r for r in table if r['split']=='train'];test=[r for r in table if r['split']=='test']
        vectorizer=DictVectorizer(sparse=False)
        X=vectorizer.fit_transform([encode_features(r['features']) for r in train]);y=np.array([r['flow'] for r in train])
        clf=DecisionTreeClassifier(max_depth=3,min_samples_leaf=50,random_state=SEED)
        clf.fit(X,y);names=vectorizer.get_feature_names_out().tolist();leaves=tree_rules(clf,names)
        predictions=clf.predict(vectorizer.transform([encode_features(r['features']) for r in test])) if test else []
        truth=[r['flow'] for r in test];majority=Counter(y).most_common(1)[0][0]
        # Exported predicates must reproduce the fitted sklearn tree on EVERY observation.
        encoded_rows=[encode_features(r['features']) for r in table]
        expected_predictions=clf.predict(vectorizer.transform(encoded_rows))
        for encoded,expected in zip(encoded_rows,expected_predictions):
            # sklearn trees use float32 internally; cast numeric values before rule checks.
            checked={k:float(np.float32(v)) if isinstance(v,(int,float)) else v for k,v in encoded.items()}
            if predict_rules(leaves,checked)!=str(expected):raise ValueError('Exported rule differs from classifier')
        labels=gateway['outgoing'];counts=Counter(r['flow'] for r in table)
        summary={**gateway,'status':'ok','observations':len(table),'train':len(train),'test':len(test),
            'train_cases':len(set(r['case_id'] for r in train)),'test_cases':len(set(r['case_id'] for r in test)),
            'branch_counts':dict(counts),'unobserved_branches':list(set(labels)-counts.keys()),
            'never_predicted_branches':list(set(labels)-{l['class'] for l in leaves}),
            'accuracy':float(accuracy_score(truth,predictions)) if test else None,
            'balanced_accuracy':float(balanced_accuracy_score(truth,predictions)) if test else None,
            'macro_f1':float(f1_score(truth,predictions,labels=labels,average='macro',zero_division=0)) if test else None,
            'majority_accuracy':float(accuracy_score(truth,[majority]*len(truth))) if test else None,
            'confusion_matrix':confusion_matrix(truth,predictions,labels=labels).tolist() if test else None,
            'features':names,'leaves':leaves,'depth':clf.get_depth(),
            'used_features':sorted({p['feature'] for l in leaves for p in l['predicates']}),
            'class_order':clf.classes_.tolist(),'parameters':clf.get_params(),
            'rule_check_rows':len(table)}
        summaries.append(summary)
        print(f'{key}: n={len(table)} test={len(test)} accuracy={summary["accuracy"]:.4f} majority={summary["majority_accuracy"]:.4f}',flush=True)
    models={g['id']:g for g in summaries if g['kind']=='split'}
    guarded={'train':Counter(),'test':Counter()}
    with (OUT/'guarded_replay.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['case_id','split','structural_fit','guarded_fit'])
        for i,(case_id,attributes,events) in enumerate(data_rows()):
            structural=original.accepts(tuple(e['concept:name'] for e in events))
            fit=guarded_accepts(aligner,events,attributes,choices,models) if structural else False
            split='train' if case_id in training else 'test'
            guarded[split]['cases']+=1;guarded[split]['structural_fitting_cases']+=structural;guarded[split]['guarded_fitting_cases']+=fit
            writer.writerow([case_id,split,int(structural),int(fit)])
            if i%5000==0:print(f'GUARDED REPLAY {i+1}/{len(case_ids)} cases',flush=True)
    writes={label:{field:{'present':count,'events':activity_counts[label],'percentage':100*count/activity_counts[label],
                         'write_operation_at_95_percent':count/activity_counts[label]>=.95}
                   for field,count in fields.items()} for label,fields in field_counts.items()}
    report={'status':'ok','created_utc':datetime.now(timezone.utc).isoformat(),'seed':SEED,
        'implementation_sha256':{p:sha(ROOT/p) for p in ('src/finite_alignment.py','src/decision_mining.py','scripts/mine_decisions.py')},
        'method':'de Leoni & van der Aalst (2013), Algorithm 1; CART replaces C4.5, explicit missingness',
        'identity':identity,'raw_sha256':data['raw_sha256'],'gateways':summaries,
        'cases':len(case_ids),'variants':len(grouped),'observations':rows,'exact_structural_fitting_cases':replay_fits,
        'alignment_cost_sum':alignment_cost,'flow_net_states':len(aligner.states),'bpmn_language_equivalence':equivalence,
        'reference_checks':reference,'training_cases':len(training),'testing_cases':len(testing),
        'write_operations':writes,'write_threshold_percentage':95,'guarded_replay':guarded,
        'case_fields':CASE_FIELDS,'event_fields':EVENT_FIELDS,
        'excluded':['case/Event/Offer IDs','Accepted','Selected','activity label','resource','Action','EventOrigin','timestamps'],
        'limitations':['One deterministic optimal alignment; choices/parallel data order may be ambiguous.',
           'Control-flow discovered using full log: held-out metrics assess guards conditional on this fixed model.',
           'Last synchronized offer values may belong to different offers; no object-centric correlation.',
           'Guards are statistical associations, not validated bank policy or executable automation.',
           'Train-only tree can assign false to minority/unobserved branches; these are reported explicitly.']}
    write(OUT/'decision_mining.json',report)
    fields=['id','bpmn_id','kind','status','observations','train','test','accuracy','balanced_accuracy','macro_f1','majority_accuracy']
    with (OUT/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(summaries)
    print('DONE: all XOR nodes inventoried and all split guards audited',flush=True)

if __name__=='__main__':main()
