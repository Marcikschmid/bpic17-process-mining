"""Render factual decision blocks and an annotated BPMN; keep report selection explicit."""
import sys,json,html,textwrap,hashlib,shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.runtime import configure_runtime
configure_runtime()
from src.decision_mining import BPMN,NS,feel_guard
from src.decision_display import annotation_text,compact_rules
OUT=ROOT/'results/decision_mining'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def short_feature(name):return name.replace('case_','c.').replace('event_','e.').replace('FirstWithdrawalAmount','FirstWithdrawal').replace('ApplicationType','AppType')
def leaf_text(leaf,branches):
    tests=[]
    for p in leaf['predicates']:
        if '=' in p['feature'] and 0<=p['threshold']<1:
            feature,value=p['feature'].split('=',1)
            tests.append(f'{short_feature(feature)} {"!=" if p["op"]=="<=" else "="} {json.dumps(value)}')
        else:tests.append(f'{short_feature(p["feature"])} {p["op"]} {p["threshold"]:.8g}')
    return (' AND '.join(tests) if tests else 'TRUE')+' -> '+branches[leaf['class']]

def main():
    import graphviz
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import FancyBboxPatch,Polygon
    data=json.loads((OUT/'decision_mining.json').read_text(encoding='utf-8'))
    root=ET.parse(ROOT/'results/refinement/final_model.bpmn').getroot()
    process=root.find('b:process',NS);nodes={e.attrib.get('id'):e for e in process};flows={e.attrib['id']:e for e in process.findall('b:sequenceFlow',NS)}
    for prefix,uri in [('bpmn',BPMN),('bpmndi',NS['di']),('omgdc',NS['dc']),('omgdi',NS['edge']),('xsi','http://www.w3.org/2001/XMLSchema-instance')]:ET.register_namespace(prefix,uri)
    root.set('expressionLanguage','https://www.omg.org/spec/DMN/20191111/FEEL/')
    process.set('isExecutable','false')
    plane=root.find('.//di:BPMNPlane',NS)
    shapes={e.attrib['bpmnElement']:e for e in plane.findall('di:BPMNShape',NS)}
    gateways={g['bpmn_id']:g for g in data['gateways']}
    guards={};pages=[]
    with PdfPages(OUT/'decision_blocks.pdf') as pdf:
        for g in data['gateways']:
            node=nodes[g['bpmn_id']];node.set('name',g['id'])
            doc=ET.Element(f'{{{BPMN}}}documentation');node.insert(0,doc)
            if g['kind']=='merge':doc.text='XOR merge; one outgoing flow; no branch choice or classifier.';continue
            branches=g['branches'];labels={fid:branches[fid]+' -> '+(gateways[flows[fid].attrib['targetRef']]['id'] if flows[fid].attrib['targetRef'] in gateways else (nodes[flows[fid].attrib['targetRef']].attrib.get('name') or nodes[flows[fid].attrib['targetRef']].tag.split('}')[-1])) for fid in g['outgoing']}
            for fid in g['outgoing']:
                condition=feel_guard(g['leaves'],fid);guards[fid]=condition
                flows[fid].set('name',branches[fid])
                expression=ET.SubElement(flows[fid],f'{{{BPMN}}}conditionExpression',{'{http://www.w3.org/2001/XMLSchema-instance}type':'bpmn:tFormalExpression','language':'https://www.omg.org/spec/DMN/20191111/FEEL/'})
                expression.text=condition
            note=(f'{g["id"]} | learned decision block\nn={g["observations"]}; test n={g["test"]}\n'
                  f'Accuracy {g["accuracy"]:.3f}; majority {g["majority_accuracy"]:.3f}\n'
                  f'Macro-F1 {g["macro_f1"]:.3f}; depth {g["depth"]}\n'
                  f'Inputs: {", ".join(short_feature(x) for x in g["used_features"]) or "constant majority"}\n'
                  f'Rules and support: decision_blocks.pdf / {g["id"]}')
            if g['never_predicted_branches']:note+='\nWarning: unpredicted '+','.join(branches[f] for f in g['never_predicted_branches'])
            doc.text=note+'\nStatistical guards; original structural quality does not measure guarded execution.'
            annotation=ET.SubElement(process,f'{{{BPMN}}}textAnnotation',{'id':'note_'+g['id']})
            ET.SubElement(annotation,f'{{{BPMN}}}text').text=annotation_text(g)
            association=ET.SubElement(process,f'{{{BPMN}}}association',{'id':'assoc_'+g['id'],'sourceRef':g['bpmn_id'],'targetRef':'note_'+g['id']})
            bounds=shapes[g['bpmn_id']].find('dc:Bounds',NS).attrib
            x=float(bounds['x'])+float(bounds['width'])+90;y=float(bounds['y'])-45
            shape=ET.SubElement(plane,f'{{{NS["di"]}}}BPMNShape',{'id':'shape_note_'+g['id'],'bpmnElement':'note_'+g['id']})
            ET.SubElement(shape,f'{{{NS["dc"]}}}Bounds',{'x':str(x),'y':str(y),'width':'440','height':'150'})
            edge=ET.SubElement(plane,f'{{{NS["di"]}}}BPMNEdge',{'id':'edge_note_'+g['id'],'bpmnElement':'assoc_'+g['id']})
            for a,b in [(float(bounds['x'])+float(bounds['width']),float(bounds['y'])+float(bounds['height'])/2),(x,y+65)]:
                ET.SubElement(edge,f'{{{NS["edge"]}}}waypoint',{'x':str(a),'y':str(b)})
            fig=plt.figure(figsize=(11.69,8.27),facecolor='white')
            fig.text(.06,.945,f'{g["id"]} | XOR decision block',fontsize=20,weight='bold',color='#183754')
            fig.text(.06,.906,f'All-case aligned observations: {g["observations"]:,} | Train: {g["train"]:,} | Held-out test: {g["test"]:,}',fontsize=11)
            fig.text(.06,.875,f'Test accuracy {g["accuracy"]:.3f} | Majority baseline {g["majority_accuracy"]:.3f} | Balanced accuracy {g["balanced_accuracy"]:.3f} | Macro-F1 {g["macro_f1"]:.3f}',fontsize=10)
            y=.82
            for fid,label in labels.items():
                count=g['branch_counts'].get(fid,0)
                fig.text(.07,y,f'{label} | aligned support {count:,}',fontsize=10);y-=.027
            fig.text(.06,y-.025,'Learned rules (training cases only; depth <= 3; minimum leaf size 50)',fontsize=11,weight='bold')
            y-=.065
            for leaf in g['leaves']:
                rule=leaf_text(leaf,branches)+f' [train n={leaf["samples"]:,}]'
                wrapped=textwrap.wrap(rule,width=118)
                fig.text(.07,y,'\n'.join(wrapped),fontsize=9,family='monospace',va='top')
                y-=.028*len(wrapped)+.016
            absent=', '.join(branches[f] for f in g['never_predicted_branches']) or 'none'
            fig.text(.06,.16,f'Branches never predicted by this tree: {absent}',fontsize=10,color='#9a421c')
            fig.text(.06,.115,'c. = case input at start; e. = last synchronized event input. Missing numeric value = -1; explicit *_known flags.',fontsize=9)
            fig.text(.06,.088,'Inputs update after synchronous moves only. One optimal alignment per variant; alternative alignments may change decisions.',fontsize=9)
            fig.text(.06,.061,'Statistical associations; not bank policy. Structural replay coverage 80.45% is measured without these guards.',fontsize=9)
            pdf.savefig(fig)
            page=OUT/'blocks'/f'{g["id"]}.pdf';page.parent.mkdir(exist_ok=True);fig.savefig(page)
            fig.savefig(page.with_suffix('.png'),dpi=110)
            plt.close(fig);pages.append(page)
    print('Rendered 16 PDF decision blocks',flush=True)
    ET.indent(root,space='  ');ET.ElementTree(root).write(OUT/'decision_model.bpmn',encoding='utf-8',xml_declaration=True)
    (OUT/'guards.json').write_text(json.dumps(guards,indent=2)+'\n',encoding='utf-8')
    # BPMN-shaped vector overview with linked statistical decision blocks.
    dot=graphviz.Digraph('decision_bpmn',graph_attr={'rankdir':'TB','bgcolor':'white','nodesep':'.45','ranksep':'.65','splines':'polyline','margin':'0'},
        node_attr={'fontname':'Arial','fontsize':'14','margin':'.16,.10'},edge_attr={'fontname':'Arial','fontsize':'11'})
    for nid,node in nodes.items():
        tag=node.tag.split('}')[-1]
        if tag not in ('task','startEvent','endEvent','exclusiveGateway','parallelGateway'):continue
        if tag=='task':dot.node(nid,node.attrib.get('name',''),shape='box',style='rounded,filled',fillcolor='#eef4f8')
        elif tag in ('startEvent','endEvent'):dot.node(nid,'',shape='doublecircle' if tag=='endEvent' else 'circle',width='.25')
        else:
            label='+' if tag=='parallelGateway' else gateways[nid]['id']+'\nX'
            dot.node(nid,label,shape='diamond',width='.7',height='.7')
            if nid in gateways and gateways[nid]['kind']=='split':
                g=gateways[nid]
                dot.node('block_'+g['id'],annotation_text(g)+'\n',shape='note',fontsize='12',color='#27777a',fontcolor='#19585c',align='left')
                dot.edge(nid,'block_'+g['id'],style='dashed',arrowhead='none',constraint='false')
                with dot.subgraph() as rank:
                    rank.attr(rank='same');rank.node(nid);rank.node('block_'+g['id'])
    for fid,flow in flows.items():dot.edge(flow.attrib['sourceRef'],flow.attrib['targetRef'],flow.attrib.get('name',''))
    for fmt in ('pdf','svg','png'):dot.render(str(OUT/'decision_bpmn'),format=fmt,cleanup=True)
    print('Rendered BPMN overview',flush=True)
    # Use the same non-overlapping Graphviz layout for native BPMN DI, including
    # the annotation boxes. Existing horizontal positions would collide with notes.
    layout=json.loads(dot.pipe(format='json').decode('utf-8'))
    graph_height=float(layout['bb'].split(',')[3]);objects={o['_gvid']:o for o in layout['objects']}
    coordinates={}
    for obj in objects.values():
        if 'pos' not in obj:continue
        nid=obj['name'];nid='note_'+nid[6:] if nid.startswith('block_') else nid
        x,y=map(float,obj['pos'].split(','));w=float(obj['width'])*72;h=float(obj['height'])*72
        coordinates[nid]=(x-w/2,graph_height-y-h/2,w,h)
    for shape in plane.findall('di:BPMNShape',NS):
        nid=shape.attrib['bpmnElement']
        if nid in coordinates:
            x,y,w,h=coordinates[nid];shape.find('dc:Bounds',NS).attrib.update(x=str(x),y=str(y),width=str(w),height=str(h))
        for label in shape.findall('di:BPMNLabel',NS):shape.remove(label)
    edge_geometry=defaultdict(list)
    for edge in layout['edges']:
        tail=objects[edge['tail']]['name'];head=objects[edge['head']]['name']
        points=[];ending=None
        for token in edge['pos'].split():
            parts=token.split(',')
            if parts[0]=='e':ending=(float(parts[1]),graph_height-float(parts[2]))
            elif parts[0]!='s':points.append((float(parts[0]),graph_height-float(parts[1])))
        if ending:points.append(ending)
        edge_geometry[(tail,head)].append(points)
    for edge in plane.findall('di:BPMNEdge',NS):
        eid=edge.attrib['bpmnElement']
        if eid in flows:pair=(flows[eid].attrib['sourceRef'],flows[eid].attrib['targetRef'])
        elif eid.startswith('assoc_'):
            key=eid[6:];g=next(g for g in data['gateways'] if g['id']==key);pair=(g['bpmn_id'],'block_'+key)
        else:continue
        points=edge_geometry[pair].pop(0)
        for child in list(edge):edge.remove(child)
        for x,y in points:ET.SubElement(edge,f'{{{NS["edge"]}}}waypoint',{'x':str(x),'y':str(y)})
    ET.indent(root,space='  ');ET.ElementTree(root).write(OUT/'decision_model.bpmn',encoding='utf-8',xml_declaration=True)
    # All readable rules are also native BPMN text annotations at their XORs.
    records={g['id']:g for g in data['gateways'] if g['kind']=='split'}
    for key,g in records.items():
        tree=graphviz.Digraph(key,graph_attr={'rankdir':'TB','bgcolor':'white'},node_attr={'fontname':'Arial','fontsize':'11','shape':'box','style':'rounded,filled','fillcolor':'#eef4f8'},edge_attr={'fontname':'Arial','fontsize':'10'})
        prefixes={}
        for leaf in g['leaves']:
            for depth in range(len(leaf['predicates'])+1):
                prefix=tuple((p['feature'],p['op'],p['threshold']) for p in leaf['predicates'][:depth])
                if prefix in prefixes:continue
                nid='n'+str(len(prefixes));prefixes[prefix]=nid
                if depth==len(leaf['predicates']):tree.node(nid,f'{g["branches"][leaf["class"]]}\ntrain n={leaf["samples"]:,}',fillcolor='#d5ece6')
                else:
                    p=leaf['predicates'][depth]
                    tree.node(nid,short_feature(p['feature'])+'\n'+format(p['threshold'],'.8g'))
                if depth:tree.edge(prefixes[prefix[:-1]],nid,'yes (<=)' if prefix[-1][1]=='<=' else 'no (>)')
        (OUT/'trees').mkdir(exist_ok=True)
        for fmt in ('pdf','svg','png'):tree.render(str(OUT/'trees'/key),format=fmt,cleanup=True)
        print(f'Rendered tree {key}',flush=True)
    overview=['<h1>BPIC-17: Decision Mining</h1><p>Alle 16 XOR-Splits; Regeln aus Trainingsfällen, Kennzahlen aus getrennten Testfällen. XOR-Merges führen nur zusammen.</p>',
        '<p><a href="decision_blocks.pdf">Alle Entscheidungsblöcke als PDF</a> · <a href="decision_bpmn.pdf">BPMN-Übersicht als PDF</a> · <a href="decision_model.bpmn" download>BPMN mit Bedingungen</a> · <a href="viewer.html">Interaktives BPMN</a></p>',
        f'<p><strong>Harte Guards: {sum(v["guarded_fitting_cases"] for v in data["guarded_replay"].values()):,} / {data["cases"]:,} Fälle vollständig replaybar. Im Test: {data["guarded_replay"]["test"]["guarded_fitting_cases"]:,} / {data["guarded_replay"]["test"]["cases"]:,} ({100*data["guarded_replay"]["test"]["guarded_fitting_cases"]/data["guarded_replay"]["test"]["cases"]:.2f} %).</strong> Die 80,45 % des bisherigen Modells gelten ohne diese Guards. Seltene Zweige können vom Baum nie vorhergesagt werden. Die Regeln sind für Analyse und Diskussion; Simulation benötigt weitere Validierung.</p>']
    for key,g in records.items():
        overview.append(f'<section id="{key}"><h2>{key}</h2><p>n={g["observations"]:,}; Test-Accuracy {g["accuracy"]:.3f}; Mehrheitsbaseline {g["majority_accuracy"]:.3f}; Macro-F1 {g["macro_f1"]:.3f}</p>')
        overview.append(f'<a href="trees/{key}.pdf"><img src="trees/{key}.svg" style="width:100%;max-height:520px" alt="Entscheidungsbaum {key}"></a>')
        for fid in g['outgoing']:
            overview.append(f'<h3>{g["branches"][fid]} · n={g["branch_counts"].get(fid,0):,}</h3><pre>{html.escape(guards[fid])}</pre>')
        overview.append(f'<a href="blocks/{key}.pdf">Entscheidungsblock {key}</a></section>')
    page='<!doctype html><meta charset="utf-8"><title>BPIC-17 Decision Mining</title><style>body{font:16px system-ui;max-width:1050px;margin:35px auto;padding:0 20px;color:#17324a}section{border-top:1px solid #ccc;padding:20px 0}pre{white-space:pre-wrap;font-size:13px;background:#f1f5f7;padding:12px}a{color:#176b70}</style>'+''.join(overview)
    (OUT/'index.html').write_text(page,encoding='utf-8')
    viewer='''<!doctype html><meta charset="utf-8"><title>BPIC-17 BPMN mit Decision Mining</title>
<link rel="stylesheet" href="/.tools/bpmn-js/dist/assets/diagram-js.css"><link rel="stylesheet" href="/.tools/bpmn-js/dist/assets/bpmn-js.css"><link rel="stylesheet" href="/.tools/bpmn-js/dist/assets/bpmn-font/css/bpmn-embedded.css">
<style>body{margin:0;font:14px system-ui}header{padding:12px;background:#16374e;color:white}a{color:#80dfdc}#canvas{height:calc(100vh - 90px);width:73vw}#details{position:absolute;right:0;top:65px;width:25vw;height:calc(100vh - 90px);overflow:auto;white-space:pre-wrap;padding:10px;box-sizing:border-box;background:#f0f5f7}button{margin-left:8px}</style>
<header>BPIC-17 · Gelernte XOR-Bedingungen · <a href="index.html">Regeln und Prüfergebnisse</a><select id="jump" aria-label="Entscheidung auswählen"></select><button onclick="modeler.get('canvas').zoom('fit-viewport')">Ganzes Modell</button><button onclick="modeler.get('canvas').zoom(modeler.get('canvas').zoom()*1.5)">+</button><button onclick="modeler.get('canvas').zoom(modeler.get('canvas').zoom()/1.5)">−</button><span id="state"> Lädt …</span></header><div id="canvas"></div><aside id="details">Klicke ein XOR-Gateway oder einen ausgehenden Pfeil. Gelernte Regeln sind statistische Zusammenhänge; die Strukturkennzahlen gelten ohne Guards.</aside>
<script src="/.tools/bpmn-js/dist/bpmn-modeler.production.min.js"></script><script>
const modeler=new BpmnJS({container:'#canvas'});window.modeler=modeler;
const decisions=DECISION_RECORDS;const jump=document.getElementById('jump');
for(const g of decisions){const o=document.createElement('option');o.value=g.id;o.textContent=g.id;jump.append(o);}
function humanPredicate(p){let n=p.feature.replace('case_','Fall.').replace('event_','Angebot.');if(n.includes('=')&&p.threshold>=0&&p.threshold<1){const i=n.indexOf('=');return n.slice(0,i)+(p.op==='<='?' ≠ ':' = ')+n.slice(i+1);}return n+' '+p.op+' '+Number(p.threshold.toFixed(4));}
function focusDecision(id){const g=decisions.find(g=>g.id===id);const e=modeler.get('elementRegistry').get(g.bpmn_id);const note=modeler.get('elementRegistry').get('note_'+id);const left=Math.min(e.x,note.x)-80;const top=Math.min(e.y,note.y)-80;modeler.get('canvas').viewbox({x:left,y:top,width:Math.max(900,Math.max(e.x+e.width,note.x+note.width)-left+80),height:Math.max(650,Math.max(e.y+e.height,note.y+note.height)-top+160)});jump.value=id;let text=g.id+' · Gelernter Entscheidungsblock\\n\\nTest-Accuracy '+g.accuracy.toFixed(3)+'; Mehrheit '+g.majority_accuracy.toFixed(3)+'; Macro-F1 '+g.macro_f1.toFixed(3)+'\\n\\nStatistische Regeln. Harte Guards: 10,19 % vollständige Testfallabdeckung.\\n\\n';for(const leaf of g.leaves){text+=g.branches[leaf.class]+': '+(leaf.predicates.map(humanPredicate).join(' UND ')||'immer')+'\\nTraining n='+leaf.samples+'\\n\\n';}text+='Fehlend: numerisch -1; *_known zeigt bekannte Werte. Für den formalen Ausdruck einen Pfeil anklicken.';document.getElementById('details').textContent=text;}
jump.onchange=()=>focusDecision(jump.value);
modeler.on('element.click',e=>{const b=e.element.businessObject;const docs=(b.documentation||[]).map(x=>x.text).join('\\n');document.getElementById('details').textContent=(b.name||b.id)+'\\n\\n'+docs+'\\n\\n'+(b.conditionExpression?b.conditionExpression.body:'');});
fetch('decision_model.bpmn').then(r=>r.text()).then(async xml=>{const r=await modeler.importXML(xml);focusDecision('D03');document.getElementById('state').textContent='Geladen · '+r.warnings.length+' Hinweise';window.bpmnReady=true;window.bpmnWarnings=r.warnings.map(x=>x.message);}).catch(e=>document.getElementById('state').textContent=e.message);
</script>'''
    viewer=viewer.replace('DECISION_RECORDS',json.dumps(list(records.values()),ensure_ascii=False))
    (OUT/'viewer.html').write_text(viewer,encoding='utf-8')
    rows=['\\begin{table}[t]','\\centering','\\caption{Alignment-based decision mining~\\cite{deleoni2013dataaware}: held-out results; case-wise 70/30 split, seed 20261018; fixed full-log control-flow model.}','\\label{tab:decision-mining}','\\begin{tabular}{lrrrr}','\\hline','XOR & Test $n$ & Accuracy & Majority & Macro-F1 \\\\','\\hline']
    for g in records.values():rows.append(f'{g["id"]} & {g["test"]:,} & {g["accuracy"]:.3f} & {g["majority_accuracy"]:.3f} & {g["macro_f1"]:.3f} \\\\')
    rows+=['\\hline','\\end{tabular}','\\end{table}']
    (OUT/'decision_metrics.tex').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    coverage=['\\begin{table}[t]','\\centering','\\caption{Exact whole-case replay of the same BPMN structure, before and after enforcing learned guards.}','\\label{tab:guarded-coverage}','\\begin{tabular}{lrrr}','\\hline','Cases & $n$ & Structure (\\%) & Guards (\\%) \\\\','\\hline']
    for title,values in [('Train',data['guarded_replay']['train']),('Test',data['guarded_replay']['test']),
        ('All',{k:sum(v[k] for v in data['guarded_replay'].values()) for k in ('cases','structural_fitting_cases','guarded_fitting_cases')})]:
        coverage.append(f'{title} & {values["cases"]:,} & {100*values["structural_fitting_cases"]/values["cases"]:.2f} & {100*values["guarded_fitting_cases"]/values["cases"]:.2f} \\\\')
    coverage+=['\\hline','\\end{tabular}','\\end{table}']
    (OUT/'guarded_coverage.tex').write_text('\n'.join(coverage)+'\n',encoding='utf-8')
    appendix=['% Selected factual assets; author-written interpretation belongs in the main report.',
        '\\clearpage','\\newgeometry{layoutwidth=420mm,layoutheight=297mm,margin=15mm,headheight=15pt,headsep=6mm,footskip=8mm}',
        '\\setlength{\\paperwidth}{420mm}','\\setlength{\\paperheight}{297mm}','\\pdfpagewidth=\\paperwidth','\\pdfpageheight=\\paperheight','\\onecolumn']
    svg=ET.parse(OUT/'decision_bpmn.svg').getroot();width,height=map(float,svg.attrib['viewBox'].split()[2:])
    import math
    max_height=max(v[3] for v in coordinates.values())
    overlap=max(120,math.ceil(max_height)+20)
    step=820-overlap
    if step<=0:raise ValueError('Decision block too tall for readable report panels')
    panels=max(1,math.ceil((height-820)/step)+1)
    for i in range(panels):
        top=height-i*step;bottom=max(0,top-820)
        if i:appendix.append('\\clearpage')
        appendix.extend([f'\\subsection{{BPMN with Decision Blocks: Panel {i+1}/{panels}}}',
            '\\begin{figure}[h!]','\\centering',
            f'\\includegraphics[viewport=0 {bottom:.3f} {width:.3f} {top:.3f},clip,width=\\textwidth,height=0.87\\textheight,keepaspectratio]{{figures/decision_bpmn.pdf}}',
            f'\\caption{{XOR splits D01--D16: learned decision blocks; merges M01--M16: no branch choice. Overlapping vector panel {i+1}/{panels}. Experimental hard guards: 3,277/31,509 fitting cases; original unguarded structure: 25,350/31,509.}}',
            '\\end{figure}'])
    appendix.extend(['\\clearpage','\\newgeometry{layoutwidth=297mm,layoutheight=210mm,margin=12mm,headheight=15pt,headsep=5mm,footskip=7mm}',
        '\\setlength{\\paperwidth}{297mm}','\\setlength{\\paperheight}{210mm}','\\pdfpagewidth=\\paperwidth','\\pdfpageheight=\\paperheight','\\onecolumn'])
    for i,key in enumerate(records):
        if i:appendix.append('\\clearpage')
        appendix.extend([f'\\subsection{{Decision Block {key}}}',f'\\includegraphics[width=\\textwidth,height=0.94\\textheight,keepaspectratio]{{figures/decision_blocks/{key}.pdf}}'])
    (OUT/'decision_appendix.tex').write_text('\n'.join(appendix)+'\n',encoding='utf-8')
    annotation_audit={'source_sha256':sha(OUT/'decision_mining.json'),'panels':panels,'panel_height':820,
        'panel_step':step,'panel_overlap':overlap,'max_shape_height':max_height,
        'splits_with_visible_rules':len(records),'original_leaf_paths':sum(len(g['leaves']) for g in records.values()),
        'compact_rule_paths':sum(len(compact_rules(g['leaves'])) for g in records.values()),
        'display_implementation_sha256':sha(ROOT/'src/decision_display.py')}
    (OUT/'annotation_audit.json').write_text(json.dumps(annotation_audit,indent=2)+'\n',encoding='utf-8')
    manifest={'source_sha256':sha(OUT/'decision_mining.json'),'artifacts':{str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('presentation_manifest.json','verification.json','artifact_verification.json') and 'observations' not in p.parts}}
    (OUT/'presentation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Rendered {len(records)} decision blocks, all {len(data["gateways"])} XOR nodes annotated',flush=True)

if __name__=='__main__':main()
