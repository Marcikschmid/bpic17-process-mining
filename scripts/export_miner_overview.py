"""Export actual miner settings, explanations and factual appendix tables.

Reasons live in companion documentation; this command never writes report/.
"""
import sys,json,textwrap,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.runtime import configure_runtime
configure_runtime()
from src.discovery import INDUCTIVE_PARAMETERS,HEURISTICS_PARAMETERS
from src.genetic_miner import GENETIC_PARAMETERS,DEFAULT_SEED
OUT=ROOT/'results/parameters'

def row(name,value,meaning,reason,role):
    return {'parameter':name,'value':value,'meaning':meaning,'reason':reason,'role':role}

def catalogue():
    refined=json.loads((ROOT/'results/refinement/final_metrics.json').read_text())
    im=[
        row('noise_threshold',INDUCTIVE_PARAMETERS['noise_threshold'],'Relative Rauschschwelle; 0 aktiviert IM, positive Werte IMf. Kein Anteil entfernter Fälle.','0 als Vergleichsbasis ohne zusätzlichen Rauschfilter; im finalen Modell 0.03 nach dokumentierter Kandidatensuche.','Relative noise threshold'),
        row('multi_processing',INDUCTIVE_PARAMETERS['multi_processing'],'Parallele Ausführung des Miners. Kein fachlicher Filter.','False begrenzt Prozess-/Speicheraufwand und vereinfacht Fehlersuche. Kein Qualitätsoptimierungshebel.','Parallel execution'),
        row('disable_fallthroughs',INDUCTIVE_PARAMETERS['disable_fallthroughs'],'False erlaubt zusätzliche Rückfallstrategien, wenn kein strukturierter Cut gefunden wird.','Standardstrategien bleiben verfügbar. True lässt hier weiterhin Empty-Trace-/Flower-Fallback zu; es garantiert keine höhere Präzision.','Disable selected fall-throughs'),
        row('final noise_threshold',refined['selected_candidate']['noise_threshold'],'Rauschschwelle des gewählten IMf-Kandidaten, bei anderer Discovery-Trainingsmenge.','0.03 wurde in der Suche ausgewählt; kein Beweis einer generell optimalen 3-Prozent-Schwelle.','Selected IMf noise'),
        row('training_coverage',0.60,'Externer Frequenzfilter für das finale Modell; kein interner IM-Parameter.','Häufige Varianten als Discovery-Fokus. Tatsächlich 18,918 Fälle und 73 Varianten; Bewertung weiterhin auf allen 31,509 Fällen.','Frequent-variant training target'),
        row('target coverage band',[78,82],'Eigenes Auswahlband für ungefähr 80 Prozent vollständig replaybare Fälle.','Operationalisierung der Aufgabenanforderung; keine Datenbereinigung und kein vom Datensatz vorgegebener Grenzwert.','Exact whole-case target band (%)'),
    ]
    hm=[row('variant','CLASSIC','Verwendete Heuristics-Miner-Variante; Ausgabe wird in ein Petri-Netz umgewandelt.','Festgelegte Vergleichsbasis. Ein exportiertes Workflow-Netz ist noch kein Soundness-Nachweis.','Algorithm variant')]
    meanings={
        'dependency_thresh':('Mindest-Abhängigkeitsmaß für eine direkt folgende Relation.','0.5 ist die dokumentierte Baseline, nicht datenoptimiert. Höher ist strenger; seltene reale Pfade können entfallen.','Dependency threshold'),
        'and_measure_thresh':('Schwelle für die Interpretation benachbarter Relationen als Parallelität.','0.65 als Bibliotheksstandard. Höhere Werte erschweren AND-Erkennung; keine globale Monotonie der Qualitätswerte.','AND threshold'),
        'loop_length_two_thresh':('Schwelle zum Erkennen kurzer Schleifen wie A-B-A.','0.5 als Standard; kurze Wiederholungen sollen nicht durch reine Richtungsabhängigkeit verloren gehen.','Length-two loop threshold'),
        'min_act_count':('Absolute Mindestanzahl beobachteter Events pro Aktivität.','1 vermeidet eine zusätzliche absolute Häufigkeitsselektion. Andere HM-Filter gelten trotzdem.','Minimum activity count'),
        'min_dfg_occurrences':('Absolute Mindesthäufigkeit einer direkt folgenden Kante.','1 als permissive absolute Baseline; Dependency und relatives Pre-Cleaning können Kanten weiterhin entfernen.','Minimum DFG edge count'),
        'dfg_pre_cleaning_noise_thresh':('Relative DFG-Bereinigung vor der Abhängigkeitsberechnung.','0.05 als expliziter Standard. Bezieht sich auf lokale Kantenhäufigkeiten, nicht auf fünf Prozent gelöschte Fälle.','Relative DFG pre-cleaning'),
    }
    for key,(meaning,reason,role) in meanings.items():hm.append(row(key,HEURISTICS_PARAMETERS[key],meaning,reason,role))
    gm=[]
    gm_info={
        'population_size':('Anzahl konkurrierender Modelle je Generation.','10 entspricht dem offiziellen kleinen Beispiel und hält den Voll-Log-Versuch bezahlbar; Default 500 wäre deutlich teurer.','Population size'),
        'generations':('Obergrenze einschließlich der Anfangspopulation; native Frühstopps sind möglich.','6 gibt vorab maximal 60 Modellbewertungen in bis zu 6 Populationen vor. Explorationsbudget, keine Konvergenzgarantie.','Maximum generations'),
        'elitism_rate':('Anteil unverändert übernommener bester Individuen; Anzahl ist round(rate * population_size).','0.1 erhält bei Population 10 genau ein Modell. Default 0.01 ergäbe bei diesem kleinen Budget null Eliten.','Elitism fraction'),
        'crossover_rate':('Wahrscheinlichkeit zur Rekombination ausgewählter Eltern.','1.0 übernimmt den nativen Standard und kombiniert Eltern bei jeder entsprechenden Auswahl.','Crossover probability'),
        'mutation_rate':('Wahrscheinlichkeit je Input-/Outputeintrag, vorhandene Nachbarn neu zu partitionieren.','0.01 übernimmt den Standard; dies ist nicht ein Prozent beliebig neu eingefügter Kanten.','Partition mutation probability'),
        'elitism_min_sample':('Tatsächlich die Stichprobengröße der Eltern-Turnierauswahl; nicht die Zahl der Eliten.','2 hält bei Population 10 den Selektionsdruck moderat und ermöglicht mehr Elternvielfalt als der Default 5.','Parent tournament sample size'),
    }
    for key,(meaning,reason,role) in gm_info.items():gm.append(row(key,GENETIC_PARAMETERS[key],meaning,reason,role))
    gm.extend([
        row('random / numpy seed',DEFAULT_SEED,'Kontrolliert Python-random und NumPy-Zufall.','Fixiert den konkreten Versuch. Ein Seed belegt keine Robustheit über mehrere Suchläufe.','Random seed'),
        row('PYTHONHASHSEED',str(DEFAULT_SEED),'Fixiert Set-Reihenfolgen im separaten Python-Prozess.','Zusätzlich nötig, weil die Implementierung zufällig aus Set-basierten Pools zieht.','Python hash seed'),
        row('log_csv','evolution.csv','Protokolliert die nativen Fitnesswerte je Population.','Unterscheidet geplante und tatsächlich durchgeführte Generationen sowie das interne Ziel von externen Qualitätsmetriken.','Generation log'),
    ])
    common=[row('activity_key','concept:name','Aktivitätslabel für alle Miner.','Originale Namen einschließlich Leerzeichen bleiben erhalten.','Activity attribute'),
        row('timestamp_key','time:timestamp','Zeitstempelattribut; beim Genetic Miner auch für interne Sortierung verwendet.','Alle Fallsequenzen nach nativer Sortierung gegen dieselbe Completion-Projektion geprüft.','Timestamp attribute'),
        row('case_id_key','case:concept:name','DataFrame-Schlüssel; im EventLog liegen IDs als Trace-Attribut concept:name vor.','Alle 31,509 Fall-IDs und Fallgewichte bleiben erhalten.','Case identifier')]
    return {'common':common,'inductive':im,'heuristics':hm,'genetic':gm}

def format_value(value):
    return json.dumps(value,ensure_ascii=False) if isinstance(value,(bool,list)) else str(value)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    groups=catalogue()
    sources={'src/discovery.py':hashlib.sha256((ROOT/'src/discovery.py').read_bytes()).hexdigest(),
             'src/genetic_miner.py':hashlib.sha256((ROOT/'src/genetic_miner.py').read_bytes()).hexdigest()}
    document={'pm4py':'2.7.23.11','groups':groups,'sources':sources,
        'native_genetic_objective':{'average_trace_fitness':.4,'fraction_fitting_traces':.6},
        'optimization_recommendation':'Sound model and exact whole-case coverage near 80% first; then improve precision, with simplicity as tie-break and generalization as a diagnostic.',
        'sources_urls':['https://processintelligence.solutions/app/pm4py/api/api/pm4py.discovery.html','https://processintelligence.solutions/pm4py/examples/process-discovery/','https://doi.org/10.1007/11494744_5']}
    (OUT/'miner_parameters.json').write_text(json.dumps(document,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    md=['# Miner-Parameter: Bedeutung, Werte und Begründung','',
        'Die Werte stammen aus der tatsächlichen Python-Konfiguration. Baseline, ausgewähltes IMf-Modell und neuer Genetic-Versuch werden ausdrücklich unterschieden.','',
        '**Hauptziel:** gültiges, soundes Modell und ungefähr 80 % exakte Fallabdeckung als Bedingungen; danach Präzision erhöhen. Einfachheit als zusätzlicher Auswahlgrund, Generalization nur mit ihren Grenzen interpretieren.','',
        '**Aktuelle Priorität:** Das Modell mit harten Guards erreicht im Test nur 10,19 % vollständige Fallabdeckung. Dieser Verlust muss zuerst erklärt oder verbessert werden; zusätzliche Präzision allein löst ihn nicht.','',
        '## Alle gemeinsam verwendeten Schlüssel','']
    titles={'common':'Gemeinsame Schlüssel','inductive':'Inductive Miner und IMf','heuristics':'Heuristics Miner CLASSIC','genetic':'Genetic Miner CLASSIC: dritter Versuch'}
    for key,rows in groups.items():
        if key!='common':md+=['',f'## {titles[key]}','']
        md+=['| Parameter | Tatsächlicher Wert | Bedeutung | Begründung und Grenze |','|---|---|---|---|']
        for r in rows:md.append(f'| `{r["parameter"]}` | `{format_value(r["value"])}` | {r["meaning"]} | {r["reason"]} |')
    md+=['','## Besonders wichtig beim Inductive Miner','',
        '- `noise_threshold=0`: IM-Baseline; positive Werte wählen hier IMf. `0.03` bedeutet **nicht**, dass 3 % der Fälle oder Events gelöscht werden.',
        '- IMf filtert bei fehlendem Cut lokal schwache DFG-Kanten relativ zu starken ausgehenden Kanten; auch die Startaktivitätsfilterung ist relativ. Die Klassifikationsschwelle verändert nicht direkt einen vorgegebenen Anteil des Logs.',
        '- `disable_fallthroughs=True` lässt in dieser Version weiterhin Empty-Trace-/Flower-Fallback zu. Es ist daher kein Schalter für garantiert weniger erlaubtes Verhalten.',
        '- `multi_processing` ist hauptsächlich ein Ausführungsparameter. Der relevante fachliche Tuninghebel ist zunächst `noise_threshold`, ergänzt durch transparent getrennte Vorverarbeitung.',
        '- Präzision und Modellgröße reagieren nicht monoton: im vollständigen Log erreicht Noise 0.10 ungefähr 86.87 % Coverage und 0.4002 Präfixpräzision; Noise 0.15 ungefähr 83.33 % und 0.3196.',
        '', 'Die hier gespeicherten HM-Schlüssel stammen aus der Low-Level-API: `dependency_thresh`, `and_measure_thresh`, `loop_length_two_thresh`. In der öffentlichen High-Level-API heißen sie `dependency_threshold`, `and_threshold`, `loop_two_threshold`.', '', '## Was der Genetic Miner tatsächlich optimiert','',
        '`J = 0.4 * average_trace_fitness + 0.6 * fraction_fitting_traces`','',
        'Das ist die fest eingebaute Zielfunktion der installierten PM4Py-Version. Precision, Generalization und Simplicity gehen dort nicht ein. Ein höherer interner Wert ist deshalb kein Beweis eines besseren Gesamtmodells für das Assignment.',
        'Ein `fitness=1` oder eine bereits unveränderte Bestfitness kann die Suche vor der konfigurierten Generationsgrenze stoppen. Maßgeblich ist die gespeicherte Anzahl tatsächlicher Generationen.',
        '', 'Tatsächlicher Versuch: 2 von maximal 6 Generationen, Population 10, Seed 20261025. Der native Frühstopp trat nach unveränderter Bestfitness ein. Das korrekt exportierte Modell erreicht Token-Fitness 0.7410 und Token-Precision 0.5970, ist aber nachweislich unbeschränkt. Exakte Fallabdeckung wurde nicht enumeriert; 0 % passende Token-Replays beweisen nicht 0 % exakte Akzeptanz. [Vollständiger Vergleich](../results/genetic/comparison.md), [Exportaudit und Begründung D26](DESIGN_DECISIONS.md).', '', '## Welche Metrik lohnt sich zu optimieren?','',
        '1. Soundness/ausführbare Semantik und vollständige Fallabdeckung prüfen. Das hier operationalisierte Zielband 78--82 % ist eine dokumentierte Wahl für „ungefähr 80 %“. Es ist kein universelles Prozess-Mining-Gesetz.',
        '2. Unter diesen Bedingungen bevorzugt **Alignment-ET-Precision** erhöhen: IM hat bereits perfekte beobachtbare Fitness, lässt aber viel zusätzliches Verhalten zu. Immer dieselbe Eingabe und ausgeschlossene Präfixe berichten.',
        '3. Bei ähnlich geeigneten Modellen kleinere/verständlichere Modelle bevorzugen. Mehrere Komplexitätsmaße verwenden, weil sie unterschiedliche Strukturmerkmale messen.',
        '4. PM4Py-Generalization als Häufigkeitsheuristik berichten; für Zukunftsaussagen separat fallweise bzw. zeitlich getrennt validieren.',
        '', '**Gegenbeispiel:** HM erreicht etwa 0.9975 Align-ET-Precision, obwohl 84.35 % der nichtleeren gewichteten Präfixe ausgeschlossen werden und die exakte Fallabdeckung höchstens 1.30 % betragen kann. Diesen Wert allein zu maximieren wäre irreführend.',
        '', '## Vollständige Begründungen und Quellen','',
        '- [Designprotokoll](DESIGN_DECISIONS.md): Alternativen, Vorteile, Nachteile, Nachweise und offene Validierung.',
        '- [Discovery](DISCOVERY.md), [Qualitätsbewertung](EVALUATION.md), [Verfeinerung](REFINEMENT.md), [Decision Mining](DECISION_MINING.md).',
        '- [Offizielle PM4Py-API](https://processintelligence.solutions/app/pm4py/api/api/pm4py.discovery.html) und [offizielles Genetic-Miner-Beispiel](https://processintelligence.solutions/pm4py/examples/process-discovery/).',
        '- [Genetic Process Mining (2005)](https://doi.org/10.1007/11494744_5); [experimentelle Evaluation (2007)](https://doi.org/10.1007/s10618-006-0061-7).',
        '', 'Der Genetic-Versuch ist ein vorab begrenzter, ungetunter Vergleichslauf auf allen Fällen. Die konkrete PM4Py-Implementierung wird versioniert verwendet; ein einzelner kleiner Lauf ersetzt keine Multi-Seed- oder Konvergenzstudie.']
    (ROOT/'docs/MINER_PARAMETERS.md').write_text('\n'.join(md)+'\n',encoding='utf-8',newline='\n')
    # Readable technical PDF; not generated scientific report prose.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(OUT/'miner_parameter_overview.pdf') as pdf:
        for key in ('common','inductive','heuristics','genetic'):
            fig=plt.figure(figsize=(16.54,11.69),facecolor='white')
            fig.text(.045,.945,titles[key],fontsize=22,weight='bold',color='#163b54')
            subtitle='Python / PM4Py 2.7.23.11 | tatsächliche Werte | Rolle und Begründung getrennt'
            fig.text(.045,.91,subtitle,fontsize=12)
            ax=fig.add_axes([.04,.18,.92,.68]);ax.axis('off')
            cells=[]
            for r in groups[key]:
                cells.append(['\n'.join(textwrap.wrap(r['parameter'],26)),
                    '\n'.join(textwrap.wrap(format_value(r['value']),20)),
                    '\n'.join(textwrap.wrap(r['meaning'],55)),
                    '\n'.join(textwrap.wrap(r['reason'],63))])
            table=ax.table(cellText=cells,colLabels=['Parameter','Wert','Bedeutung','Begründung / Grenze'],
                colWidths=[.18,.13,.32,.37],cellLoc='left',loc='upper left')
            table.auto_set_font_size(False);table.set_fontsize(10)
            for (i,j),cell in table.get_celld().items():
                cell.set_edgecolor('#c5d2dc');cell.PAD=.05
                if i==0:cell.set_facecolor('#173d55');cell.set_text_props(color='white',weight='bold');cell.set_height(.065)
                else:
                    lines=max(value.count('\n')+1 for value in cells[i-1]);cell.set_height(.025*lines+.027)
                    cell.set_facecolor('#f0f5f8' if i%2 else 'white');cell.set_text_props(va='center')
            if key=='common':
                footer='Priorität: Soundness + ungefähr 80 % exakte Fallabdeckung; danach Precision erhöhen.\nHarte Guards: aktuell 10,19 % vollständige Testfallabdeckung; Struktur ohne Guards: 80,45 %.\nMetriken stets auf derselben Eingabe und mit ihren Ausschlüssen vergleichen.'
            elif key=='genetic':footer='Native Zielfunktion: 0.4 × mittlere Trace-Fitness + 0.6 × Anteil passender Traces.\nPrecision wird intern nicht optimiert. Maximal 60 Modellbewertungen in bis zu 6 Populationen; tatsächliche Generationen im Laufprotokoll.\nTatsächlich 2 Generationen; Modell unbeschränkt. Explorationslauf, keine globale Optimalitätsbehauptung.'
            elif key=='inductive':footer='Wichtig: 0.03 ist eine relative Rauschschwelle, kein Anteil gelöschter Fälle.\nDas finale Modell verwendet zusätzlich eine häufigkeitsbasierte Discovery-Trainingsmenge.\nMehr Rauschfilterung garantiert keine monoton höhere Precision.'
            else:footer='Die Baselinewerte sind dokumentierte Standardwerte, keine Optimierung auf diesen Datensatz.\nDas aktuelle HM-Netz ist nachweislich unbeschränkt. Hohe Precision allein genügt nicht.\nDie Folgen dieser Wahl sind Teil des Ergebnisvergleichs.'
            fig.text(.045,.09,footer,fontsize=11,linespacing=1.6)
            fig.text(.045,.025,'Details und Quellen: docs/MINER_PARAMETERS.md | Begründungen: docs/DESIGN_DECISIONS.md',fontsize=10,color='#526777')
            pdf.savefig(fig);fig.savefig(OUT/f'parameters_{key}.png',dpi=85);plt.close(fig)
    # Factual English parameter appendix. Justifications stay in companion docs.
    def tex(value):
        return str(value).replace('\\',r'\textbackslash{}').replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
    lines=['% Factual configuration only; author-written rationale belongs in the main report.']
    for key in ('common','inductive','heuristics','genetic'):
        title={'common':'Shared Attribute Keys','inductive':'Inductive Miner and Refinement','heuristics':'Heuristics Miner CLASSIC','genetic':'Genetic Miner CLASSIC: Exploratory Trial'}[key]
        lines+=['\\clearpage',f'\\subsection{{{title}}}',r'\begin{table}[h!]',r'\centering',r'\small',r'\begin{tabular}{p{0.34\textwidth}p{0.20\textwidth}p{0.38\textwidth}}',r'\hline',r'Parameter & Value & Role \\',r'\hline']
        for r in groups[key]:lines.append('\\texttt{'+tex(r['parameter'])+'} & '+tex(format_value(r['value']))+' & '+tex(r['role'])+r' \\')
        lines += [r'\hline',r'\end{tabular}',r'\caption{Actual configuration; PM4Py 2.7.23.11.}',r'\end{table}']
    (OUT/'miner_parameters.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print('Exported code-derived parameter JSON, Markdown, PDF and factual LaTeX tables',flush=True)

if __name__=='__main__':main()
