# Decision Mining: Assignment 3.3.4

## Ergebnis und Grenzen

Alle **32 XOR-Gateways** des finalen BPMN sind erfasst: **16 Splits** mit gelernten
Entscheidungsblöcken und **16 Merges** ohne Auswahlentscheidung. Die Regeln stammen
aus **453.820 ausgerichteten Entscheidungsereignissen** aller 31.509 Fälle und
5.623 Varianten. Wiederholte Schleifendurchläufe zählen als einzelne Entscheidungen.

Die Ergebnisansicht bietet je Split einen grafischen Entscheidungsbaum, alle
Regelpfade, Häufigkeiten, Testkennzahlen und einen Vergleich mit der Mehrheitsklasse:

- <http://127.0.0.1:8787/results/decision_mining/index.html>
- Interaktives BPMN: <http://127.0.0.1:8787/results/decision_mining/viewer.html>
- `results/decision_mining/decision_blocks.pdf`: alle 16 Entscheidungsblöcke.
- `results/decision_mining/decision_model.bpmn`: separates BPMN mit experimentellen
  FEEL-Bedingungen und Textannotationen; `isExecutable=false`.
- `results/decision_mining/decision_bpmn.pdf`: Vektorübersicht mit verknüpften Blöcken.
- `results/decision_mining/summary.csv` und `decision_mining.json`: Kennzahlen und
  sämtliche Parameter, Blattverteilungen und Grenzen.

Die Regeln stehen jetzt auch **direkt in den Textblöcken am jeweiligen XOR-Split**
des BPMN und in seiner PDF-Grafik. `B1`/`B2` verknüpfen die ausgehenden Pfeile mit
den Bedingungen im Block. Gleich vorhersagende Teilbäume werden für die Anzeige
zu gemeinsamen Regelpfaden zusammengefasst; ein vollständiger Präfixabgleich
gegen sämtliche ursprünglichen Blattpfade sichert dieselbe Klassifikation.
Die formalen Bedingungen in der BPMN-Datei bleiben unverändert.

**Die Regeln sind keine validierten Geschäftsregeln der Bank.** Ihre Test-Accuracy
liegt je Split ungefähr zwischen 0,542 und 0,922. Mehrere Bäume verbessern die
Mehrheitsvorhersage kaum; sechs Bäume sagen einen Minderheitszweig überhaupt nicht
vorher. Deshalb werden Accuracy, Macro-F1, Balanced Accuracy, Zweighäufigkeiten und
nicht vorhergesagte Zweige gemeinsam ausgewiesen.

Wird jeder Baum als harte Routingbedingung erzwungen, können **3.277 / 31.509 Fälle
(10,40 %)** vollständig replayt werden. Im getrennten Test sind es **963 / 9.453
(10,19 %)**; im Training 2.314 / 22.056 (10,49 %). Das wurde durch vollständiges
guardabhängiges Tau-/NFA-Replay aller Fälle geprüft, mit allen erlaubten Pfaden,
ohne Token-Einfügung und ohne Beschränkung auf das eine gewählte Alignment.

Die **80,4532 %** aus 3.3.3 betreffen das Kontrollflussmodell **ohne** diese Guards.
Dessen PNML, BPMN und Qualitätswerte bleiben erhalten. Die bisherigen Precision-,
Generalization- und Simplicity-Werte werden dem experimentellen Guard-Modell nicht
als neu gemessene Werte zugeschrieben. Für realistische Simulation sind zusätzliche
Informationen oder probabilistische Entscheidungen zu prüfen; die gelernten
Mehrheitsregeln reichen dafür nicht aus. Das Modell wird nicht als deploybare
Camunda-Anwendung ausgegeben.

## Bezug zum vorgegebenen Paper

de Leoni und van der Aalst (2013), *Data-Aware Process Mining: Discovering Decisions
in Processes Using Alignments*, DOI
[10.1145/2480362.2480633](https://doi.org/10.1145/2480362.2480633),
[Original beim Autor](https://vdaalst.com/publications/p741.pdf).

Umgesetzt ist die Reihenfolge aus Algorithmus 1:

1. Optimales vollständiges Kontrollfluss-Alignment bestimmen.
2. Vor dem Feuern einer Konflikttransition den aktuellen Variablenzustand und den
   gewählten Zweig speichern, einschließlich unsichtbarer Routingtransitionen.
3. Eingaben erst **nach synchronen Schritten** aktualisieren. Log-only- und
   Model-only-Schritte schreiben keine beobachteten Datenwerte in den Modellzustand.
4. Je Entscheidungspunkt einen erklärbaren Klassifikator lernen; Blattpfade als
   disjunkte Bedingungen exportieren.

Das Paper verwendet C4.5. Hier wird ausdrücklich **scikit-learn CART** verwendet,
mit One-Hot-Kodierung und expliziter Missingness. Die Alignment-/Snapshot-Methode
folgt dem Paper; dies ist keine Behauptung einer identischen C4.5-Replikation.

## Modell, Alignments und Mehrdeutigkeit

`src/decision_mining.py:bpmn_net` übersetzt die im finalen Modell vorhandenen Tasks,
Start-/Endereignisse, XORs und parallelen Gateways in gewöhnliche P/T-Semantik.
Sequenzflüsse werden zu Places. Jeder ausgehende XOR-Zweig erhält eine eigene,
über stabile BPMN-IDs identifizierbare Transition. Unbekannte Konstrukte werden
abgewiesen. Die 1.357 erreichbaren Markierungen sind vollständig enumeriert.
Die gesamte Kontrollflusssprache ist zum geprüften finalen PNML äquivalent
(57 determinisierte Zustandspaare); es handelt sich nicht nur um einen Stichprobenvergleich.

`src/finite_alignment.py` berechnet mit Dijkstra für jede vollständige Variante
ein optimales Alignment im Produkt aus Eventposition und Markierung. Kosten:
sync 0, tau 1, sichtbarer Modell-/Log-Schritt 10.000. Keine Zeitgrenze,
Stichprobe, Beam-Suche oder eingefügten Tokens. Alle Alignments werden anhand
der tatsächlichen Vor-/Nachbedingungen replayt; 24 reale Varianten zusätzlich
gegen PM4Pys unveränderten `DIJKSTRA_LESS_MEMORY` mit explizit denselben Kosten
geprüft. Unit-Tests vergleichen auch mit PM4Pys A*-Algorithmus.

Bei gleichen optimalen Kosten wird nach stabilen Knoten-/Transitionsnamen
deterministisch entschieden. Es werden **nicht alle optimalen Alignments** gelernt.
Alternative Alignments, besonders bei optionalen Tasks und Parallelität, können
andere Zweigzuordnungen und verfügbare Variablen ergeben. Der Ausgabezeitpunkt
des unsichtbaren Split-Schritts innerhalb des gewählten Alignments definiert hier
den Entscheidungszeitpunkt. Die resultierenden Regeln sind entsprechend bedingt
auf diese Kontrollflussinterpretation.

## Datenverfügbarkeit und Feature-Auswahl

Zu Fallbeginn verfügbar: `ApplicationType`, `LoanGoal`, `RequestedAmount` aus
den Trace-Attributen. Diese Verfügbarkeitsannahme ist fachlich zu prüfen.
Nach synchronem `O_Create Offer`: `CreditScore`, `FirstWithdrawalAmount`,
`MonthlyCost`, `NumberOfTerms`, `OfferedAmount`. Diese fünf Felder stehen in allen
42.995 entsprechenden Completion-Events; die dokumentierte Schwelle zum Erkennen
einer Schreiboperation beträgt 95 %. Andere Aktivitäten schreiben diese Felder
im betrachteten Log nicht.

Verwendet wird jeweils der zuletzt synchron beobachtete Wert, nicht der letzte
Wert des gesamten Falls. Fehlende numerische Eingaben erhalten -1 und zusätzliche
`*_known`-Indikatoren. Numerische Rohwerte werden auf Nichtnegativität geprüft.
Kategoriale Kodierung wird nur auf Trainingsfällen gelernt; unbekannte Kategorien
im Test erzeugen keine neue Spalte.

Bewusst ausgeschlossen: Case-/Event-/Offer-IDs, `Accepted`, `Selected`, aktuelle
Aktivitätsnamen, Ressourcen, `Action`, `EventOrigin` und Zeitstempel. Insbesondere
`Accepted`/`Selected` können eine retrospektive Ergebnisinformation enthalten.
Mehrere Angebote pro Fall werden nicht objektzentriert korreliert: Der letzte
beobachtete Angebotswert kann fachlich zu einem anderen Angebot gehören. Das ist
eine verbleibende Einschränkung, keine nachgewiesene Kausalregel.

## Training, Test und Bedingungen

Ein globaler Fall-Split: **70/30**, `random_state=20261018`; 22.056 Trainingsfälle,
9.453 Testfälle. Alle Wiederholungen eines Falls bleiben in derselben Gruppe und
bei sämtlichen Gateways in derselben Teilmenge. `case_split.json` speichert die IDs.
Die Kontrollflussstruktur wurde zuvor mit dem vollständigen Log ausgewählt;
die Testwerte bewerten daher nur das Lernen der Guards auf diesem festen Modell,
nicht die Generalisierung der gesamten Discovery-Pipeline.

`DictVectorizer(sparse=False)`; `DecisionTreeClassifier(max_depth=3,
min_samples_leaf=50, random_state=20261018)`, sonst dokumentierte sklearn-Defaults,
keine Testdaten zur Hyperparameterwahl, kein nachträgliches Refit auf Testdaten.
Macro-F1 umfasst alle strukturellen Zweige, einschließlich unvorhergesagter Klassen.
Die Mehrheitsbaseline wird ausschließlich aus dem jeweiligen Training bestimmt.

Blattpfade stehen mit voller Schwellengenauigkeit in JSON. Sie wurden für alle
453.820 Beobachtungen gegen den trainierten Baum geprüft. Die Klassifikation
verwendet wie sklearn float32-Eingaben. FEEL exportiert entsprechende numerische
Trennschwellen und explizite Nullbehandlung; dieser Export ist nicht in einer
Workflow-Engine zertifiziert. Der Python-Guard-Replay verwendet die tatsächlich
auditierten Baumregeln. Ein nie vorhergesagter Zweig erhält im experimentellen
BPMN `false`; das bedeutet **nicht**, dass dieser Ablauf fachlich unmöglich ist.

## Prüfen und reproduzieren

```powershell
.\.venv\Scripts\python.exe scripts/mine_decisions.py
.\.venv\Scripts\python.exe scripts/render_decisions.py
.\.venv\Scripts\python.exe scripts/verify_decisions.py
.\.venv\Scripts\python.exe -m unittest tests.test_decision_mining -v
# Bewusste Auswahl der geprüften Reportkopien, danach separat kompilieren:
.\.venv\Scripts\python.exe scripts/select_decision_report.py
& ./report/build.ps1
```

Checkpoints liegen unter `tmp/decision_mining/`. Ein frischer Lauf benötigt die
Rohdaten, das finale Modell und den aus der Discovery vorbereiteten Sequenzcache.
Die Basismodelle werden nicht verändert. Normale Analyse-/Renderbefehle schreiben
nicht nach `report/`; die dortigen Kopien werden bewusst separat ausgewählt.
Die sechs neuen Tests prüfen Kosten gegen PM4Py, parallele Pfade, Schleifen,
Limits, unbekannte Kategorien, vollständige Sprachäquivalenz und zukünftige Daten.
Der Audit prüft alle Vorhersagen, alle Bedingungen, die Falltrennung und rekonstruiert
sämtliche Snapshots aus der unveränderten Rohdatei.

Die gesamte Suite besteht aus **42 bestandenen Tests**. Der abschließende Audit
prüft zudem die numerischen exportierten Guard-Prädikate für sämtliche 453.820
Beobachtungen; eine Zertifizierung in einer externen FEEL-Engine ist damit nicht
verbunden. Nach rein grafischen Änderungen kann
`scripts/verify_decisions.py --artifacts-only` die bestehenden wissenschaftlichen
Prüfungen, neuen Render-Prüfsummen und ausgewählten Berichtskopien abgleichen.
