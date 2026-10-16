# Aktuelle Codebasis

Die Codebasis deckt bisher Einrichtung, Datenbeschaffung, einen vollständigen Importcheck und den Einstieg über Jupyter ab. Discovery-Algorithmen, Qualitätsmetriken, Decision Mining und die Advanced-Analyse sind noch nicht implementiert.

## Wiederverwendbarer Python-Code: src/

`src/event_log.py` enthält `load_event_log()`. Die Funktion findet die Originaldatei relativ zum Projektordner, prüft ihre Existenz und lädt sie mit PM4Py. Der explizite Importer `iterparse` erzeugt ein `EventLog`. Es werden keine Aktivitäten, Fälle oder Lifecycle-Zustände gefiltert.

Ein `EventLog` enthält Fälle, auch Traces genannt. `log[0]` ist der erste Fall. `log[0].attributes` enthält Case-Attribute, etwa den beantragten Betrag. Die Events dieses Falls enthalten jeweils eigene Attribute, etwa Aktivitätsname und Zeitstempel.

`src/runtime.py` stellt Graphviz für den aktuellen Python-Prozess bereit und legt den matplotlib-Cache im lokalen, ignorierten Ordner `tmp/` ab. Es verändert keine permanenten System-Suchpfade. `src/__init__.py` kennzeichnet den Ordner als Python-Paket.

## Ausführbare Arbeitsschritte: scripts/

| Skript | Aufgabe |
|---|---|
| `setup.ps1` | Erstellt `.venv/`, installiert festgehaltene Paketversionen, registriert den lokalen Notebook-Kernel und richtet Graphviz ein |
| `setup_graphviz.py` | Lädt das offizielle Windows-ZIP, prüft seine SHA-256-Prüfsumme und entpackt es nach `.tools/graphviz/` |
| `check_setup.py` | Prüft Bibliotheksimporte, SVG-/PNG-Rendering, Notebook-Format und Registrierung des Jupyter-Kernels |
| `download_data.py` | Beschafft Originaldateien und prüft Größe sowie Quell-MD5; dokumentiert zusätzlich lokale SHA-256-Prüfsummen |
| `inspect_log.py` | Lädt alle Fälle, zählt Events und Aktivitätsnamen, prüft notwendige Felder auf fehlende Werte und exportiert eine Fallvorschau |
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
- `results/figures/` und `results/models/`: Platz für später erzeugte Diagramme und Prozessmodelle.
- `requirements.in`: direkte Abhängigkeiten, etwa PM4Py und JupyterLab.
- `requirements.txt`: konkret installierte Versionen einschließlich weiterer Abhängigkeiten.
- `.venv/`, `.tools/` und `tmp/`: lokale Umgebung, Werkzeuge und temporäre Dateien; nicht in Git.

## Eigenständiger Bericht: report/

Alle LaTeX-Quellen, Literaturangaben, ausgewählten Abbildungen und Tabellen sowie das Bericht-Buildskript liegen unter `report/`. Der Build führt keinen Python-Code aus und liest keinen Event Log. Details stehen in `report/README.md`.

Der Arbeitsfluss ist: Originaldaten → Python-Import/Analyse → Ergebnisse unter `results/` → bewusste Auswahl für `report/figures/` und `report/tables/` → LaTeX-PDF. Eine erneute Analyse überschreibt den Bericht nicht.
