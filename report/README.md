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

Erst wenn ein Ergebnis für die Abgabe ausgewählt wurde, wird die passende Abbildung nach `report/figures/` beziehungsweise eine fertige LaTeX-Tabelle nach `report/tables/` kopiert. Diese Auswahl erfolgt bewusst; es gibt derzeit keinen automatischen Kopier- oder Exportprozess. Im Bericht werden nur diese lokalen Dateien referenziert, beispielsweise mit `\includegraphics{figures/model.pdf}` oder `\input{tables/statistics.tex}`.

Dadurch lässt sich die Analyse erneut ausführen, ohne den Berichtsstand zu verändern. Umgekehrt lässt sich der Bericht ohne Datenimport kompilieren. Für eine separate LaTeX-Umgebung kann der gesamte Ordner `report/` übernommen werden.

Der Hauptteil enthält weiterhin die Gliederung und Kommentare als Arbeitsgerüst. Der Anhang enthält die beiden entdeckten Petri-Netze (Inductive Miner und Heuristics Miner) sowie faktische Tabellen zur gemeinsamen Eingabe, zu den Parametern und zu den Modellgrößen. Die ausgewählten PDFs liegen unter `figures/`, die Tabellenkopie unter `tables/discovery_setup.tex`. Literaturangaben werden mit BibTeX erzeugt.

Hauptteil und Parametertabellen verwenden A4. Die beiden vollständigen Modelltafeln stehen auf größeren A3-Seiten im Anhang, damit die Aktivitätsbeschriftungen lesbar bleiben; die eingebundenen PDFs sind Vektorgrafiken. `latexmkrc` führt BibTeX im Berichtsordner aus, um ungültige MSYS-Suchpfade zwischen Git-for-Windows-Perl und nativem MiKTeX zu vermeiden.

Die wissenschaftliche Interpretation und die eigenen Berichtstexte sind noch zu schreiben. Die Baseline-Modelle sind noch nicht mit Qualitätsmetriken bewertet und noch kein finales BPMN-Modell.
