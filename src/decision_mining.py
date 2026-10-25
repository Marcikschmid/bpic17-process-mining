"""Alignment-based guard discovery, following de Leoni & van der Aalst (2013).

Record the PRE-firing variable state; update only after synchronous moves
(Algorithm 1). IDs and retrospective offer outcome flags are excluded.
"""
import json
import xml.etree.ElementTree as ET
from collections import defaultdict

BPMN='http://www.omg.org/spec/BPMN/20100524/MODEL'
NS={'b':BPMN,'di':'http://www.omg.org/spec/BPMN/20100524/DI',
    'dc':'http://www.omg.org/spec/DD/20100524/DC','edge':'http://www.omg.org/spec/DD/20100524/DI'}
CASE_FIELDS=('ApplicationType','LoanGoal','RequestedAmount')
EVENT_FIELDS=('CreditScore','FirstWithdrawalAmount','MonthlyCost','NumberOfTerms','OfferedAmount')


def bpmn_net(path):
    """Ordinary token-flow semantics with stable IDs for EACH outgoing XOR flow.

Only the task/start/end/XOR/AND subset present in this project is accepted.
Flow places make gateway-to-transition correspondence explicit, with no reduction.
"""
    from pm4py.objects.petri_net.obj import PetriNet,Marking
    from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to
    root=ET.parse(path).getroot();process=root.find('b:process',NS)
    flows={e.attrib['id']:e for e in process.findall('b:sequenceFlow',NS)}
    nodes={e.attrib['id']:e for e in process if e.tag.split('}')[-1] in
           ('task','startEvent','endEvent','exclusiveGateway','parallelGateway')}
    incoming=defaultdict(list);outgoing=defaultdict(list)
    for fid,e in flows.items():
        if e.attrib['sourceRef'] not in nodes or e.attrib['targetRef'] not in nodes:raise ValueError('Unsupported BPMN node')
        incoming[e.attrib['targetRef']].append(fid);outgoing[e.attrib['sourceRef']].append(fid)
    net=PetriNet('BPMN flow semantics');places={fid:PetriNet.Place(fid) for fid in flows}
    places['__source']=PetriNet.Place('__source');places['__sink']=PetriNet.Place('__sink')
    net.places.update(places.values());choices={};gateways=[];split_number=merge_number=0
    def transition(name,label,pre,post):
        t=PetriNet.Transition(name,label);net.transitions.add(t)
        for fid in pre:add_arc_from_to(places[fid],t,net)
        for fid in post:add_arc_from_to(t,places[fid],net)
    coords={e.attrib['bpmnElement']:(float(e.find('dc:Bounds',NS).attrib['y']),float(e.find('dc:Bounds',NS).attrib['x']))
            for e in root.findall('.//di:BPMNShape',NS)}
    for nid,e in sorted(nodes.items(),key=lambda pair:(coords.get(pair[0],(0,0)),pair[0])):
        tag=e.tag.split('}')[-1];ins=sorted(incoming[nid]);outs=sorted(outgoing[nid])
        if tag=='exclusiveGateway':
            split=len(outs)>1
            if split:split_number+=1;key=f'D{split_number:02d}'
            else:merge_number+=1;key=f'M{merge_number:02d}'
            record={'id':key,'bpmn_id':nid,'kind':'split' if split else 'merge','outgoing':outs,'incoming':ins,'branches':{}}
            for a in ins:
                for j,b in enumerate(outs):
                    name=f'{nid}|{a}|{b}';transition(name,None,[a],[b])
                    if split:choices[name]=(key,b)
                    record['branches'][b]=f'B{j+1}'
            gateways.append(record)
        elif tag=='startEvent':transition(nid,None,['__source'],outs)
        elif tag=='endEvent':transition(nid,None,ins,['__sink'])
        else:
            if tag=='task' and (len(ins)!=1 or len(outs)!=1):raise ValueError('Ambiguous implicit task gateway')
            transition(nid,e.attrib.get('name') if tag=='task' else None,ins,outs)
    return net,Marking({places['__source']:1}),Marking({places['__sink']:1}),gateways,choices


def observations(events,case_attributes,alignment,choices):
    """Return snapshots of known inputs BEFORE the outgoing-flow transition."""
    state={f'case_{k}':case_attributes[k] for k in CASE_FIELDS if k in case_attributes}
    result=[];latest=None
    for step_index,move in enumerate(alignment['moves']):
        if move['transition'] in choices:
            gateway,flow=choices[move['transition']]
            result.append({'gateway':gateway,'flow':flow,'features':state.copy(),
                           'alignment_step':step_index,'last_sync_event':latest})
        if move['kind']=='sync':
            latest=move['event_index'];event=events[latest]
            for k in EVENT_FIELDS:
                if k in event and event[k] is not None:
                    value=event[k]
                    if isinstance(value,bool) or not isinstance(value,(int,float)) or value<0:raise ValueError('Expected nonnegative numeric input')
                    state[f'event_{k}']=value
    return result


def encode_features(features):
    result={k:features.get(k,'__MISSING__') for k in ('case_ApplicationType','case_LoanGoal')}
    for k in ('case_RequestedAmount',*(f'event_{x}' for x in EVENT_FIELDS)):
        result[k]=float(features.get(k,-1));result[k+'_known']=int(k in features)
    return result


def tree_rules(classifier,feature_names):
    """Exact disjoint leaf predicates; no rounding thresholds in saved rules."""
    tree=classifier.tree_;leaves=[]
    def walk(node,path):
        if tree.children_left[node]==tree.children_right[node]:
            label=str(classifier.classes_[tree.value[node][0].argmax()])
            leaves.append({'node':int(node),'class':label,'predicates':path,
                           'samples':int(tree.n_node_samples[node]),'distribution':tree.value[node][0].tolist()})
        else:
            feature=feature_names[tree.feature[node]];threshold=float(tree.threshold[node])
            walk(tree.children_left[node],path+[{'feature':feature,'op':'<=','threshold':threshold}])
            walk(tree.children_right[node],path+[{'feature':feature,'op':'>','threshold':threshold}])
    walk(0,[]);return leaves


def predict_rules(leaves,encoded):
    matches=[]
    for leaf in leaves:
        good=True
        for p in leaf['predicates']:
            name=p['feature']
            value=float(encoded.get(name,0)) if '=' not in name else float(str(encoded.get(name.split('=',1)[0],''))==name.split('=',1)[1])
            if not ((value<=p['threshold']) if p['op']=='<=' else (value>p['threshold'])):good=False;break
        if good:matches.append(leaf['class'])
    if len(matches)!=1:raise ValueError('Guard partition is not exclusive and exhaustive')
    return matches[0]


def guarded_accepts(aligner,events,case_attributes,choices,models):
    """Exact whole-trace replay with learned guards on the fixed event order.

    In deviation-free replay every event synchronizes. Its values become known
    only AFTER that step. Explore all allowed tau paths, not one chosen alignment.
    """
    import numpy as np
    state={f'case_{k}':case_attributes[k] for k in CASE_FIELDS if k in case_attributes}
    def closure(markings):
        encoded=encode_features(state)
        encoded={k:float(np.float32(v)) if isinstance(v,(float,int)) else v for k,v in encoded.items()}
        predictions={};seen=set(markings);queue=list(markings)
        for s in queue:
            for k,target in aligner.edges[s]:
                t=aligner.transitions[k]
                if t.label is not None:continue
                if t.name in choices:
                    gateway,flow=choices[t.name]
                    if gateway not in predictions:predictions[gateway]=predict_rules(models[gateway]['leaves'],encoded)
                    if predictions[gateway]!=flow:continue
                if target not in seen:seen.add(target);queue.append(target)
        return seen
    markings=closure({0})
    for event in events:
        targets={target for s in markings for k,target in aligner.edges[s]
                 if aligner.transitions[k].label==event['concept:name']}
        if not targets:return False
        for field in EVENT_FIELDS:
            if field in event and event[field] is not None:state[f'event_{field}']=event[field]
        markings=closure(targets)
    return aligner.final in markings


def feel_guard(leaves,flow):
    clauses=[]
    for leaf in leaves:
        if leaf['class']!=flow:continue
        tests=[]
        for p in leaf['predicates']:
            name=p['feature']
            if '=' in name:
                base,value=name.split('=',1)
                expression=f'(if {base} = {json.dumps(value)} then 1 else 0)'
            elif name.endswith('_known'):
                expression=f'(if {name[:-6]} = null then 0 else 1)'
            else:expression=f'(if {name} = null then -1 else {name})'
            # scikit-learn converts input to float32. Carry that distinction in
            # metadata; FEEL rendering uses the equivalent threshold boundary.
            import numpy as np
            lo=np.float32(p['threshold']);hi=np.nextafter(lo,np.float32(float('inf')))
            if float(lo)>p['threshold']:
                hi=lo;lo=np.nextafter(lo,np.float32(float('-inf')))
            boundary=(float(lo)+float(hi))/2
            tests.append(f'{expression} {"<" if p["op"]=="<=" else ">="} {boundary:.17g}')
        clauses.append('('+' and '.join(tests)+')' if tests else 'true')
    return ' or '.join(clauses) if clauses else 'false'
