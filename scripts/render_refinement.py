"""Factual refinement comparisons and literature provenance; results/ only."""
import csv
import json
from pathlib import Path
from scripts.refine_model import ROOT, OUT, CACHE, sha, write
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    final=json.loads((OUT/'final_metrics.json').read_text())
    assert final['status']=='ok'
    baseline=json.loads((ROOT/'results/tables/quality_metrics.json').read_text())['models']
    raw=json.loads((ROOT/'results/tables/raw_log_statistics.json').read_text())
    data=json.loads(CACHE.read_text())
    multi=sum(t['activities'].count('O_Create Offer')>1 for t in data['traces'])
    comparison={'input_cache_sha256':sha(CACHE),'own_mean_case_days':raw['case_duration']['days']['mean'],
        'own_multiple_offer_cases':multi,'own_multiple_offer_percentage':100*multi/len(data['traces']),
        'external_results':[
        {'title':'Stairway to Value','authors':'Rodrigues et al.','year':2017,'pages':[3,6,7,8,9],
         'url':'https://ais.win.tue.nl/bpi/2017/bpi2017_winner_academic.pdf',
         'reported_fitness':.9728,'reported_precision':.9872,'model_versions':19,
         'removed_cases':100,'remaining_cases':31409,'comparable_exact_case_replay_percentage':None,
         'scope':'Filtered cases; activity clustering used in model development; ProM replay and Align-ET; no direct numerical ranking against our completion projection'},
        {'title':'BPIC 2017: Density Analysis of the Interaction With Clients','authors':'Povalyaeva et al.','year':2017,'pages':[3,4],
         'url':'https://ais.win.tue.nl/bpi/2017/bpi2017_winner_student.pdf',
         'raw_cases':31509,'raw_events':1202267,'bpmn_software':'Celonis',
         'reported_comparable_quality_metrics':None,
         'scope':'BPMN structure as domain reference; application/offer perspectives; no matched quantitative conformance result used here'},
        {'title':'Process mining on the loan application process of a Dutch Financial Institute','authors':'Blevi, Delporte, Robbrecht','year':2017,'pages':[2,3],
         'url':'https://ais.win.tue.nl/bpi/2017/bpi2017_winner_professional.pdf',
         'reported_mean_case_days_approx':22,'reported_multiple_offer_percentage_approx':27,
         'scope':'Approximate performance/frequency results; agreement checks, not model-quality scores'}]}
    write(OUT/'literature_comparison.json',comparison)
    im=baseline['inductive_miner']
    metrics=final['metrics']
    rows=[('Exact complete-case replay (\\%)',100,final['coverage']['fitting_percentage']),
          ('Token replay fitness',im['token']['fitness']['log_fitness'],metrics['token_fitness']['log_fitness']),
          ('Token fitting cases (\\%)',im['token']['fitness']['perc_fit_traces'],metrics['token_fitness']['perc_fit_traces']),
          ('Token precision',im['token_precision']['precision'],metrics['token_precision']),
          ('Align-ET precision',im['alignment_precision']['precision'],metrics['alignment_precision']['precision']),
          ('Token generalization',im['token']['generalization'],metrics['generalization']),
          ('Arc-degree simplicity',im['structure']['simplicity_arc_degree'],metrics['simplicity_arc_degree']),
          ('Nodes',im['structure']['size_own']['nodes'],metrics['size_own']['nodes']),
          ('Arcs',im['structure']['size_own']['arcs'],metrics['size_own']['arcs']),
          ('Extended Cardoso',im['structure']['cardoso_own'],metrics['cardoso_own']),
          ('Extended Cyclomatic',im['structure']['reachability']['value'],metrics['reachability']['value'])]
    lines=['% Factual output; final_metrics.json SHA256 '+sha(OUT/'final_metrics.json'),
        r'\begin{table}[htbp]',r'\centering',r'\small',
        r'\caption{Refined model versus IM baseline: same 31,509 cases; exact case replay from the complete marking graph.}',
        r'\label{tab:refined-quality}',r'\begin{tabular}{@{}lrr@{}}',r'\toprule',r'Metric & IM & Refined \\',r'\midrule']
    def number(x):return f'{x:,}' if isinstance(x,int) else f'{x:.4f}'
    lines.extend(label+' & '+number(a)+' & '+number(b)+r' \\' for label,a,b in rows)
    lines.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}',''])
    (OUT/'refined_quality.tex').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    candidates={}
    for filename in ('candidates.json','focused_candidates.json'):
        candidates.update(json.loads((OUT/filename).read_text())['candidates'])
    with (OUT/'iteration_metrics.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n')
        writer.writerow(['candidate','training_cases','noise_threshold','exact_fitting_cases','exact_fitting_percentage','exact_prefix_precision','excluded_weighted_prefixes','nodes','arcs','cardoso'])
        for key,v in candidates.items():writer.writerow([key,v.get('training_cases',31509),v['noise_threshold'],v['coverage']['fitting_cases'],v['coverage']['fitting_percentage'],v['exact_prefix_precision']['value'],v['exact_prefix_precision']['excluded_weighted_prefixes'],v['size']['nodes'],v['size']['arcs'],v['cardoso']])
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(8,4.6),layout='constrained')
    ax.axvspan(78,82,color='#dceddf',label='Declared target: 78-82%')
    for family,label,color in [('imf_','IMf: full discovery log','#547e9d'),('frequent_','IMf: frequent-variant training subset','#c48437')]:
        values=[v for k,v in candidates.items() if k.startswith(family)]
        ax.scatter([v['coverage']['fitting_percentage'] for v in values],[v['exact_prefix_precision']['value'] for v in values],color=color,s=35,alpha=.8,label=label)
    x,y=final['coverage']['fitting_percentage'],final['selected_candidate']['exact_prefix_precision']['value']
    ax.scatter([x],[y],s=180,marker='*',color='#1d653d',edgecolor='white',zorder=5,label='Selected BPMN')
    ax.annotate(f'Selected: {x:.2f}%, {y:.3f}',(x,y),xytext=(-45,28),textcoords='offset points',arrowprops={'arrowstyle':'-','color':'#1d653d'})
    ax.set(xlabel='Exact complete-case replay (%)',ylabel='Exact prefix escaping-edge precision',xlim=(-2,103),ylim=(0,1),title=f'{len(candidates)} refinement candidates | evaluation on all 31,509 cases')
    ax.grid(alpha=.2);ax.legend(loc='lower left',fontsize=8,frameon=False)
    for ext in ('pdf','png','svg'):fig.savefig(OUT/f'refinement_tradeoff.{ext}',dpi=180,bbox_inches='tight',facecolor='white')
    plt.close(fig)
    lines=['# Refinement summary (Assignment 3.3.3)','',f"Selected: `{final['selected']}`",'',
           f"Exact replay: **{final['coverage']['fitting_cases']:,}/{final['coverage']['cases']:,} cases ({x:.4f}%)**.",
           f"Discovery training: {final['selected_candidate'].get('training_cases',31509):,} cases; evaluation: all 31,509 cases.",'',
           '| Metric | IM baseline | Refined |','|---|---:|---:|']
    lines.extend('| '+label.replace('\\%','%')+' | '+number(a)+' | '+number(b)+' |' for label,a,b in rows)
    ap=metrics['alignment_precision']
    lines+=['',f"Align-ET excludes {ap['weighted_unfit_prefixes']:,} weighted nonempty prefixes; denominator 443,797.",
            'Token replay is heuristic; its fitting-case fraction and fitness are separate from exact language acceptance. PM4Py defaults may ignore activities missing from the model.',
            'Generalization is the PM4Py frequency heuristic on the full evaluation log, not held-out predictive validation.','',
            '## Published BPIC-17 results','',
            '| Source | Reported result | Comparability |','|---|---|---|',
            '| [Rodrigues et al., academic winner](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_academic.pdf), PDF pp. 3, 7-9 | Fitness 97.28%; precision 98.72%; 19 model versions | 100 cases removed; activity abstraction; different log/model representation; no exact whole-case coverage comparison |',
            '| [Povalyaeva et al., student winner](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_student.pdf), PDF p. 3 | BPMN 2.0 using Celonis; raw 31,509 cases and 1,202,267 events | Structural/domain comparison; no matched four-dimension quality score used |',
            f"| [Blevi et al., KPMG](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_professional.pdf), PDF pp. 2-3 | Approximately 22 days and 27% multiple-offer cases | Our raw mean {comparison['own_mean_case_days_approx'] if 'own_mean_case_days_approx' in comparison else comparison['own_mean_case_days']:.3f} days; multiple-offer cases {comparison['own_multiple_offer_percentage_approx'] if 'own_multiple_offer_percentage_approx' in comparison else comparison['own_multiple_offer_percentage']:.3f}%; contextual check, not conformance |",'',
            '## Excluded activity labels','',', '.join('`'+a+'`' for a in final['omitted_activity_labels']),'',
            'All cases containing these labels remain in evaluation; no fitting subset is substituted. Rare paths and residual concurrency remain limitations. Additional duration/resource distributions and decision probabilities are required for a calibrated simulation.','']
    (OUT/'refinement_summary.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    literature_tex=[r'\begin{table}[h!]',r'\centering',r'\small',
        r'\caption{Published BPIC-17 results: differing filters and representations; contextual comparison.}',
        r'\label{tab:published-comparison}',r'\begin{tabular}{@{}p{0.21\textwidth}p{0.31\textwidth}p{0.41\textwidth}@{}}',
        r'\toprule',r'Source & Reported result & Scope \\',r'\midrule',
        r'Rodrigues et al.~\cite{rodrigues2017stairway} & Fitness 97.28\%; precision 98.72\%; 19 versions & 100 cases removed; activity abstraction; no matched exact-case replay score \\',
        r'Povalyaeva et al.~\cite{povalyaeva2017density} & Celonis BPMN 2.0; 31,509 raw cases & Structural reference; no matched quality score used \\',
        r'Blevi et al.~\cite{blevi2017kpmg} & About 22 days; 27\% multiple-offer cases & '+f"Own raw mean {comparison['own_mean_case_days']:.3f} days; multiple-offer cases {comparison['own_multiple_offer_percentage']:.3f}"+r'\% \\',
        r'\bottomrule',r'\end{tabular}',r'\end{table}','']
    (OUT/'literature_comparison.tex').write_text('\n'.join(literature_tex),encoding='utf-8',newline='\n')
    write(OUT/'presentation_manifest.json',{'metrics_sha256':sha(OUT/'final_metrics.json'),
        'baseline_quality_sha256':sha(ROOT/'results/tables/quality_metrics.json'),
        'artifacts':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name in ('refined_quality.tex','iteration_metrics.csv','refinement_summary.md','literature_comparison.json','literature_comparison.tex','refinement_tradeoff.pdf','refinement_tradeoff.png','refinement_tradeoff.svg')}})
    print('Rendered refinement comparison and literature provenance')


if __name__=='__main__':main()
