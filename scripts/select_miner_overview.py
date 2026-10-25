"""Explicitly select the factual miner configuration appendix for report/."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    folder=ROOT/'results/parameters';record=json.loads((folder/'miner_parameters.json').read_text())
    for path,digest in record['sources'].items():assert sha(ROOT/path)==digest,path
    source=folder/'miner_parameters.tex';target=ROOT/'report/sections/miner_parameters.tex'
    shutil.copyfile(source,target);assert sha(source)==sha(target)
    proof={'source_parameters_sha256':sha(folder/'miner_parameters.json'),'source':'results/parameters/miner_parameters.tex',
           'selected':'report/sections/miner_parameters.tex','sha256':sha(target)}
    (ROOT/'docs/miner_parameter_report_manifest.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Selected actual miner configuration appendix; no generated scientific rationale paragraphs')
if __name__=='__main__':main()
