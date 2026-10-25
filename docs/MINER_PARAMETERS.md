# Miner-Parameter: Bedeutung, Werte und Begründung

Die Werte stammen aus der tatsächlichen Python-Konfiguration. Baseline, ausgewähltes IMf-Modell und neuer Genetic-Versuch werden ausdrücklich unterschieden.

**Hauptziel:** gültiges, soundes Modell und ungefähr 80 % exakte Fallabdeckung als Bedingungen; danach Präzision erhöhen. Einfachheit als zusätzlicher Auswahlgrund, Generalization nur mit ihren Grenzen interpretieren.

**Aktuelle Priorität:** Das Modell mit harten Guards erreicht im Test nur 10,19 % vollständige Fallabdeckung. Dieser Verlust muss zuerst erklärt oder verbessert werden; zusätzliche Präzision allein löst ihn nicht.

## Alle gemeinsam verwendeten Schlüssel

| Parameter | Tatsächlicher Wert | Bedeutung | Begründung und Grenze |
|---|---|---|---|
| `activity_key` | `concept:name` | Aktivitätslabel für alle Miner. | Originale Namen einschließlich Leerzeichen bleiben erhalten. |
| `timestamp_key` | `time:timestamp` | Zeitstempelattribut; beim Genetic Miner auch für interne Sortierung verwendet. | Alle Fallsequenzen nach nativer Sortierung gegen dieselbe Completion-Projektion geprüft. |
| `case_id_key` | `case:concept:name` | DataFrame-Schlüssel; im EventLog liegen IDs als Trace-Attribut concept:name vor. | Alle 31,509 Fall-IDs und Fallgewichte bleiben erhalten. |

## Inductive Miner und IMf

| Parameter | Tatsächlicher Wert | Bedeutung | Begründung und Grenze |
|---|---|---|---|
| `noise_threshold` | `0.0` | Relative Rauschschwelle; 0 aktiviert IM, positive Werte IMf. Kein Anteil entfernter Fälle. | 0 als Vergleichsbasis ohne zusätzlichen Rauschfilter; im finalen Modell 0.03 nach dokumentierter Kandidatensuche. |
| `multi_processing` | `false` | Parallele Ausführung des Miners. Kein fachlicher Filter. | False begrenzt Prozess-/Speicheraufwand und vereinfacht Fehlersuche. Kein Qualitätsoptimierungshebel. |
| `disable_fallthroughs` | `false` | False erlaubt zusätzliche Rückfallstrategien, wenn kein strukturierter Cut gefunden wird. | Standardstrategien bleiben verfügbar. True lässt hier weiterhin Empty-Trace-/Flower-Fallback zu; es garantiert keine höhere Präzision. |
| `final noise_threshold` | `0.03` | Rauschschwelle des gewählten IMf-Kandidaten, bei anderer Discovery-Trainingsmenge. | 0.03 wurde in der Suche ausgewählt; kein Beweis einer generell optimalen 3-Prozent-Schwelle. |
| `training_coverage` | `0.6` | Externer Frequenzfilter für das finale Modell; kein interner IM-Parameter. | Häufige Varianten als Discovery-Fokus. Tatsächlich 18,918 Fälle und 73 Varianten; Bewertung weiterhin auf allen 31,509 Fällen. |
| `target coverage band` | `[78, 82]` | Eigenes Auswahlband für ungefähr 80 Prozent vollständig replaybare Fälle. | Operationalisierung der Aufgabenanforderung; keine Datenbereinigung und kein vom Datensatz vorgegebener Grenzwert. |

## Heuristics Miner CLASSIC

| Parameter | Tatsächlicher Wert | Bedeutung | Begründung und Grenze |
|---|---|---|---|
| `variant` | `CLASSIC` | Verwendete Heuristics-Miner-Variante; Ausgabe wird in ein Petri-Netz umgewandelt. | Festgelegte Vergleichsbasis. Ein exportiertes Workflow-Netz ist noch kein Soundness-Nachweis. |
| `dependency_thresh` | `0.5` | Mindest-Abhängigkeitsmaß für eine direkt folgende Relation. | 0.5 ist die dokumentierte Baseline, nicht datenoptimiert. Höher ist strenger; seltene reale Pfade können entfallen. |
| `and_measure_thresh` | `0.65` | Schwelle für die Interpretation benachbarter Relationen als Parallelität. | 0.65 als Bibliotheksstandard. Höhere Werte erschweren AND-Erkennung; keine globale Monotonie der Qualitätswerte. |
| `loop_length_two_thresh` | `0.5` | Schwelle zum Erkennen kurzer Schleifen wie A-B-A. | 0.5 als Standard; kurze Wiederholungen sollen nicht durch reine Richtungsabhängigkeit verloren gehen. |
| `min_act_count` | `1` | Absolute Mindestanzahl beobachteter Events pro Aktivität. | 1 vermeidet eine zusätzliche absolute Häufigkeitsselektion. Andere HM-Filter gelten trotzdem. |
| `min_dfg_occurrences` | `1` | Absolute Mindesthäufigkeit einer direkt folgenden Kante. | 1 als permissive absolute Baseline; Dependency und relatives Pre-Cleaning können Kanten weiterhin entfernen. |
| `dfg_pre_cleaning_noise_thresh` | `0.05` | Relative DFG-Bereinigung vor der Abhängigkeitsberechnung. | 0.05 als expliziter Standard. Bezieht sich auf lokale Kantenhäufigkeiten, nicht auf fünf Prozent gelöschte Fälle. |

## Genetic Miner CLASSIC: dritter Versuch

| Parameter | Tatsächlicher Wert | Bedeutung | Begründung und Grenze |
|---|---|---|---|
| `population_size` | `10` | Anzahl konkurrierender Modelle je Generation. | 10 entspricht dem offiziellen kleinen Beispiel und hält den Voll-Log-Versuch bezahlbar; Default 500 wäre deutlich teurer. |
| `generations` | `6` | Obergrenze einschließlich der Anfangspopulation; native Frühstopps sind möglich. | 6 gibt vorab maximal 60 Modellbewertungen in bis zu 6 Populationen vor. Explorationsbudget, keine Konvergenzgarantie. |
| `elitism_rate` | `0.1` | Anteil unverändert übernommener bester Individuen; Anzahl ist round(rate * population_size). | 0.1 erhält bei Population 10 genau ein Modell. Default 0.01 ergäbe bei diesem kleinen Budget null Eliten. |
| `crossover_rate` | `1.0` | Wahrscheinlichkeit zur Rekombination ausgewählter Eltern. | 1.0 übernimmt den nativen Standard und kombiniert Eltern bei jeder entsprechenden Auswahl. |
| `mutation_rate` | `0.01` | Wahrscheinlichkeit je Input-/Outputeintrag, vorhandene Nachbarn neu zu partitionieren. | 0.01 übernimmt den Standard; dies ist nicht ein Prozent beliebig neu eingefügter Kanten. |
| `elitism_min_sample` | `2` | Tatsächlich die Stichprobengröße der Eltern-Turnierauswahl; nicht die Zahl der Eliten. | 2 hält bei Population 10 den Selektionsdruck moderat und ermöglicht mehr Elternvielfalt als der Default 5. |
| `random / numpy seed` | `20261025` | Kontrolliert Python-random und NumPy-Zufall. | Fixiert den konkreten Versuch. Ein Seed belegt keine Robustheit über mehrere Suchläufe. |
| `PYTHONHASHSEED` | `20261025` | Fixiert Set-Reihenfolgen im separaten Python-Prozess. | Zusätzlich nötig, weil die Implementierung zufällig aus Set-basierten Pools zieht. |
| `log_csv` | `evolution.csv` | Protokolliert die nativen Fitnesswerte je Population. | Unterscheidet geplante und tatsächlich durchgeführte Generationen sowie das interne Ziel von externen Qualitätsmetriken. |

## Besonders wichtig beim Inductive Miner

- `noise_threshold=0`: IM-Baseline; positive Werte wählen hier IMf. `0.03` bedeutet **nicht**, dass 3 % der Fälle oder Events gelöscht werden.
- IMf filtert bei fehlendem Cut lokal schwache DFG-Kanten relativ zu starken ausgehenden Kanten; auch die Startaktivitätsfilterung ist relativ. Die Klassifikationsschwelle verändert nicht direkt einen vorgegebenen Anteil des Logs.
- `disable_fallthroughs=True` lässt in dieser Version weiterhin Empty-Trace-/Flower-Fallback zu. Es ist daher kein Schalter für garantiert weniger erlaubtes Verhalten.
- `multi_processing` ist hauptsächlich ein Ausführungsparameter. Der relevante fachliche Tuninghebel ist zunächst `noise_threshold`, ergänzt durch transparent getrennte Vorverarbeitung.
- Präzision und Modellgröße reagieren nicht monoton: im vollständigen Log erreicht Noise 0.10 ungefähr 86.87 % Coverage und 0.4002 Präfixpräzision; Noise 0.15 ungefähr 83.33 % und 0.3196.

Die hier gespeicherten HM-Schlüssel stammen aus der Low-Level-API: `dependency_thresh`, `and_measure_thresh`, `loop_length_two_thresh`. In der öffentlichen High-Level-API heißen sie `dependency_threshold`, `and_threshold`, `loop_two_threshold`.

## Was der Genetic Miner tatsächlich optimiert

`J = 0.4 * average_trace_fitness + 0.6 * fraction_fitting_traces`

Das ist die fest eingebaute Zielfunktion der installierten PM4Py-Version. Precision, Generalization und Simplicity gehen dort nicht ein. Ein höherer interner Wert ist deshalb kein Beweis eines besseren Gesamtmodells für das Assignment.
Ein `fitness=1` oder eine bereits unveränderte Bestfitness kann die Suche vor der konfigurierten Generationsgrenze stoppen. Maßgeblich ist die gespeicherte Anzahl tatsächlicher Generationen.

Tatsächlicher Versuch: 2 von maximal 6 Generationen, Population 10, Seed 20261025. Der native Frühstopp trat nach unveränderter Bestfitness ein. Das korrekt exportierte Modell erreicht Token-Fitness 0.7410 und Token-Precision 0.5970, ist aber nachweislich unbeschränkt. Exakte Fallabdeckung wurde nicht enumeriert; 0 % passende Token-Replays beweisen nicht 0 % exakte Akzeptanz. [Vollständiger Vergleich](../results/genetic/comparison.md), [Exportaudit und Begründung D26](DESIGN_DECISIONS.md).

## Welche Metrik lohnt sich zu optimieren?

1. Soundness/ausführbare Semantik und vollständige Fallabdeckung prüfen. Das hier operationalisierte Zielband 78--82 % ist eine dokumentierte Wahl für „ungefähr 80 %“. Es ist kein universelles Prozess-Mining-Gesetz.
2. Unter diesen Bedingungen bevorzugt **Alignment-ET-Precision** erhöhen: IM hat bereits perfekte beobachtbare Fitness, lässt aber viel zusätzliches Verhalten zu. Immer dieselbe Eingabe und ausgeschlossene Präfixe berichten.
3. Bei ähnlich geeigneten Modellen kleinere/verständlichere Modelle bevorzugen. Mehrere Komplexitätsmaße verwenden, weil sie unterschiedliche Strukturmerkmale messen.
4. PM4Py-Generalization als Häufigkeitsheuristik berichten; für Zukunftsaussagen separat fallweise bzw. zeitlich getrennt validieren.

**Gegenbeispiel:** HM erreicht etwa 0.9975 Align-ET-Precision, obwohl 84.35 % der nichtleeren gewichteten Präfixe ausgeschlossen werden und die exakte Fallabdeckung höchstens 1.30 % betragen kann. Diesen Wert allein zu maximieren wäre irreführend.

## Vollständige Begründungen und Quellen

- [Designprotokoll](DESIGN_DECISIONS.md): Alternativen, Vorteile, Nachteile, Nachweise und offene Validierung.
- [Discovery](DISCOVERY.md), [Qualitätsbewertung](EVALUATION.md), [Verfeinerung](REFINEMENT.md), [Decision Mining](DECISION_MINING.md).
- [Offizielle PM4Py-API](https://processintelligence.solutions/app/pm4py/api/api/pm4py.discovery.html) und [offizielles Genetic-Miner-Beispiel](https://processintelligence.solutions/pm4py/examples/process-discovery/).
- [Genetic Process Mining (2005)](https://doi.org/10.1007/11494744_5); [experimentelle Evaluation (2007)](https://doi.org/10.1007/s10618-006-0061-7).

Der Genetic-Versuch ist ein vorab begrenzter, ungetunter Vergleichslauf auf allen Fällen. Die konkrete PM4Py-Implementierung wird versioniert verwendet; ein einzelner kleiner Lauf ersetzt keine Multi-Seed- oder Konvergenzstudie.
