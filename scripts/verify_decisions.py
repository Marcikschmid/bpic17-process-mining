"""Audit saved decisions, case split, all rule predictions and BPMN coverage inventory."""
import os,sys,json,csv,hashlib
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from src.decision_mining import bpmn_net,encode_features,predict_rules,observations,NS,CASE_FIELDS,EVENT_FIELDS,feel_guard
OUT=ROOT/'results/decision_mining'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts-only',action='store_true',help='After a completed full audit, verify a cosmetic re-render without retraining or re-extracting.')
    args=parser.parse_args()
    if args.artifacts_only:
        audit=json.loads((OUT/'verification.json').read_text())
        assert audit['status']=='ok' and audit['source_sha256']==sha(OUT/'decision_mining.json')
        data=json.loads((OUT/'decision_mining.json').read_text())
        for p,digest in data['implementation_sha256'].items():assert sha(ROOT/p)==digest,p
        manifest=json.loads((OUT/'presentation_manifest.json').read_text())
        assert manifest['source_sha256']==audit['source_sha256']
        for p,digest in manifest['artifacts'].items():assert sha(OUT/p)==digest,p
        from src.decision_display import annotation_text,compact_rules
        annotated=ET.parse(OUT/'decision_model.bpmn').getroot()
        flows={e.attrib['id']:e for e in annotated.findall('.//b:sequenceFlow',NS)}
        checked=0
        for gateway in data['gateways']:
            if gateway['kind']!='split':continue
            note=annotated.find(f'.//b:textAnnotation[@id="note_{gateway["id"]}"]/b:text',NS)
            assert note is not None and note.text==annotation_text(gateway)
            compact_rules(gateway['leaves'])  # Exact prefix cover, same branch on every original leaf.
            for flow in gateway['outgoing']:
                assert flows[flow].find('b:conditionExpression',NS).text==feel_guard(gateway['leaves'],flow)
            checked+=1
        selections=json.loads((ROOT/'docs/decision_report_manifest.json').read_text())
        for p,record in selections.items():assert sha(ROOT/'report'/p)==record['sha256']==sha(ROOT/record['source']),p
        result={'status':'ok','scientific_audit_source_sha256':audit['source_sha256'],
            'presentation_manifest_sha256':sha(OUT/'presentation_manifest.json'),'report_copies_checked':len(selections),
            'visible_xor_rule_blocks_checked':checked}
        (OUT/'artifact_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return
    import numpy as np
    from sklearn.metrics import accuracy_score,balanced_accuracy_score,f1_score,confusion_matrix
    data=json.loads((OUT/'decision_mining.json').read_text(encoding='utf-8'))
    split=json.loads((OUT/'case_split.json').read_text());train=set(split['train_cases']);test=set(split['test_cases'])
    assert not train&test and len(train|test)==data['cases']
    assert sha(ROOT/'data/raw/BPI Challenge 2017.xes.gz')==data['raw_sha256']
    assert sha(ROOT/'results/refinement/final_model.bpmn')==data['identity']['bpmn_sha256']
    if 'implementation_sha256' in data:
        for p,digest in data['implementation_sha256'].items():assert sha(ROOT/p)==digest,p
    net,im,fm,gateways,choices=bpmn_net(ROOT/'results/refinement/final_model.bpmn')
    assert {(g['id'],g['bpmn_id'],g['kind']) for g in gateways}=={(g['id'],g['bpmn_id'],g['kind']) for g in data['gateways']}
    annotated=ET.parse(OUT/'decision_model.bpmn').getroot()
    flows={e.attrib['id']:e for e in annotated.findall('.//b:sequenceFlow',NS)}
    def row_hash(row):return hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    def exported_prediction(leaves,encoded):
        matches=[]
        for leaf in leaves:
            good=True
            for p in leaf['predicates']:
                name=p['feature']
                value=float(encoded.get(name,0)) if '=' not in name else float(str(encoded.get(name.split('=',1)[0],''))==name.split('=',1)[1])
                lo=np.float32(p['threshold']);hi=np.nextafter(lo,np.float32(float('inf')))
                if float(lo)>p['threshold']:hi=lo;lo=np.nextafter(lo,np.float32(float('-inf')))
                boundary=(float(lo)+float(hi))/2
                if not ((value<boundary) if p['op']=='<=' else (value>=boundary)):good=False;break
            if good:matches.append(leaf['class'])
        assert len(matches)==1
        return matches[0]
    saved_rows=Counter()
    rules_checked=conditions_checked=0;allowed={f'case_{k}' for k in CASE_FIELDS}|{f'event_{k}' for k in EVENT_FIELDS}
    for g in data['gateways']:
        if g['kind']=='merge':assert g['status']=='merge_no_choice';continue
        rows=json.loads((OUT/'observations'/f'{g["id"]}.json').read_text(encoding='utf-8'))
        assert len(rows)==g['observations']
        test_truth=[];test_pred=[];counts=Counter();training_labels=Counter()
        for row in rows:
            saved_rows[row_hash(row)]+=1
            assert set(row['features'])<=allowed
            assert row['flow'] in g['outgoing'] and row['gateway']==g['id']
            assert row['split']==('train' if row['case_id'] in train else 'test')
            encoded_raw=encode_features(row['features']);encoded={k:float(np.float32(v)) if isinstance(v,(float,int)) else v for k,v in encoded_raw.items()}
            prediction=predict_rules(g['leaves'],encoded);rules_checked+=1;counts[row['flow']]+=1
            assert exported_prediction(g['leaves'],encoded_raw)==prediction
            if row['split']=='test':test_truth.append(row['flow']);test_pred.append(prediction)
            else:training_labels[row['flow']]+=1
        assert dict(counts)==g['branch_counts']
        labels=g['outgoing'];majority=training_labels.most_common(1)[0][0]
        assert abs(accuracy_score(test_truth,test_pred)-g['accuracy'])<1e-12
        assert abs(accuracy_score(test_truth,[majority]*len(test_truth))-g['majority_accuracy'])<1e-12
        assert abs(f1_score(test_truth,test_pred,labels=labels,average='macro',zero_division=0)-g['macro_f1'])<1e-12
        assert confusion_matrix(test_truth,test_pred,labels=labels).tolist()==g['confusion_matrix']
        for fid in labels:
            expression=flows[fid].find('b:conditionExpression',NS)
            assert expression is not None and expression.text==feel_guard(g['leaves'],fid)
            conditions_checked+=1
        assert annotated.find(f'.//b:textAnnotation[@id="note_{g["id"]}"]',NS) is not None
    assert rules_checked==data['observations']
    # Reconstruct EVERY snapshot from raw XES and aligned transition order.
    from scripts.mine_decisions import data_rows
    cache={};raw_rows=Counter();raw_cases=0
    for case_id,attributes,events in data_rows():
        sequence=tuple(e['concept:name'] for e in events)
        if sequence not in cache:
            key=hashlib.sha256(json.dumps(sequence,ensure_ascii=False).encode()).hexdigest()
            alignment=json.loads((ROOT/'tmp/decision_mining'/(key+'.json')).read_text(encoding='utf-8'))
            assert alignment['identity']==data['identity']
            cache[sequence]=alignment['result']
        for row in observations(events,attributes,cache[sequence],choices):
            row['case_id']=case_id;row['split']='train' if case_id in train else 'test'
            raw_rows[row_hash(row)]+=1
        raw_cases+=1
    assert saved_rows==raw_rows and raw_cases==data['cases']
    guarded=Counter();seen=set()
    with (OUT/'guarded_replay.csv').open(encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            assert row['case_id'] not in seen;seen.add(row['case_id'])
            assert row['split']==('train' if row['case_id'] in train else 'test')
            assert not int(row['guarded_fit']) or int(row['structural_fit'])
            guarded['cases']+=1;guarded['structural']+=int(row['structural_fit']);guarded['guarded']+=int(row['guarded_fit'])
    assert seen==train|test and guarded['structural']==data['exact_structural_fitting_cases']
    for p,digest in json.loads((OUT/'presentation_manifest.json').read_text())['artifacts'].items():assert sha(OUT/p)==digest,p
    result={'status':'ok','source_sha256':sha(OUT/'decision_mining.json'),'xor_nodes':len(gateways),
        'xor_splits':sum(g['kind']=='split' for g in gateways),'xor_merges':sum(g['kind']=='merge' for g in gateways),
        'rule_predictions_checked':rules_checked,'flow_conditions_checked':conditions_checked,'case_split_overlap':0,
        'guarded_replay_counts':dict(guarded),'reference_cost_checks':len(data['reference_checks']),
        'raw_snapshot_rows_reconstructed':sum(raw_rows.values()),'exported_guard_predicate_rows_checked':rules_checked}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
