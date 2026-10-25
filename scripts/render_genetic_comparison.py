"""Compare the completed Genetic trial with existing models on the same log."""
import sys,json,csv,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.runtime import configure_runtime
configure_runtime()
from src.genetic_miner import DEFAULT_SEED
OUT=ROOT/'results/genetic'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    import pm4py
    from src.simplicity import model_size,extended_cardoso
    baseline=json.loads((ROOT/'results/tables/quality_metrics.json').read_text())
    final=json.loads((ROOT/'results/refinement/final_metrics.json').read_text())
    path=OUT/f'seed_{DEFAULT_SEED}/manifest.json';genetic=json.loads(path.read_text())
    if genetic['status']!='ok':raise ValueError('Genetic experiment is not complete; no partial scores compared')
    assert genetic['input']['identity']['input_cache_sha256']==baseline['input_cache_sha256']==final['input_cache_sha256']
    rows=[]
    for key,label in [('inductive_miner','IM'),('heuristics_miner','HM')]:
        jobs=baseline['models'][key];token=jobs['token'];metrics=token['fitness']
        net,im,fm=pm4py.read_pnml(str(ROOT/f'results/models/{key}.pnml'))
        rows.append({'model':label,'training_cases':31509,'evaluation_cases':31509,'token_fitness':metrics['log_fitness'],
            'token_fitting_percentage':metrics['perc_fit_traces'],'token_precision':jobs['token_precision']['precision'],
            'generalization':token['generalization'],'simplicity':jobs['structure']['simplicity_arc_degree'],
            'nodes':model_size(net)['nodes'],'cardoso':extended_cardoso(net),
            'exact_case_coverage':100 if key=='inductive_miner' else None,
            'sound':jobs['structure']['reachability'].get('sound',False),'structure_status':jobs['structure']['reachability']['status']})
    m=genetic['metrics'];coverage=m['exact_coverage']
    rows.append({'model':'Genetic','training_cases':31509,'evaluation_cases':31509,'token_fitness':m['token_fitness']['log_fitness'],
        'token_fitting_percentage':m['token_fitness']['perc_fit_traces'],'token_precision':m['token_precision'],
        'generalization':m['generalization'],'simplicity':m['arc_degree_simplicity'],'nodes':m['size']['nodes'],
        'cardoso':m['extended_cardoso'],'exact_case_coverage':coverage.get('fitting_percentage'),
        'sound':m['reachability'].get('sound',False),'structure_status':m['reachability']['status']})
    m=final['metrics']
    rows.append({'model':'Refined IMf','training_cases':final['selected_candidate']['training_cases'],'evaluation_cases':31509,
        'token_fitness':m['token_fitness']['log_fitness'],'token_fitting_percentage':m['token_fitness']['perc_fit_traces'],
        'token_precision':m['token_precision'],'generalization':m['generalization'],'simplicity':m['simplicity_arc_degree'],
        'nodes':m['size_own']['nodes'],'cardoso':m['cardoso_own'],'exact_case_coverage':final['coverage']['fitting_percentage'],'sound':True,'structure_status':'ok'})
    record={'input_cache_sha256':baseline['input_cache_sha256'],'genetic_manifest_sha256':sha(path),'rows':rows,
        'notes':['Same full completion evaluation log, 31,509 cases; refined training set differs and is explicit.',
            'Token-based scores do not establish soundness or exact case replay; see the explicit sound field.',
            'A single small seeded Genetic run is exploratory; no globally best model is claimed.',
            'Genetic net is provably unbounded (PM4Py witness crosscheck). Exact whole-case coverage is not enumerated; 0% token fitting is heuristic.',
            'The original duplicate-ID export was corrected from its intact source graph; native objective reproduced exactly. Invalid initial scores are excluded.']}
    (OUT/'comparison.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    with (OUT/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    md=['# Third discovery experiment: native PM4Py Genetic Miner','',
        f'Genetic seed: {genetic["seed"]}; population: {genetic["parameters"]["population_size"]}; actual generations: {genetic["evaluated_generations"]}/{genetic["parameters"]["generations"]}; native objective: {genetic["native_best_objective"]:.6f}.','',
        '| Model | Train cases | Token fitness | Token fitting % | Token precision | Generalization | Arc simplicity | Nodes | Cardoso | Exact coverage % | Sound | State space |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for r in rows:
        exact='not enumerated' if r['exact_case_coverage'] is None else f'{r["exact_case_coverage"]:.4f}'
        md.append(f'| {r["model"]} | {r["training_cases"]} | {r["token_fitness"]:.4f} | {r["token_fitting_percentage"]:.2f} | {r["token_precision"]:.4f} | {r["generalization"]:.4f} | {r["simplicity"]:.4f} | {r["nodes"]} | {r["cardoso"]} | {exact} | {r["sound"]} | {r["structure_status"]} |')
    md+=['',*record['notes'],'','HM exact-replay upper bound: 1.3044%; this is not an observed fitting percentage.',
        'The refined IMf row describes its original unguarded structure; hard-guard test coverage remains 10.19%.',
        '', '[Parameters and reasons](../../docs/MINER_PARAMETERS.md) | [Design choices](../../docs/DESIGN_DECISIONS.md)']
    (OUT/'comparison.md').write_text('\n'.join(md)+'\n',encoding='utf-8',newline='\n')
    tex=[r'\begin{table}[h!]',r'\centering',r'\small',r'\begin{tabular}{lrrrrrrc}',r'\hline',r'Model & Train $n$ & Fitness & Precision & Gen. & Simp. & Exact (\%) & Sound \\',r'\hline']
    for r in rows:
        exact='--' if r['exact_case_coverage'] is None else f'{r["exact_case_coverage"]:.2f}'
        tex.append(f'{r["model"]} & {r["training_cases"]:,} & {r["token_fitness"]:.4f} & {r["token_precision"]:.4f} & {r["generalization"]:.4f} & {r["simplicity"]:.4f} & {exact} & {str(r['sound'])} '+r'\\')
    tex.extend([r'\hline',r'\end{tabular}',r'\caption{Full completion-log evaluation, 31,509 cases; token-based scores; exact case replay reported separately. Genetic Miner: native PM4Py CLASSIC, exploratory seeded budget~\cite{vdaalst2005genetic}. HM and Genetic: certified unbounded; exact coverage not enumerated (--).}',r'\end{table}'])
    (OUT/'comparison.tex').write_text('\n'.join(tex)+'\n',encoding='utf-8',newline='\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(11.7,8.3),layout='constrained')
    colors=['#24668d','#a8743b','#298173','#754c8a']
    for ax,key,title in zip(axes.flat,('token_fitness','token_precision','generalization','simplicity'),
            ('Token replay fitness','Token-based ET precision','Token generalization','Arc-degree simplicity')):
        values=[r[key] for r in rows];ax.bar([r['model'] for r in rows],values,color=colors)
        ax.set(ylim=(0,1.13),title=title,ylabel='Score')
        for i,value in enumerate(values):ax.text(i,value+.025,f'{value:.4f}',ha='center',fontsize=10)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Same evaluation log; numeric scores require structure/coverage checks',fontsize=14)
    for fmt in ('pdf','png','svg'):fig.savefig(OUT/f'comparison.{fmt}',dpi=130)
    plt.close(fig)
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()
