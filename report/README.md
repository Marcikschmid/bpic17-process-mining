# LaTeX-Bericht

Dieser Ordner enthält das eigenständige LaTeX-Projekt für die Abgabe. Zum Kompilieren werden eine TeX-Installation und Latexmk benötigt. Python, Jupyter und der BPIC-17-Datensatz werden dafür nicht benötigt.

## Dateien

| Pfad | Aufgabe |
|---|---|
| `main.tex` | Hauptdokument: Titel, Gliederung und Einbindung der Kapitel |
| `sections/` | Eigene englische Texte für die einzelnen Aufgabenabschnitte |
| `references.bib` | Literaturangaben im BibTeX-Format |
| `figures/` | Ausgewählte Abbildungen für die Abgabe |
| `tables/` | Ausgewählte LaTeX-Tabellen für die Abgabe |
| `tum/`, `tumuser.sty` | Übernommene TUM-Vorlage mit Klassen, Stilen und Ressourcen |
| `latexmkrc` | Suchpfade der Vorlage und Ausgabeordner |
| `build.ps1` | Startet ausschließlich die LaTeX-Kompilierung |
| `build/` | Erzeugte PDF und Hilfsdateien; von Git ausgeschlossen |

## Kompilieren

Aus dem Repository-Hauptordner:

```powershell
.\report\build.ps1
```

Die fertige PDF liegt unter `report/build/main.pdf`. Alternativ innerhalb dieses Ordners `latexmk -pdf main.tex` ausführen; unter Windows muss Perl im Suchpfad verfügbar sein. Das PowerShell-Skript ergänzt bei vorhandener Standardinstallation den Perl-Pfad von Git for Windows für den Build-Prozess.

## Grenze zum Analyseprojekt

Die Python-Analyse liest Daten aus `data/` und schreibt Ergebnisse nach `results/`. Sie erzeugt oder verändert keine Berichtstexte.

Erst wenn ein Ergebnis für die Abgabe ausgewählt wurde, wird die passende Abbildung nach `report/figures/` beziehungsweise eine fertige LaTeX-Tabelle nach `report/tables/` kopiert. Diese Auswahl erfolgt bewusst. Das separat aufzurufende `scripts/finalize_evaluation.py` aktualisiert ausschließlich die drei bereits ausgewählten Qualitätsassets und baut den Bericht; gewöhnliche Analyseaufrufe verändern den Bericht weiterhin nicht. Im Bericht werden nur diese lokalen Dateien referenziert, beispielsweise mit `\includegraphics{figures/model.pdf}` oder `\input{tables/statistics.tex}`.

Dadurch lässt sich die Analyse erneut ausführen, ohne den Berichtsstand zu verändern. Umgekehrt lässt sich der Bericht ohne Datenimport kompilieren. Für eine separate LaTeX-Umgebung kann der gesamte Ordner `report/` übernommen werden.

Stand 29.10.2026: Der Hauptteil enthält weiterhin Gliederung, Kommentare und `% TODO`-Platzhalter als Arbeitsgerüst, dazu faktische Tabellen und Stichpunkte: `sections/02_technical_setup.tex` (Werkzeuge mit Versionen und Fußnoten), `tables/raw_log_statistics.tex` und `tables/concepts.tex` (Abschnitt 2.2), `tables/quality_metrics.tex`, `tables/refined_quality.tex` und `tables/guarded_coverage.tex` (Abschnitt 2.3). Der Anhang enthält die drei entdeckten Petri-Netze (`figures/inductive_miner.pdf`, `figures/heuristics_miner.pdf`, `figures/genetic_miner.pdf`), `tables/discovery_setup.tex` und `sections/miner_parameters.tex`, `tables/raw_attribute_profile.tex` mit `figures/raw_log_overview.pdf` und `figures/raw_activity_frequencies.pdf`, `figures/refinement_tradeoff.pdf` mit `tables/literature_comparison.tex`, `tables/genetic_comparison.tex` mit `figures/genetic_comparison.pdf`, `figures/quality_comparison.pdf` und `figures/simplicity_comparison.pdf`, `tables/decision_metrics.tex`, `figures/final_bpmn.pdf` sowie `sections/decision_appendix.tex` mit `figures/decision_bpmn.pdf` und `figures/decision_blocks/D01.pdf`–`D16.pdf`. Insgesamt 10 Tabellen unter `tables/` und 11 PDFs plus 16 Regelblätter unter `figures/`; Alpha-Miner-, HM-Sweep- und Modellbewertungsergebnisse liegen bisher nur unter `../results/`. Eigene Interpretation, Abstract und Einleitung fehlen noch; Abschnitt 2.4 (3.4) ist leer. Literaturangaben werden mit BibTeX erzeugt.

Hauptteil und Parametertabellen verwenden A4. Die beiden vollständigen Modelltafeln stehen auf größeren A3-Seiten im Anhang, damit die Aktivitätsbeschriftungen lesbar bleiben; die eingebundenen PDFs sind Vektorgrafiken. `latexmkrc` führt BibTeX im Berichtsordner aus, um ungültige MSYS-Suchpfade zwischen Git-for-Windows-Perl und nativem MiKTeX zu vermeiden.

Die Qualitätsbewertung aus Aufgabe 3.3.2 hat eine ausgewählte faktische Tabelle
unter `tables/quality_metrics.tex` und zwei Vergleichsabbildungen unter
`figures/quality_comparison.pdf` und `figures/simplicity_comparison.pdf`.
Die Tabelle wird im Hauptteil eingebunden, die Grafiken im Anhang. Die
ursprünglichen Berechnungen und maschinenlesbaren Ergebnisse liegen getrennt
unter `../results/`; Definitionen und Einschränkungen stehen in `../docs/EVALUATION.md`.

Die wissenschaftliche Interpretation und die eigenen Berichtstexte sind noch zu
schreiben. Die Baselines sind noch kein finales BPMN-Modell. Die vollständige
Rohdatenstatistik aus 3.2 ist als ausgewählte Tabelle in Abschnitt 2.2 eingebunden;
Attributprofile und zwei statistische Abbildungen stehen im Anhang. Ihre Quellen
liegen unter `../results/`, Definitionen und Audit unter `../docs/STATISTICS.md`.

Die Verfeinerung aus 3.3.3 ist als `tables/refined_quality.tex` und
`tables/literature_comparison.tex` ausgewählt. Die Kandidatengrafik liegt unter
`figures/refinement_tradeoff.pdf`, das vollständige finale BPMN unter
`figures/final_bpmn.pdf`. Die lange BPMN-Grafik erhält im Anhang eine A2-Vektor-
Modelltafel; die beiden Discovery-Baselines bleiben auf A3. Die zugehörigen
Berechnungen, der unveränderte BPMN-2.0-XML-Export und die lokale bpmn-js-Ansicht
stehen getrennt unter `../results/refinement/`. Die wissenschaftliche
Interpretation bleibt eine eigene Schreibaufgabe; Methodik: `../docs/REFINEMENT.md`.

Decision Mining (3.3.4) ist als faktische Abdeckungstabelle, Testkennzahlen,
überlappende A3-Vektor-Panels des BPMN mit Entscheidungsblöcken und 16 einzelne
Regelblätter im Querformat ausgewählt. Herkunft und Prüfsummen stehen in
`../docs/decision_report_manifest.json`. Die zugehörigen Analyseskripte schreiben
weiterhin ausschließlich nach `../results/decision_mining/`; Reportkopien werden
separat ausgewählt. Die 80,45 % des Strukturmodells gelten ohne die experimentellen
Guards; harte Guards ergeben 10,19 % vollständige Testfallabdeckung. Die eigene
Interpretation dieser Grenze bleibt offen (`../docs/DECISION_MINING.md`).

Stand 30.10.2026 (Tutor-Feedback, Branch `assignment-feedback`): Neu ausgewählt
über `scripts/select_feedback_report.py` (Herkunft und Prüfsummen in
`../docs/feedback_report_manifest.json`): im Hauptteil `tables/conformance_to_edits.tex`,
`tables/single_edits.tex`, `tables/final_quality.tex`, `tables/holdout_check.tex` und
`tables/block_structure.tex`; im Anhang `tables/model_comparison.tex`,
`tables/soundness_summary.tex`, `tables/guard_stage.tex`, `tables/branch_probabilities.tex`,
`figures/alpha_miner.pdf`, `figures/heuristics_net.pdf`, `figures/final_edited_bpmn.pdf`
(finales Modell nach den manuellen Änderungen G3+R3+R4) und
`figures/branch_probabilities.pdf`. `figures/final_bpmn.pdf` zeigt jetzt das
verfeinerte Modell **vor** den manuellen Änderungen. Decision Mining wurde auf dem
finalen Modell neu gerechnet: 17 Regelblätter `figures/decision_blocks/D01.pdf`–`D17.pdf`;
Strukturabdeckung 79,39 %, harte Guards 10,07 % im Test. Die Absätze oben beschreiben
den Stand vor dieser Runde. Stichpunkte für die eigenen Texte stehen als
`%`-Kommentare in `sections/04_process_model.tex`; generierte Sätze enthält der Bericht nicht.
