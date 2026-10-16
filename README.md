# BPIC-17 Process Mining

Gemeinsames Repository für Assignment I: Python-Analyse, Prozessmodelle und LaTeX-Bericht.

GitHub: https://github.com/Marcikschmid/bpic17-process-mining

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

Der unveränderte Log wird mit dem expliziten PM4Py-Importer `iterparse` als `EventLog` geladen. Bisher werden keine Lifecycle-Zustände oder Aktivitäten gefiltert. `results/tables/import_summary.json` dokumentiert den Import und `results/tables/first_case.csv` enthält den ersten Fall in der gespeicherten Event-Reihenfolge. Die vollständige Analyse aus Abschnitt 3.2 folgt anschließend.

Der erste Import wurde erfolgreich geprüft: **31.509 Cases**, **1.202.267 Events** und **26 unterschiedliche Aktivitätsnamen**. Die notwendigen Case-IDs, Aktivitätsnamen und Event-Zeitstempel sind im Importcheck vollständig vorhanden. Der erste vollständige Import dauerte auf diesem Rechner ungefähr zweieinhalb Minuten.

Die Umgebung lässt sich jederzeit prüfen:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_setup.py
```

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

## Abgabe

Der Bericht ist auf Englisch und umfasst höchstens fünf Seiten ohne Literatur und Anhang. Code und Parameter müssen nachvollziehbar sein; bei Zufallsverfahren sind Seeds festzuhalten. Bibliotheken und Werkzeuge werden entsprechend der Aufgabenstellung referenziert. Die KI-Nutzung wird unter `docs/AI_USAGE.md` protokolliert und später im Bericht deklariert. Ganze Berichtssätze oder Absätze sollen laut Aufgabenstellung nicht von GenAI erzeugt werden.

## Git im Alltag

```powershell
git status
git add <Dateien>
git commit -m "Describe the completed change"
git push
```

Die Lizenzangaben in den übernommenen TUM-Dateien gelten für diese Dateien. Dieses Repository vergibt keine zusätzliche Lizenz für die Kursunterlagen.
