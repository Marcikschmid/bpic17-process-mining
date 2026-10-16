# Discovery-Baselines: Abschnitt 3.3, Aufgabe 1

## Ausführen und Ergebnisse ansehen

Aus dem Repository-Hauptordner:

```powershell
.\.venv\Scripts\python.exe scripts/discover_models.py
```

Das Skript lädt die verifizierte Originaldatei, bereitet eine gemeinsame Eingabe auf und führt **zwei unterschiedliche Algorithmen** aus. Kein einzelner Trace wird als Trainingsbeispiel ausgewählt: Alle Fälle gehen in die Discovery ein.

- `results/models/inductive_miner.pnml` und `heuristics_miner.pnml`: vollständige Petri-Netze mit Anfangs- und Endmarkierung; später für die Qualitätsbewertung wieder einlesbar.
- `results/figures/inductive_miner.pdf` und `heuristics_miner.pdf`: vollständige Vektorgrafiken zum Zoomen; zusätzlich SVG, PNG und Graphviz-Quellen.
- `results/tables/discovery_manifest.json`: tatsächliche Fall-/Eventzahlen, ausgeschlossene Lifecycle-Zustände, Aktivitätsnamen, Parameter, Versionen, Laufzeiten, Modellgrößen und Prüfsummen.
- `report/figures/`: bewusst ausgewählte PDF-Kopien für den LaTeX-Anhang. Eine erneute Discovery verändert diesen Ordner nicht.

Die Darstellung verkleinert ausschließlich Places und stille Transitionen und verwendet die unveränderten Aktivitätslabels. Keine Knoten oder Kanten werden zur Vereinfachung der Abbildung entfernt. Der Anhang verwendet für die vollständigen Modelle größere A3-Tafeln; Hauptteil und Parametertabellen bleiben A4.

## Gemeinsame Datenaufbereitung

1. SHA-256 der komprimierten Originaldatei gegen `data/manifest.json` prüfen.
2. Vollständigen Event Log mit dem bestehenden `iterparse`-Importer laden.
3. Auf Event-Ebene ausschließlich `lifecycle:transition == complete` behalten.
4. Prüfen, dass alle Fall-IDs in derselben Reihenfolge vorhanden bleiben. Bei Fallverlust oder einem leeren Fall abbrechen.
5. Dieselbe aufbereitete Eingabe an beide Algorithmen übergeben.

Die Reihenfolge innerhalb eines Falls bleibt die Reihenfolge der Originaldatei. Keine Sortierung nach Zeitstempeln, kein Sampling, keine Auswahl bestimmter Outcomes oder Fallvarianten, keine Zusammenfassung oder Umbenennung von Aktivitäten. Der nachgestellte Leerraum in `W_Shortened completion ` wird ebenfalls beibehalten.

Der vollständige Lauf verwendet **31.509 Fälle und 475.306 Events mit 24 Aktivitätsnamen**. Gegenüber den 1.202.267 ursprünglichen Events werden 726.961 Nicht-Completion-Events ausgeschlossen. `W_Personal Loan collection` und `W_Shortened completion ` besitzen keine Completion-Events und fehlen deshalb in dieser Projektion. Es entfällt kein Fall. Auch der geladene Rohlog im Arbeitsspeicher wird durch die Projektion nicht verändert.

**Begründung:** Ein Work-Item kann durch `schedule`, `start`, `suspend`, `resume` und `complete` mehrfach im Log stehen. Für diese erste Vergleichsbasis soll eine abgeschlossene Ausführung durch ein Completion-Event repräsentiert werden. Tatsächliche Wiederholungen abgeschlossener Aktivitäten bleiben erhalten.

**Grenze:** Abgebrochene oder zurückgezogene Work-Items ohne `complete` werden nicht abgebildet. Auch Aktivitätsnamen können dadurch vollständig entfallen; das Manifest nennt diese ausdrücklich. Die Modelle beschreiben die Completion-Projektion, nicht das gesamte Lifecycle-Verhalten des Rohlogs. Diese Entscheidung ist bei späteren Metriken und Verfeinerungen zu berücksichtigen. Beide Modelle müssen zunächst gegen dieselbe Projektion bewertet werden; Werte sind nicht unmittelbar mit Auswertungen des ungefilterten Logs oder anders aufbereiteter Literaturdaten vergleichbar.

## Algorithmen und Parameter

| Verfahren | Implementierung | Explizite Parameter |
|---|---|---|
| Inductive Miner | `pm4py.discover_petri_net_inductive`, Variante **IM** bei Noise Threshold 0.0; Process Tree intern zu Petri-Netz konvertiert | `noise_threshold=0.0`, `multi_processing=False`, `disable_fallthroughs=False` |
| Heuristics Miner | `pm4py.algo.discovery.heuristics.algorithm.apply`, Variante **CLASSIC**; Heuristics Net intern zu Petri-Netz konvertiert | `dependency_thresh=0.5`, `and_measure_thresh=0.65`, `loop_length_two_thresh=0.5`, `min_act_count=1`, `min_dfg_occurrences=1`, `dfg_pre_cleaning_noise_thresh=0.05` |

Aktivitätsattribut: `concept:name`; Zeitstempel: `time:timestamp`; PM4Py-Case-Key: `case:concept:name` (im XES-EventLog liegen Case-IDs als Trace-Attribut `concept:name` vor).

IM zerlegt das beobachtete Verhalten in strukturierte Teilprozesse. Heuristics Miner nutzt Häufigkeiten und Abhängigkeitsmaße zwischen Aktivitäten. Die Schwellenwerte des Heuristics Miner können Kanten ausschließen; das ist Bestandteil dieses Algorithmus und keine zusätzliche Filterung seiner Eingabefälle. Insbesondere ist sein DFG-Pre-Cleaning explizit auf den installierten Standardwert 0.05 gesetzt. Die Werte sind erste Baselines und noch keine durch Qualitätsmessungen optimierten Einstellungen.

Keine stochastische Suche und kein Sampling; kein algorithmischer Random Seed. PM4Py erzeugt teils UUIDs für Modellknoten. Knoten-IDs, Dateihashes und Graphviz-Anordnung können deshalb bei Wiederholung abweichen. Paketversionen sind in `requirements.txt` festgehalten, die verwendeten Runtime-Versionen zusätzlich im Manifest.

## Prüfung und nächste Aufgabe

Das Skript liest jedes exportierte PNML erneut ein und vergleicht Knoten, Aktivitätslabels, gewichtete Kanten sowie Anfangs- und Endmarkierungen. Die Tests unter `tests/` schützen vor Fallverlust, veränderter Reihenfolge und fehlerhaften Pflichtfeldern:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Knoten- und Kantenzahlen sind **noch keine Simplicity-Metriken**. Fitness, Precision, Generalization, Simplicity und der Anteil vollständig replaybarer Cases sind für diese Baselines noch nicht berechnet. Die Modelle sind noch keine Auswahl des finalen Simulationsmodells. Das später geforderte finale BPMN-2.0-Modell und Decision Mining folgen in weiteren Aufgaben.

## Primärquellen

- [Leemans, Fahland und van der Aalst (2013): Discovering block-structured process models from event logs: a constructive approach](https://research.tue.nl/en/publications/discovering-block-structured-process-models-from-event-logs-a-con-2/), DOI: 10.1007/978-3-642-38697-8_17.
- [Offizieller PM4Py-Quellcode: Heuristics Miner CLASSIC](https://github.com/process-intelligence-solutions/pm4py/blob/release/pm4py/algo/discovery/heuristics/variants/classic.py).
- Verwendete lokale PM4Py-Version und die tatsächlich aufgerufenen Parameter: `results/tables/discovery_manifest.json`. Die lokale, gepinnte Installation ist für diesen Lauf maßgeblich; der verlinkte Release-Branch kann sich ändern.
