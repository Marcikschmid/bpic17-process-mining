# BPIC-17 Process Mining

Gemeinsames Repository für Assignment I: Python-Analyse, Prozessmodelle und LaTeX-Bericht.

GitHub: https://github.com/Marcikschmid/bpic17-process-mining

## Struktur

- `1 Introduction/`, `2 Process Mining/`, `Allgemeines/`, `index.html`: unveränderte Kursunterlagen inklusive Aufgabenstellung und Originalvorlage.
- `src/`: Python-Code für Analyse, Discovery, Qualitätsmetriken und Decision Mining.
- `notebooks/`: explorative Untersuchungen.
- `data/raw/`: heruntergeladener Originaldatensatz; lokal vorhanden, über das Download-Skript reproduzierbar.
- `data/processed/`: aus dem Originaldatensatz erzeugte Arbeitsdaten.
- `results/figures/`, `results/tables/`, `results/models/`: erzeugte Ergebnisse für den Bericht.
- `report/`: LaTeX-Bericht auf Basis der bereitgestellten TUM-Vorlage.
- `docs/`: Aufgabencheckliste, Arbeitsnotizen und Protokoll der KI-Nutzung.
- `scripts/download_data.py`: Download und Integritätsprüfung der Originaldaten.

Große Datensätze, virtuelle Umgebungen und LaTeX-Hilfsdateien werden nicht in Git gespeichert. Die Datenbeschaffung wird in `data/README.md` dokumentiert. Die vorhandenen Kursunterlagen sind dagegen vollständig enthalten.

## Arbeitsablauf

1. GitHub-Repository verbinden und den ersten Stand hochladen.
2. BPIC-17 beschaffen und Quelle, Lizenz und Prüfsumme dokumentieren.
3. Python-Umgebung einrichten und die tatsächlich verwendeten Paketversionen festhalten.
4. Daten prüfen und einfache Event-Log-Statistiken berechnen.
5. Discovery, Qualitätsbewertung und Modellverfeinerung durchführen.
6. Decision Mining und gegebenenfalls die Advanced-Aufgabe bearbeiten.
7. Eigene englische Berichtstexte parallel unter `report/sections/` schreiben.

## Python-Umgebung

Nach der Datenbeschaffung wird eine lokale Umgebung mit PM4Py, pandas und matplotlib eingerichtet. Zu diesem Stand ist noch keine Analyse implementiert und keine Paketliste festgeschrieben.

## LaTeX

Die Datei `Allgemeines/Assignment Template.imscc` ist ein ZIP-Archiv mit der originalen LaTeX-Vorlage. Ihre Klassen, Stile und Ressourcen liegen unter `report/`. Das Arbeitsdokument enthält zunächst nur die Gliederung und Kommentare; die ursprüngliche Vorlage bleibt im Archiv erhalten.

Mit einer lokalen TeX-Installation und Latexmk, aus dem Repository-Hauptordner:

```powershell
Set-Location report
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
Set-Location ..
```

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
