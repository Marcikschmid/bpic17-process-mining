# BPIC-17 Process Mining

Gemeinsames Repository für Assignment I: Python-Analyse, Prozessmodelle und LaTeX-Bericht.

GitHub: https://github.com/Marcikschmid/bpic17-process-mining

## Arbeitsordner prüfen

Öffne in VS Code den Repository-Hauptordner mit `.git`, `src/`, `report/` und dieser README. `git rev-parse --show-toplevel` zeigt den richtigen Arbeitsordner an. Nach einem Verschieben des Projekts muss der projektlokale Jupyter-Kernel neu registriert werden:

```powershell
.\.venv\Scripts\python.exe -m ipykernel install --prefix .venv --name bpic17 --display-name "BPIC17 (.venv)"
```

## Struktur

- `1 Introduction/`, `2 Process Mining/`, `Allgemeines/`, `index.html`: unveränderte Kursunterlagen inklusive Aufgabenstellung und Originalvorlage.
- `src/`: Python-Code für Analyse, Discovery, Qualitätsmetriken und Decision Mining.
- `notebooks/`: explorative Untersuchungen.
- `data/raw/`: heruntergeladener Originaldatensatz; lokal vorhanden, über das Download-Skript reproduzierbar.
- `data/processed/`: aus dem Originaldatensatz erzeugte Arbeitsdaten.
- `results/figures/`, `results/tables/`, `results/models/`: durch die Analyse erzeugte Ergebnisse.
- `report/`: eigenständiges LaTeX-Projekt mit Berichtstexten und ausgewählten Abbildungen/Tabellen für die Abgabe.
- `docs/`: Aufgabencheckliste, Arbeitsnotizen und Protokoll der KI-Nutzung.
- `literature/`: separate Sammlung veröffentlichter BPIC-17-Analysen mit Quellenübersicht; heruntergeladene Originale bleiben lokal.
- `scripts/download_data.py`: Download und Integritätsprüfung der Originaldaten.
- `scripts/setup.ps1`: lokale Python-Umgebung und Graphviz reproduzieren.
- `scripts/inspect_log.py`: vollständigen Log laden und eine Vorschau des ersten Falls exportieren.

Große Datensätze, virtuelle Umgebungen und LaTeX-Hilfsdateien werden nicht in Git gespeichert. Die Datenbeschaffung wird in `data/README.md` dokumentiert. Die vorhandenen Kursunterlagen sind dagegen vollständig enthalten.

Die Codebasis ist in `docs/CODEBASE.md` erklärt. Der Berichtsbereich besitzt eine eigene Anleitung in `report/README.md`. Die Analyse liest aus `data/` und schreibt nach `results/`; für die Abgabe ausgewählte Ergebnisse werden bei Bedarf manuell nach `report/figures/` oder `report/tables/` kopiert. Der Bericht wird unabhängig von Python und Jupyter kompiliert.

## Arbeitsablauf

1. GitHub-Repository verbinden und den ersten Stand hochladen.
2. BPIC-17 beschaffen und Quelle, Lizenz und Prüfsumme dokumentieren.
3. Python-Umgebung einrichten und die tatsächlich verwendeten Paketversionen festhalten.
4. Daten prüfen und einfache Event-Log-Statistiken berechnen.
5. Discovery, Qualitätsbewertung und Modellverfeinerung durchführen.
6. Decision Mining und gegebenenfalls die Advanced-Aufgabe bearbeiten.
7. Eigene englische Berichtstexte parallel unter `report/sections/` schreiben.

## Python-Umgebung

Verwendet wird Python 3.12 in `.venv/`. Die direkten Abhängigkeiten stehen in `requirements.in`; `requirements.txt` hält die tatsächlich installierten Paketversionen fest. Enthalten sind PM4Py, pandas, matplotlib, scikit-learn, JupyterLab und ipykernel.

Graphviz liegt als portable Windows-Version unter `.tools/graphviz/`. Python-Code aus `src/` ergänzt dessen Verzeichnis nur für den aktuellen Prozess zum Suchpfad. Das Skript `scripts/setup_graphviz.py` lädt das offizielle, auf https://graphviz.org/download/ verlinkte ZIP und prüft dessen veröffentlichte SHA-256-Prüfsumme. Quelle und Version stehen in `docs/graphviz_manifest.json`.

Um die Umgebung auf Windows mit Python 3.12 nachzubauen:

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\python.exe scripts/download_data.py
.\.venv\Scripts\python.exe scripts/inspect_log.py
```

Das Setup registriert den Kernel **BPIC17 (.venv)** ausschließlich innerhalb von `.venv/`. Eine Aktivierung der virtuellen Umgebung oder eine globale Kernel-Installation ist nicht erforderlich. Die Paketliste wurde unter Windows mit Python 3.12 erstellt; unter anderen Betriebssystemen können zusätzliche Anpassungen erforderlich sein.

## Mit dem Notebook beginnen

Aus dem Repository-Hauptordner:

```powershell
.\scripts\start_jupyter.ps1
```

Oeffne den ausgegebenen `http://localhost:...`-Link im Browser. Das Startskript verwendet den gesamten Projektordner als Jupyter-Wurzel und oeffnet das Einstiegsnotebook. Es verzichtet auf die automatische HTML-Weiterleitungsseite. Das Terminal muss waehrend der Arbeit laufen; weitere Befehle gehoeren in ein zweites Terminal. Zum Beenden `Strg+C` druecken und die Rueckfrage bestaetigen. Eine Aktivierung der Umgebung ist nicht notwendig.

Alternativ direkt mit Python:

```powershell
.\.venv\Scripts\python.exe -m jupyterlab --no-browser --ServerApp.root_dir=. --ServerApp.default_url=/lab/tree/notebooks/01_getting_started.ipynb
```

Wähle den Kernel **BPIC17 (.venv)** und führe die Zellen der Reihe nach aus. Das Notebook zeigt Case-Attribute und die Events eines einzelnen Antrags. Der erste vollständige Import kann etwas Zeit und Arbeitsspeicher benötigen.

Der unveränderte Log wird mit dem expliziten PM4Py-Importer `iterparse` als `EventLog` geladen. Das Einstiegsnotebook und der Importcheck filtern keine Lifecycle-Zustände oder Aktivitäten. `results/tables/import_summary.json` dokumentiert den Import und `results/tables/first_case.csv` enthält den ersten Fall in der gespeicherten Event-Reihenfolge. Die vollständige Analyse aus Abschnitt 3.2 folgt anschließend.

Der erste Import wurde erfolgreich geprüft: **31.509 Cases**, **1.202.267 Events** und **26 unterschiedliche Aktivitätsnamen**. Die notwendigen Case-IDs, Aktivitätsnamen und Event-Zeitstempel sind im Importcheck vollständig vorhanden. Der erste vollständige Import dauerte auf diesem Rechner ungefähr zweieinhalb Minuten.

Die Umgebung lässt sich jederzeit prüfen:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_setup.py
```

## Zwei Discovery-Verfahren (Abschnitt 3.3, Aufgabe 1)

```powershell
.\.venv\Scripts\python.exe scripts/discover_models.py
```

Inductive Miner (IM, Noise Threshold 0.0) und Heuristics Miner (CLASSIC) verwenden dieselbe Completion-Projektion aller Fälle. Nur `complete`-Events gehen in die Discovery ein; der ursprüngliche Log bleibt unverändert. Parameter, Ausschlüsse und Grenzen sind in `docs/DISCOVERY.md` dokumentiert. Die Modelle liegen als PNML unter `results/models/`, die Abbildungen als PDF, SVG und PNG unter `results/figures/`; das Manifest steht unter `results/tables/discovery_manifest.json`.

Das Skript verändert `report/` nicht. Ausgewählte PDF-Kopien liegen separat unter `report/figures/` und sind im Anhang eingebunden. Fitness, Precision, Generalization, Simplicity und Case-Replay-Abdeckung sind anschließend zu berechnen.

## LaTeX

Die Datei `Allgemeines/Assignment Template.imscc` ist ein ZIP-Archiv mit der originalen LaTeX-Vorlage. Ihre Klassen, Stile und Ressourcen liegen unter `report/`. Das Arbeitsdokument enthält zunächst nur die Gliederung und Kommentare; die ursprüngliche Vorlage bleibt im Archiv erhalten.

Mit einer lokalen TeX-Installation und Latexmk, aus dem Repository-Hauptordner:

```powershell
Set-Location report
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
Set-Location ..
```

Alternativ erledigt `.\report\build.ps1` den Build einschließlich des lokalen Perl-Suchpfads. Alle Berichtstexte, Abgabe-Abbildungen, Tabellen und die Build-Konfiguration liegen unter `report/`; die Python-Skripte gehören zum getrennten Analysebereich.

Auf diesem Windows-Rechner ist Perl über Git for Windows verfügbar. Falls Latexmk meldet, dass Perl fehlt, ergänze vor dem Build für die aktuelle PowerShell-Sitzung:

```powershell
$env:PATH = 'C:\Program Files\Git\usr\bin;' + $env:PATH
```

Bei einer frischen MiKTeX-Installation kann der erste Build zusätzliche LaTeX-Pakete benötigen. Der Paketinstaller lässt sich für den Build explizit aktivieren:

```powershell
Set-Location report
latexmk -pdf -pdflatex='pdflatex -enable-installer %O %S' -interaction=nonstopmode -halt-on-error main.tex
Set-Location ..
```

Die Ausgabe liegt unter `report/build/main.pdf`. Der ganze Ordner `report/` kann auch als LaTeX-Projekt verwendet werden; die TUM-Dateien und `latexmkrc` müssen dabei mitgenommen werden.

## Rohdatenstatistik (Assignment 3.2)

```powershell
.\.venv\Scripts\python.exe scripts/analyze_log.py
.\.venv\Scripts\python.exe scripts/render_log_statistics.py
.\.venv\Scripts\python.exe scripts/verify_log_statistics.py
```

Ergebnisse: [`results/tables/raw_log_statistics.md`](results/tables/raw_log_statistics.md).
Die vollständige Rohdatei enthält 31.509 Fälle, 1.202.267 Events und 15.930
Aktivitätsvarianten. Alle Pflichtstatistiken, Attributklassifikation und zusätzliche
Häufigkeits-/Verteilungsanalysen sind in [`docs/STATISTICS.md`](docs/STATISTICS.md)
erläutert. Ein unabhängiger XML-Audit hat alle Fälle und Events überprüft.
Ausgewählte statische Tabellen und Abbildungen sind im getrennten LaTeX-Bericht.

## Verfeinertes BPMN (Assignment 3.3.3)

Das ausgewählte Modell erreicht **25.350/31.509 vollständig replaybare Fälle
(80,4532 %)**. Definitionen, Iterationen, Qualitätswerte und der Vergleich mit
veröffentlichten Originalberichten: [`docs/REFINEMENT.md`](docs/REFINEMENT.md).

Die lokale Software bpmn-js zeigt das BPMN an und unterstützt Bearbeitung sowie
BPMN-/SVG-Export. Einmalig bei fehlenden lokalen Bibliotheken:

```powershell
.\.venv\Scripts\python.exe scripts/setup_bpmn_viewer.py
.\.venv\Scripts\python.exe -m http.server 8787 --bind 127.0.0.1
```

Öffnen: <http://127.0.0.1:8787/results/refinement/index.html>.
Ergebnisse: [`results/refinement/refinement_summary.md`](results/refinement/refinement_summary.md).
Die Original-Baselines bleiben erhalten; ausgewählte Kopien stehen im Bericht.

## Abgabe

Die Qualitätsbewertung der beiden Discovery-Baselines (Aufgabe 3.3.2) ist unter
[`docs/EVALUATION.md`](docs/EVALUATION.md) beschrieben. Start:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_models.py
.\.venv\Scripts\python.exe scripts/audit_dead_transitions.py
.\.venv\Scripts\python.exe scripts/render_evaluation.py
.\.venv\Scripts\python.exe scripts/verify_evaluation.py
```

Ergebnisse: `results/tables/quality_metrics.csv` und die Vergleichsgrafiken unter
`results/figures/`. Die vollständige Rohdatenanalyse aus Abschnitt 3.2 ist getrennt unter
[`docs/STATISTICS.md`](docs/STATISTICS.md) dokumentiert.

`verify_evaluation.py` prüft standardmäßig auch vollständige Alignment-Fitness.
Für einen dokumentierten unvollständigen Zusatzlauf erlaubt
`--allow-incomplete-alignment` die Prüfung aller tatsächlich berichteten Werte;
die Lücke bleibt im Audit ausdrücklich sichtbar.

Der Bericht ist auf Englisch und umfasst höchstens fünf Seiten ohne Literatur und Anhang. Code und Parameter müssen nachvollziehbar sein; bei Zufallsverfahren sind Seeds festzuhalten. Bibliotheken und Werkzeuge werden entsprechend der Aufgabenstellung referenziert. Die KI-Nutzung wird unter `docs/AI_USAGE.md` protokolliert und später im Bericht deklariert. Ganze Berichtssätze oder Absätze sollen laut Aufgabenstellung nicht von GenAI erzeugt werden.

## Git im Alltag

```powershell
git status
git add <Dateien>
git commit -m "Describe the completed change"
git push
```

Die Lizenzangaben in den übernommenen TUM-Dateien gelten für diese Dateien. Dieses Repository vergibt keine zusätzliche Lizenz für die Kursunterlagen.
## Decision Mining (3.3.4)

Alle 16 XOR-Splits haben erklärbare Entscheidungsbäume und geprüfte Bedingungen;
16 XOR-Merges sind separat gekennzeichnet. [Methode und Grenzen](docs/DECISION_MINING.md).
Bei laufendem lokalen Server: [Ergebnisse und Bäume](http://127.0.0.1:8787/results/decision_mining/index.html)
und [BPMN mit Bedingungen](http://127.0.0.1:8787/results/decision_mining/viewer.html).
Die experimentellen harten Guards erreichen 10,19 % vollständige Testfallabdeckung;
die 80,45 % des bisherigen Modells beziehen sich auf dessen Struktur ohne Guards.
