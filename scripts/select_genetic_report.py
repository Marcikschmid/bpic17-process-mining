"""Select only verified factual Genetic comparison/model artifacts for report/."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 folder=ROOT/'results/genetic/seed_20261025';record=json.loads((folder/'manifest.json').read_text())
 proof=json.loads((ROOT/'docs/genetic_verification.json').read_text())
 assert record['status']==proof['status']=='ok' and proof['manifest_sha256']==sha(folder/'manifest.json')
 comparison=json.loads((ROOT/'results/genetic/comparison.json').read_text())
 assert comparison['genetic_manifest_sha256']==sha(folder/'manifest.json')
 selected=[]
 for source,target in [('results/genetic/comparison.tex','report/tables/genetic_comparison.tex'),
  ('results/genetic/comparison.pdf','report/figures/genetic_comparison.pdf'),
  ('results/genetic/seed_20261025/figures/genetic_miner.pdf','report/figures/genetic_miner.pdf')]:
  shutil.copyfile(ROOT/source,ROOT/target);assert sha(ROOT/source)==sha(ROOT/target)
  selected.append({'source':source,'selected':target,'sha256':sha(ROOT/target)})
 (ROOT/'docs/genetic_report_manifest.json').write_text(json.dumps({'selected':selected},indent=2)+'\n',encoding='utf-8',newline='\n')
 print('Selected verified factual Genetic table, comparison plot and model; scientific narrative remains author work.')
if __name__=='__main__':main()
