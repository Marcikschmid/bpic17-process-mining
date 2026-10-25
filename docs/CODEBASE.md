# Aktuelle Codebasis

Die Codebasis deckt Einrichtung, Datenbeschaffung, Import, Jupyter-Einstieg, zwei Discovery-Baselines, deren Qualitätsbewertung, ein verfeinertes BPMN und Alignment-basiertes Decision Mining mit lokaler Browseransicht ab. Die zusätzliche optimale HM-Alignment-Fitness läuft noch; die Advanced-Analyse ist noch nicht implementiert. Die vollständige Rohdatenstatistik aus 3.2 ist unabhängig direkt gegen den Roh-XES geprüft (docs/STATISTICS.md). Die Grenzen der experimentellen Guards stehen in docs/DECISION_MINING.md.

## Wiederverwendbarer Python-Code: src/

`src/event_log.py` enthält `load_event_log()`. Die Funktion findet die Originaldatei relativ zum Projektordner, prüft ihre Existenz und lädt sie mit PM4Py. Der explizite Importer `iterparse` erzeugt ein `EventLog`. Es werden keine Aktivitäten, Fälle oder Lifecycle-Zustände gefiltert.

Ein `EventLog` enthält Fälle, auch Traces genannt. `log[0]` ist der erste Fall. `log[0].attributes` enthält Case-Attribute, etwa den beantragten Betrag. Die Events dieses Falls enthalten jeweils eigene Attribute, etwa Aktivitätsname und Zeitstempel.

`src/runtime.py` stellt Graphviz für den aktuellen Python-Prozess bereit und legt den matplotlib-Cache im lokalen, ignorierten Ordner `tmp/` ab. Es verändert keine permanenten System-Suchpfade. `src/__init__.py` kennzeichnet den Ordner als Python-Paket.

`src/discovery.py` definiert eine gemeinsame Discovery-Eingabe und explizite Parameter für **Inductive Miner (IM)** und **Heuristics Miner (CLASSIC)**. Nur Events mit `lifecycle:transition == complete` werden für diese Baselines verwendet. Fall-IDs und ihre Reihenfolge müssen erhalten bleiben; andernfalls bricht die Verarbeitung ab. Der Originalimport bleibt unverändert. Modellgrößen sind strukturelle Beschreibungen, noch keine Qualitätsbewertung. Die Gründe und Grenzen stehen in `docs/DISCOVERY.md`.

`src/log_statistics.py` berechnet die Statistik des unveränderten Roh-Logs:
Varianten, Attributprofile, Länge und Dauer mit SDs und Quantilen sowie
Aktivitäts-/Lifecycle-Häufigkeiten, Ressourcen und Variantenabdeckung.
Die Discovery-Projektion wird dafür nicht verwendet.

`src/simplicity.py` implementiert eigene Maße für Modellgröße, Extended Cardoso
und Extended Cyclomatic. Es erhält ein Petri-Netz und dessen Markierungen aus
dem PNML-Import; es benötigt keinen Event Log. Die Qualitätsbewertung der
gespeicherten Modelle übernimmt `scripts/evaluate_models.py`, das für
Fitness, Precision und Generalization dieselbe Completion-Projektion aus
`src/discovery.py` verwendet. Definitionen und Grenzen: `docs/EVALUATION.md`.

`src/quality.py` führt PM4Pys Alignment-Precision in kleinen Präfixblöcken aus,
damit nicht alle synchronen Produktnetze gleichzeitig im Speicher liegen.
Die globale Gewichtung und die Metrik bleiben erhalten; Tests vergleichen die
Ergebnisse mit dem unveränderten PM4Py-Aufruf.

`src/alignment.py` berechnet optimale A*-Alignments pro Aktivitätsvariante,
speichert jedes fertige Resultat sofort unter `tmp/evaluation/` und setzt
unterbrochene Läufe anhand geprüfter Checkpoints fort. Die Endauswertung enthält
wieder alle ursprünglichen Fälle mit ihrer tatsächlichen Häufigkeit.
Standardmäßig gibt es keine Zeitgrenze für diesen Zusatzlauf.

`src/replay_coverage.py` prüft ganze Fälle exakt über den vollständigen
endlichen Markierungsgraphen und Epsilon-Abschlüsse. Es prüft auch die gesamte
Sprachäquivalenz zwischen Petri-Netz und erneut importiertem BPMN.
`src/finite_precision.py` berechnet PM4Pys Align-ET auf diesem Graphen mit
gewichteten unsichtbaren Schritten, ohne wiederholt Produktnetze zu erzeugen.
Tests und echte PM4Py-Präfixprüfungen bestätigen die Gleichwertigkeit.
`src/bpmn_viewer.html` ist die Vorlage für die lokale bpmn-js-Modellansicht.

`src/validation.py` überprüft mit exakten rationalen Ungleichungen Nachweise für
unerreichbare Transitionen. Der zusätzliche Struktur-Audit benötigt nur die
gespeicherten Modelle und ihre Anfangsmarkierungen.

## Ausführbare Arbeitsschritte: scripts/

| Skript | Aufgabe |
|---|---|
| `setup.ps1` | Erstellt `.venv/`, installiert festgehaltene Paketversionen, registriert den lokalen Notebook-Kernel und richtet Graphviz ein |
| `setup_graphviz.py` | Lädt das offizielle Windows-ZIP, prüft seine SHA-256-Prüfsumme und entpackt es nach `.tools/graphviz/` |
| `check_setup.py` | Prüft Bibliotheksimporte, SVG-/PNG-Rendering, Notebook-Format und Registrierung des Jupyter-Kernels |
| `download_data.py` | Beschafft Originaldateien und prüft Größe sowie Quell-MD5; dokumentiert zusätzlich lokale SHA-256-Prüfsummen |
| `inspect_log.py` | Lädt alle Fälle, zählt Events und Aktivitätsnamen, prüft notwendige Felder auf fehlende Werte und exportiert eine Fallvorschau |
| `analyze_log.py` | Berechnet alle Statistiken aus 3.2 über alle unveränderten Roh-Events; exportiert Fall-/Varianten-CSV und Attributprofile |
| `render_log_statistics.py` | Erstellt faktische LaTeX-Tabellen und statistische PDF-/SVG-/PNG-Grafiken ausschließlich unter results/ |
| `verify_log_statistics.py` | Unabhängiger XML-Reader: prüft alle Fälle, Eventzahlen, Varianten, Attributprofile und statistischen Momente direkt gegen die gzip-XES-Datei |
| `discover_models.py` | Entdeckt beide Petri-Netze auf derselben Completion-Projektion; exportiert PNML, PDF, SVG, PNG, Graphviz-Quellen und ein Parameter-/Prüfsummenmanifest ausschließlich nach `results/` |
| `refine_model.py` / `refine_frequent.py` | Systematische IMf-Verfeinerungen und explizit dokumentierte häufige Discovery-Varianten; Bewertung immer auf allen Fällen |
| `export_refined_model.py` | Wählt den Kandidaten im Zielband, prüft BPMN-Sprachäquivalenz und exportiert Modell, Kennzahlen und Browseransicht |
| `accelerate_refinement.py` | Berechnet alle 27.816 Präfixe mit dem schnellen endlichen Solver und prüft 191 Präfixe gegen die unveränderte PM4Py-Suche |
| `render_refinement.py` / `verify_refinement.py` | Iterations-/Literaturvergleich rendern; Fallgewichte, PM4Py-Referenzgraph und echte optimale Alignment-Beispiele prüfen |
| `setup_bpmn_viewer.py` | Installiert die in docs/bpmn_viewer_manifest.json gepinnte bpmn-js-Version projektlokal und prüft npm-SHA-512 |
| `evaluate_models.py` | Bewertet beide gespeicherten Modelle mit PM4Py-Metriken und eigenen Komplexitätsmaßen; protokolliert Vollständigkeit, Laufgrenzen und Provenienz |
| `render_evaluation.py` | Erstellt Vergleichsgrafiken, CSV und eine faktische LaTeX-Tabelle aus den Bewertungsresultaten ausschließlich unter `results/` |
| `finalize_evaluation.py` | Wartet optional ohne Frist auf den Alignment-Prozess; nach vollständigen Resultaten: zusammenfassen, rendern, streng prüfen, drei bereits ausgewählte Reportassets kopieren und LaTeX bauen |
| `verify_evaluation.py` | Prüft Fallgewichtung, Modell- und Artefakt-Prüfsummen sowie das Unbeschränktheitszeugnis unabhängig mit PM4Py-Semantik |
| `audit_dead_transitions.py` | Speichert exakt nachprüfbare Nachweise unerreichbarer Transitionen; Originalmodelle bleiben erhalten |
| `start_jupyter.ps1` | Startet die lokale Jupyter-Oberfläche mit dem gesamten Repository als Arbeitsbereich |

Vorhandene passende Datendateien werden beim Download erneut verifiziert. Abweichende Dateien werden nicht automatisch überschrieben. Der Importcheck ersetzt keine vollständige Datenqualitätsanalyse.

## Interaktives Arbeiten: notebooks/

`01_getting_started.ipynb` enthält Erklärungen und kleine Codezellen. Es verwendet die Ladefunktion aus `src/`, statt den Import erneut zu implementieren. Anschließend zeigt es die Case-Attribute und die ersten zwanzig Events eines Falls. Es speichert beim Ausführen keine neuen Analyse-Tabellen; der separate Importcheck erledigt den Export.

## Daten, Ergebnisse und Umgebung

- `data/raw/`: unveränderte Originaldateien; lokal gespeichert und nicht in Git.
- `data/processed/`: Platz für später erzeugte Arbeitsdaten; ebenfalls nicht in Git.
- `data/manifest.json`: dokumentierte Herkunft, Größen und Prüfsummen.
- `results/tables/import_summary.json`: Ergebnis des Importchecks.
- `results/tables/first_case.csv`: vollständige Event-Vorschau des ersten Falls.
- `results/tables/discovery_manifest.json`: Eingabe-Prüfsumme, Lifecycle-Filter, Fall-/Eventzahlen, Parameter, Versionen und Modellstruktur.
- `results/models/`: Petri-Netze einschließlich Anfangs- und Endmarkierung im PNML-Format.
- `results/figures/`: vollständige Modellabbildungen und ihre Graphviz-Quellen.
- `requirements.in`: direkte Abhängigkeiten, etwa PM4Py und JupyterLab.
- `requirements.txt`: konkret installierte Versionen einschließlich weiterer Abhängigkeiten.
- `.venv/`, `.tools/` und `tmp/`: lokale Umgebung, Werkzeuge und temporäre Dateien; nicht in Git.

## Eigenständiger Bericht: report/

Alle LaTeX-Quellen, Literaturangaben, ausgewählten Abbildungen und Tabellen sowie das Bericht-Buildskript liegen unter `report/`. Der Build führt keinen Python-Code aus und liest keinen Event Log. Details stehen in `report/README.md`.

Der Arbeitsfluss ist: Originaldaten → Python-Import/Analyse → Ergebnisse unter `results/` → bewusste Auswahl für `report/figures/` und `report/tables/` → LaTeX-PDF. Eine erneute Analyse überschreibt den Bericht nicht.

Die beiden Discovery-Abbildungen sind als ausgewählte Kopien in den Anhang eingebunden. `tests/test_discovery_preprocessing.py` prüft Reihenfolge, Attribute, unveränderte Rohdaten und Fehlerfälle der gemeinsamen Datenaufbereitung. Das Exportskript prüft außerdem Topologie und Markierungen nach erneutem Einlesen jedes PNML-Modells.
## Decision Mining (3.3.4)

- `src/finite_alignment.py`: optimale vollständige Alignments auf einem zertifiziert endlichen Markierungsgraphen; Replay jedes Ergebnisses.
- `src/decision_display.py`: lesbare Bedingungen direkt am XOR; nur gleich vorhersagende Teilbäume vereinfachen, vollständigen Präfixabgleich prüfen.
- `src/decision_mining.py`: explizite BPMN-Flusssemantik, Zuordnung von XOR-Zweigen, Datenzustand vor Entscheidungen, Regel- und FEEL-Export, exaktes Replay mit Guards.
- `scripts/mine_decisions.py`: alle Fälle/Varianten, globaler Fall-Split, CART-Training und Testbewertung, Guard-Abdeckung.
- `scripts/render_decisions.py`: grafische Bäume und Blöcke, BPMN-Bedingungen, Browseransicht, faktische Tabellen und lesbare Vektor-Panels.
- `scripts/verify_decisions.py`: alle Regeln, getrennte Fallgruppen und sämtliche Rohdatensnapshots gegenprüfen.
- `scripts/select_decision_report.py`: geprüfte faktische Artefakte ausdrücklich nach `report/` übernehmen; von normaler Analyse und Rendering getrennt.
- `tests/test_decision_mining.py`: Kostenvergleich mit PM4Py, Datenverfügbarkeit, Sprache und Guard-Replay.
- Ablauf und Grenzen: `docs/DECISION_MINING.md`. Originalmodelle und bisherige Strukturkennzahlen bleiben getrennt; das experimentelle Guard-Modell erreicht im Test 10,19 % vollständige Fallabdeckung.


## Zusätzlicher Genetic-Miner-Versuch und Parameterübersicht

`src/genetic_miner.py` kapselt den nativen PM4Py-Algorithmus mit gespeicherten
Parametern und Seeds. `scripts/discover_genetic.py` prüft den identischen Voll-Log-
Input, startet den getrennten Hash-Seed-Prozess und nutzt den gemeinsamen Exporter
in `scripts/discover_models.py`. Dieser vergibt in einer Modellkopie eindeutige
Export-IDs, ohne das Verhalten oder sichtbare Aktivitätsnamen zu verändern.

`render_genetic_comparison.py` vergleicht gespeicherte Messwerte; es trainiert
keine Modelle. `export_miner_overview.py` liest die Konfiguration aus den beiden
Discovery-Modulen und erzeugt Erklärungen unter `docs/` und Artefakte unter
`results/parameters/`. Die beiden `select_*_report.py`-Schritte wählen ausdrücklich
faktische Parameter-/Genetic-Artefakte für `report/` aus.

Die einmalige historische Exportkorrektur ist in `recover_genetic_export.py`
nachvollziehbar. `verify_genetic_trial.py` vergleicht unabhängig Graphkanten,
Labels, Markierungen, Prüfsummen, native Zielfunktion und Unbeschränktheitsbeweis.
