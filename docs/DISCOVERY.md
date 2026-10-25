# Discovery-Baselines: Abschnitt 3.3, Aufgabe 1

## Ausführen und Ergebnisse ansehen

Aus dem Repository-Hauptordner:

```powershell
.\.venv\Scripts\python.exe scripts/discover_models.py
```

Das Skript lädt die verifizierte Originaldatei, bereitet eine gemeinsame Eingabe auf und führt **zwei unterschiedliche Algorithmen** aus. Kein einzelner Trace wird als Trainingsbeispiel ausgewählt: Alle Fälle gehen in die Discovery ein.

Nur den Inductive Miner erneut starten:

```powershell
.\.venv\Scripts\python.exe scripts/discover_models.py --algorithm inductive
```

Dieser einzelne Lauf schreibt nach `results/runs/inductive/`: die Grafik nach `figures/inductive_miner.png` (auch SVG und PDF), das Modell nach `models/inductive_miner.pnml` und das Manifest nach `tables/discovery_manifest.json`. Der Ordner enthält jeweils den letzten einzelnen IM-Lauf und bleibt lokal. `--algorithm heuristics` startet entsprechend nur Heuristics Miner. Ohne Option werden beide Baselines wie bisher unter `results/` erzeugt. Ein abweichender Ausgabeordner kann mit `--output-dir results/runs/mein_lauf` gewählt werden.

Nur den Heuristics Miner starten:

```powershell
.\.venv\Scripts\python.exe scripts/discover_models.py --algorithm heuristics
```

Dieser Lauf schreibt nach `results/runs/heuristics/`; die Grafik liegt dort unter `figures/heuristics_miner.png` (auch SVG und PDF), das Petri-Netz unter `models/heuristics_miner.pnml` und das Laufprotokoll unter `tables/discovery_manifest.json`.

- `results/models/inductive_miner.pnml` und `heuristics_miner.pnml`: vollständige Petri-Netze mit Anfangs- und Endmarkierung; später für die Qualitätsbewertung wieder einlesbar.
- `results/figures/inductive_miner.pdf` und `heuristics_miner.pdf`: vollständige Vektorgrafiken zum Zoomen; zusätzlich SVG, PNG und Graphviz-Quellen.
- `results/tables/discovery_manifest.json`: tatsächliche Fall-/Eventzahlen, ausgeschlossene Lifecycle-Zustände, Aktivitätsnamen, Parameter, Versionen, Laufzeiten, Modellgrößen und Prüfsummen.
- `report/figures/`: bewusst ausgewählte PDF-Kopien für den LaTeX-Anhang. Eine erneute Discovery verändert diesen Ordner nicht.

Die Darstellung verkleinert ausschließlich Places und stille Transitionen und verwendet die unveränderten Aktivitätslabels. Keine Knoten oder Kanten werden zur Vereinfachung der Abbildung entfernt. Der Anhang verwendet für die vollständigen Modelle größere A3-Tafeln; Hauptteil und Parametertabellen bleiben A4.

## Warum Petri-Netze statt BPMN?

Discovery bezeichnet die Methode zum Entdecken eines Modells aus einem Event Log. Petri-Netze und BPMN sind unterschiedliche Modellierungssprachen. Die Ausgabe hängt vom Algorithmus und der aufgerufenen Funktion ab.

| Verfahren | Interne Modellform | Ausgabe in unserem Code |
|---|---|---|
| Inductive Miner | Process Tree | Umwandlung in ein Petri-Netz mit Anfangs- und Endmarkierung |
| Heuristics Miner CLASSIC | Heuristics Net | Umwandlung in ein Petri-Netz mit Anfangs- und Endmarkierung |

PM4Py bietet für Inductive Miner auch `discover_bpmn_inductive()` als BPMN-Ausgabe. Unsere zwei Baselines verwenden dieselbe Modellform für die spätere Qualitätsbewertung. Das finale Modell soll gemäß Assignment in BPMN 2.0 vorliegen; die Entdeckungsmodelle im Anhang können Petri-Netze sein. Ein Wechsel der Darstellung allein ist noch keine Modellverfeinerung.

Quelle: [Offizielle PM4Py-API: Discovery](https://processintelligence.solutions/app/pm4py/api/api/pm4py.discovery.html). Die hier verwendeten lokalen Implementierungen stehen in `pm4py/discovery.py` und `pm4py/algo/discovery/heuristics/variants/classic.py` der gepinnten Installation.

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

Der zusätzliche Vergleich unter `results/tables/discovery_comparison_audit.json` bestätigt die gleiche Eingabe, alle Artefakt-Prüfsummen und die aus PNML unabhängig gezählten Modellgrößen. Beide Modelle enthalten dieselben 24 sichtbaren Aktivitäten; IM besitzt 29 stille Transitionen und 114 Kanten, HM 70 stille Transitionen und 220 Kanten.

Eine gezielte Ausführungsprüfung mit PM4Pys Petri-Netz-Semantik zeigt einen Verhaltensunterschied: Der erste Originalfall `Application_652823628` mit 14 Completion-Events erreicht im IM-Modell die Endmarkierung. Im HM-Modell blockiert er beim dritten sichtbaren Event `A_Concept`, nach `A_Create Application` und `A_Submitted`. Fall-ID und die gesamte Completion-Sequenz wurden direkt gegen die komprimierte Original-XES geprüft. Zusätzliche Präfixprüfungen wurden unabhängig per XML-basierter Zustandsraumsuche und anschließend mit PM4Py gegengeprüft; stille Übergänge werden dabei berücksichtigt.

Dies ist eine konkrete Gegenprobe für die aktuelle HM-Baseline, keine Messung der Gesamt-Fitness oder des Anteils replaybarer Fälle und keine allgemeine Aussage über Heuristics Miner. Ein erfolgreicher Datei-Export garantiert keine hohe Modellqualität. Die Modelle und Parameter bleiben für den anschließenden systematischen Vergleich unverändert.

Das Skript liest jedes exportierte PNML erneut ein und vergleicht Knoten, Aktivitätslabels, gewichtete Kanten sowie Anfangs- und Endmarkierungen. Die Tests unter `tests/` schützen vor Fallverlust, veränderter Reihenfolge und fehlerhaften Pflichtfeldern:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_setup.py
```

Diese drei Prüfungen wurden am 2026-10-17 erfolgreich ausgeführt: keine Paketkonflikte, drei bestandene Tests sowie erfolgreiche Import-, Graphviz-, PNG-, Notebook-Format- und Kernel-Registrierungsprüfungen. Die Unit-Tests prüfen die gemeinsame Datenaufbereitung; sie sind kein vollständiger Korrektheitsbeweis für PM4Py oder die gesamte Anwendung.

Für einen vollständigen neuen Discovery-Lauf mit beiden Verfahren und eigener Ergebnisablage:

```powershell
.\.venv\Scripts\python.exe scripts/discover_models.py --output-dir results/runs/review
```

Aufgabe 3.3.1 ist erfüllt: zwei unterschiedliche Verfahren wurden angewendet und beide Modelle sind im LaTeX-Anhang eingebunden. Die Umsetzung von 3.3.2 ist in `docs/EVALUATION.md` beschrieben; die zusätzliche optimale HM-Alignment-Fitness ist noch offen. Rohdatenstatistik: `docs/STATISTICS.md`; finales Strukturmodell: `docs/REFINEMENT.md`; Decision Mining und seine Grenzen: `docs/DECISION_MINING.md`.

Die ursprüngliche Discovery-Tabelle enthält lediglich Strukturzahlen. Die separate Qualitätsbewertung ergänzt literaturbasierte Komplexitätsmaße und PM4Py-Qualitätsmetriken (`docs/EVALUATION.md`). Die Discovery-Baselines, das verfeinerte Strukturmodell und das experimentelle Modell mit gelernten Guards bleiben getrennt; die Guards sind noch keine validierten Regeln für eine realistische Simulation.

## Primärquellen

- [Leemans, Fahland und van der Aalst (2013): Discovering block-structured process models from event logs: a constructive approach](https://research.tue.nl/en/publications/discovering-block-structured-process-models-from-event-logs-a-con-2/), DOI: 10.1007/978-3-642-38697-8_17.
- [Offizieller PM4Py-Quellcode: Heuristics Miner CLASSIC](https://github.com/process-intelligence-solutions/pm4py/blob/release/pm4py/algo/discovery/heuristics/variants/classic.py).
- Verwendete lokale PM4Py-Version und die tatsächlich aufgerufenen Parameter: `results/tables/discovery_manifest.json`. Die lokale, gepinnte Installation ist für diesen Lauf maßgeblich; der verlinkte Release-Branch kann sich ändern.
