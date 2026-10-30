"""Explicitly select audited factual Decision Mining assets for report/.

Ordinary mining/rendering never writes report/. Run this command deliberately,
then report/build.ps1. No scientific interpretation is generated.
"""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source=ROOT/'results/decision_mining';report=ROOT/'report'
    audit=json.loads((source/'verification.json').read_text())
    assert audit['status']=='ok' and audit['source_sha256']==sha(source/'decision_mining.json')
    rendered=json.loads((source/'presentation_manifest.json').read_text())
    assert rendered['source_sha256']==audit['source_sha256']
    for p,digest in rendered['artifacts'].items():assert sha(source/p)==digest,p
    copies={'decision_bpmn.pdf':'figures/decision_bpmn.pdf','decision_metrics.tex':'tables/decision_metrics.tex',
            'guarded_coverage.tex':'tables/guarded_coverage.tex','decision_appendix.tex':'sections/decision_appendix.tex'}
    splits=[g['id'] for g in json.loads((source/'decision_mining.json').read_text(encoding='utf-8'))['gateways'] if g['kind']=='split']
    copies.update({f'blocks/{key}.pdf':f'figures/decision_blocks/{key}.pdf' for key in splits})
    manifest={}
    for src,dest in copies.items():
        output=report/dest;output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/src,output)
        assert sha(source/src)==sha(output)
        manifest[dest]={'source':'results/decision_mining/'+src,'sha256':sha(output)}
    path=ROOT/'docs/decision_report_manifest.json';temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n');temporary.replace(path)
    print(f'Selected {len(copies)} audited factual report artifacts')
if __name__=='__main__':main()
