# Veröffentlichte BPIC-17-Analysen

Recherche und Download: 16.10.2026.

Der BPIC-17-Log ist öffentlich. Die offizielle BPI-Challenge-Seite listet 23 Einreichungen und nennt Gewinner in drei Kategorien:
https://ais.win.tue.nl/bpi/2017/challenge.html

Hier liegen fünf unveränderte Originalberichte und ein separater GitHub-Code-Snapshot. Sie behandeln denselben Datensatz. Eine vollständige Übereinstimmung mit unserem konkreten Assignment ist nicht verifiziert. Die nachfolgende Zuordnung zur Aufgabe ist eine Einschätzung für unsere Literaturarbeit.

## Empfohlene Lesereihenfolge

Die Seitenzahlen beziehen sich auf die Seiten im PDF-Viewer, beginnend bei 1.

### 1. Akademischer Gewinner: Stairway to Value

[Lokales PDF](bpic2017/01_academic_winner_stairway_to_value.pdf) · [Originalquelle](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_academic.pdf)

Rodrigues et al., PUC-Rio, 2017; 30 Seiten.

Für die iterative Modellverfeinerung besonders relevant: Der Bericht beschreibt die Entwicklung von 19 Petri-Netz-Versionen und dokumentiert Fitness und Precision. Einstieg: PDF-Seite 3 für die Datenaufbereitung, Seiten 7–9 für Modellierung, Qualitätsvergleich und finales Modell. Die Autoren entfernen zunächst 100 unvollständige Fälle und verwenden auch gruppierte Aktivitäten. Die berichteten Qualitätswerte sind daher keine direkt übertragbaren Sollwerte für unseren unveränderten Log.

### 2. Frank Berger: Prozess und Lifecycle verstehen

[Lokales PDF](bpic2017/04_berger_loan_application_process.pdf) · [Originalquelle](https://ais.win.tue.nl/bpi/2017/bpi2017_paper_3.pdf)

Frank Berger, Exploras, 2017; 29 Seiten.

Erklärt die A-, O- und W-Aktivitäten sowie ihre Bedeutung im Kreditprozess. Behandelt Arbeits- und Wartezeiten und Prozesskennzahlen. Einstieg: PDF-Seiten 3–7, insbesondere die Interpretation der Workflow-Lifecycle-Zustände. Hilfreich für das Datenverständnis und begründete Zeitmessungen.

### 3. Ryu et al.: Entscheidungsstellen

[Lokales PDF](bpic2017/05_ryu_various_process_mining_techniques.pdf) · [Originalquelle](https://ais.win.tue.nl/bpi/2017/bpi2017_paper_31.pdf)

Dohyeon Ryu, Jitaek Lim, Dawoon Jeong und Minseok Song, POSTECH, 2017; 27 Seiten.

Abschnitt 7 untersucht Entscheidungsstellen und einen Entscheidungsbaum; siehe PDF-Seiten 14–16. Die Autoren untersuchen drei Entscheidungsstellen, erzielen aber nur für eine davon ein verwendbares Ergebnis. Der Bericht nennt 561.671 Events; unsere Originaldatei enthält 1.202.267. Datenbasis und Aufbereitung müssen vor einem Ergebnisvergleich geklärt werden. Das ist eine methodische Anregung, keine belegte Erfüllung aller XOR-Anforderungen unseres Assignments.

### 4. Professioneller Gewinner: KPMG

[Lokales PDF](bpic2017/02_professional_winner_kpmg.pdf) · [Originalquelle](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_professional.pdf)

Liese Blevi, Lucie Delporte und Julie Robbrecht, KPMG Technology Advisory, 2017; 33 Seiten.

Breite Untersuchung des Kreditprozesses mit Daten- und Prozessverständnis, deskriptiven Auswertungen und prädiktiven Analysen. Hilfreich als Beispiel für die Struktur einer umfassenden Analyse. Die Autoren verwenden unter anderem SQL, Power BI, Disco und ProM; ihre Werkzeugumgebung unterscheidet sich von unserer Python-Umgebung.

### 5. Studentischer Gewinner: Density Analysis

[Lokales PDF](bpic2017/03_student_winner_density_analysis.pdf) · [Originalquelle](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_student.pdf)

Elizaveta Povalyaeva, Ismail Khamitov und Artyom Fomenko, HSE, 2017; 28 Seiten.

Untersucht Kundeninteraktion und Wartezeiten und enthält ein BPMN-Modell. Einstieg: PDF-Seite 3 für das BPMN, Seiten 9–15 für Wartezeiten. Als Orientierung für verständliche Prozessdarstellung und weiterführende Analysefragen geeignet.

## Zusätzlich: Python-Codebeispiel

[GitHub-Original](https://github.com/hjonks/process-mining-project-bpi2017) · [Lokale README](code/hjonks/process-mining-project-bpi2017-f24496edf84a50ef4b39ef09d7ddcbafd6b64970/README.md)

Repository: `hjonks/process-mining-project-bpi2017`; heruntergeladener Commit: `f24496edf84a50ef4b39ef09d7ddcbafd6b64970`.

Der Snapshot enthält Python-Skripte für explorative Analyse, Kennzahlen und ML sowie Beispielabbildungen. Der Code wurde gelesen, aber nicht ausgeführt. Bei der Sichtung fallen konkrete Grenzen auf:

- `load_data()` kann bei fehlender XES-Datei oder Importfehlern auf synthetische Daten umschalten.
- `discover_process()` zählt Varianten und Aktivitäten; die Funktion entdeckt kein Petri-Netz mit einem Discovery-Algorithmus.
- `conformance_checking()` prüft selbst definierte Regeln für Start, Ende, Wiederholungen und Reihenfolge. Das ist keine Replay-/Alignment-Bewertung eines entdeckten Modells.

Damit eignet sich der Snapshot als Anschauungsmaterial für Codeorganisation und Tabellen. Seine Bezeichnungen und Ergebnisse sollten nicht als Erfüllung unserer Discovery- und Qualitätsanforderungen übernommen werden.

## Ablage und Herkunft

- `bpic2017/sources.json`: Original-URLs, Kategorien, Größen und SHA-256-Prüfsummen der fünf PDFs.
- `code_source.json`: Repository, exakter Commit, Archivquelle und Prüfsumme des Code-Snapshots.
- Die heruntergeladenen PDFs und fremden Quelldateien bleiben lokal; das Git-Repository enthält die Quellenübersicht und Metadaten.
- Die fremden Arbeiten liegen getrennt von `src/`, `results/` und dem eigenen Bericht unter `report/`.

Für unsere Arbeit halten wir je Quelle fest: verwendete Log-Version, Filter/Lifecycle-Auswahl, Methode und Parameter, berichtete Ergebnisse und Grenzen. Übernommene Erkenntnisse werden mit ihrer Quelle zitiert; eigene Ergebnisse werden auf unseren Daten reproduziert.
