# Qualitätsbewertung: Assignment 3.3.2

**Stand:** Die vier Qualitätsdimensionen sind für beide Modelle auf der gesamten
Projektion berechnet: Token-Fitness, Token-/Alignment-Precision, Token-Generalization
und Simplicity. Die zusätzliche optimale Alignment-Fitness ist beim IM vollständig,
beim HM unvollständig. Ein serieller Lauf lieferte 21.501 vollständige Fallwerte;
ein weiterer Acht-Prozess-Lauf wurde nach rund 66 Minuten ohne zurückgegebenes
Gesamtergebnis beendet. Auf ausdrücklichen Nutzerwunsch läuft jetzt eine erneute
vollständige Berechnung ohne weitere Zeitgrenze, mit dauerhaften Checkpoints
pro Variante. Bis zu ihrem Abschluss wird kein Teilmengenmittelwert angegeben.

## Eingabe und Abgrenzung

Aktueller Wiederanlauf am 18.10.2026: 654 fertige Varianten mit 22.578 Fällen
übernommen. Wegen nahezu vollständig belegtem physischen RAM wurde der Lauf von
vier auf **zwei Worker** umgestellt. Log:
`tmp/evaluation/heuristics_miner_alignment_unlimited_2.log`; keine weitere
Zeitgrenze. Die automatische Nachbereitung wartet auf Prozess 16200 und akzeptiert
nur ein vollständiges Ergebnis für beide Modelle. Bis dahin ist die zusätzliche
HM-Alignment-Fitness weiterhin offen; die vier vorhandenen Qualitätsdimensionen
werden nicht durch einen Mittelwert aus den fertigen Checkpoints ersetzt.

Weitere Beschleunigungsproben: zusätzliche vorwärts/rückwärts monotone
Markierungsschranken begrenzen nur sieben von 49 Places; kaskadierte Dead-Transition-
Zertifikate entfernen 13 Transitionen, das verbleibende Netz ist weiterhin
nachweislich unbeschränkt. Der getestete stärkere ILP-Heuristik-Solver zeigte
bereits bei einem bekannten Fall keinen praktischen Vorteil und wurde als
separater Test beendet. Die Basismodelle wurden dabei nicht geändert.

Bewertet werden die gespeicherten Baselines `results/models/inductive_miner.pnml`
und `heuristics_miner.pnml`, deren Prüfsummen gegen das Discovery-Manifest geprüft
werden. Die Modelle werden dabei weder verändert noch neu entdeckt.

Die Eingabe ist dieselbe Completion-Projektion wie bei der Discovery:
**31.509 Fälle, 475.306 Events, 24 Aktivitätsnamen**. Alle Fälle und die ursprüngliche
Eventreihenfolge bleiben erhalten. Es gibt keine Stichprobe und keinen Train/Test-Split.
Diese Werte beschreiben die Discovery-Eingabe. Die vollständige Rohdatenanalyse
aus Abschnitt 3.2 ist getrennt in `docs/STATISTICS.md` dokumentiert.

Ein lokaler JSON-Cache unter `tmp/evaluation/` enthält für jeden Fall die ID und
die vollständige Aktivitätsfolge. Andere Attribute werden für die hier verwendeten
Kontrollflussmetriken nicht benötigt. Varianten werden intern effizient wiederverwendet;
die Häufigkeit jeder Variante und damit das Gewicht jedes Falls bleiben erhalten.

## Ausführen und Ergebnisse ansehen

Im Projektordner:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_models.py
.\.venv\Scripts\python.exe scripts/render_evaluation.py
```

Der erste Befehl bereitet den Cache vor und startet alle Metriken. Zum gezielten
Wiederholen stehen `--prepare`, `--run`, `--model` und `--job` bereit, beispielsweise:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_models.py --model inductive_miner --job token
.\.venv\Scripts\python.exe scripts/evaluate_models.py --summarize
```

`--run` verwendet den vorbereiteten Cache; `--summarize` sammelt die Ergebnisse
aller Jobs. Nach Einzelstarts zuerst zusammenfassen, dann die Grafiken neu erzeugen.
Erfolgreiche Einzelresultate werden nur bei identischen Code-, Modell- und
Eingabe-Prüfsummen sowie derselben PM4Py-Version wiederverwendet. `--force`
erzwingt eine neue Berechnung. Unvollständige Ergebnisse werden nicht wiederverwendet.

| Datei | Inhalt |
|---|---|
| `results/tables/quality_metrics.json` | Vollständige Ergebnisse, Status, Eingabe, Parameter, Versionen und Prüfsummen |
| `results/tables/quality_metrics.csv` | Vergleich als lange Tabelle; leere Werte haben einen expliziten Status |
| `results/tables/quality_metrics.md` | Direkt lesbare Vergleichstabelle, auch für die Markdown-Vorschau in VS Code |
| `results/tables/evaluation/*.json` | Einzelne Berechnungen für jedes Modell und jede Metrikgruppe |
| `results/figures/quality_comparison.pdf` | Qualitätswerte und Anteil passender Fälle |
| `results/figures/simplicity_comparison.pdf` | Eigene Komplexitätsmaße |
| `results/tables/quality_metrics.tex` | Faktische LaTeX-Tabelle zur bewussten Übernahme in den Bericht |
| `results/tables/quality_artifacts.json` | Prüfsummen der Tabellen und Abbildungen |
| `results/tables/dead_transition_audit.json` | Exakt prüfbare Invarianten als Nachweise unerreichbarer Transitionen |

Die Grafiken liegen zusätzlich als PNG und SVG vor. Die Skripte schreiben
ausschließlich nach `results/` und `tmp/`. Ausgewählte Berichtskopien liegen separat
unter `report/`; eine erneute Analyse überschreibt diese Kopien nicht.

## Welche PM4Py-Metriken werden berechnet?

| Dimension | Berechnung | Richtung / Bedeutung |
|---|---|---|
| Fitness | Token Replay: Log-Fitness und mittlere Trace-Fitness | Größer, bis 1; fehlende und verbleibende Tokens verursachen Abzüge |
| Fitness | Optimale Alignments: Log-Fitness und mittlere Trace-Fitness | Größer, bis 1; Abweichungen zwischen Log und Modell verursachen Kosten |
| Case-Abdeckung | Anteil passender Fälle, getrennt für Token Replay und Alignments | Prozent; nicht mit durchschnittlicher Fitness verwechseln |
| Precision | Token-basiertes ETConformance | Größer, bis 1; betrachtet zusätzliche vom Modell erlaubte nächste Aktivitäten |
| Precision | Alignment-basiertes ETConformance | Größer, bis 1; Präfix-Alignments statt heuristischem Token Replay |
| Generalization | Token-basierte PM4Py-Generalization | Größer, bis 1; Häufigkeit der beim Replay aktivierten Modelltransitionen |
| Simplicity | Arc Degree mit `k=2` | Größer, bis 1; bestraft mittlere Knotengrade über 2 |
| Komplexität | PM4Py Extended Cardoso und Extended Cyclomatic | Kleiner; keine normierten Werte zwischen 0 und 1 |

Token Replay ist ein heuristisches Verfahren. Es kann bei einem unpassenden Modell
Tokens hinzufügen und liefert dadurch trotzdem eine Fitnesszahl. Sowohl die Token-
als auch die Alignment-ET-Precision schließen nicht passende Präfixe aus der
eigentlichen Precision-Aggregation aus. Ein hoher Precisionwert bei niedriger
Fitness ist deshalb allein kein Qualitätsbeweis. Beim HM meldet die vollständige
Alignment-Precision **374.337 nicht passende gewichtete Präfixe**; insgesamt gibt
es `475.306 - 31.509 = 443.797` gewichtete nichtleere Präfixe. Der Wert von
0,9975 beschreibt damit nur einen kleinen Teil der beobachteten Präfixe sowie
die zusätzlich berücksichtigten leeren Präfixe.

PM4Pys Standard-Alignments verwenden Kosten von 10.000 für sichtbare Log-/Modell-
Abweichungen, 1 für stille Modellschritte und 0 für synchrone Schritte. Die
Trace-Fitness behandelt stille Schritte anders als die aggregierte Log-Fitness
der installierten Evaluator-Variante. Deshalb können beim IM gleichzeitig
100 % passende Fälle, mittlere Trace-Fitness 1,0 und Log-Fitness 0,99977 entstehen.
Das ist keine zusätzliche beobachtbare Prozessabweichung. Für die spätere
80-%-Anforderung ist der Anteil vollständig passender Fälle maßgeblich.

Die Generalization ist die konkrete PM4Py-Heuristik
`1 - mean(1/sqrt(transition_replay_count))`; nicht besuchte Transitionen erhalten
einen Strafterm von 1. Sie zählt auch stille Transitionen. Sie ist kein Nachweis,
dass das Modell unbekannte künftige Fälle gut vorhersagt. Für beide Modelle stammen
Discovery und Bewertung aus demselben Log.

Verwendet werden die installierten PM4Py-Varianten `token_replay`,
`alignment_based`, `etconformance_token`, `align_etconformance`, `token_based`,
`arc_degree`, `extended_cardoso` und, nur bei vollständig endlichem Zustandsraum,
`extended_cyclomatic`. Die Token-Replay-Ergebnisse werden für Fitness und
Generalization gemeinsam verwendet; das ist dieselbe Berechnung ohne doppelten Replay.

Die direkte PM4Py-Alignment-Precision hielt bei diesem Log mehrere GB an
synchronen Produktnetzen gleichzeitig im Speicher. `src/quality.py` verwendet
deshalb dieselben PM4Py-Präfix-Alignments in Blöcken von 128 Präfixen. Der
globale Präfixbaum, die global beobachteten Folgeaktivitäten, die Häufigkeiten
und die Empty-Prefix-Korrektur bleiben unverändert. Die einzelnen
Batch-Precisionwerte werden **nicht** gemittelt. Aktivierte Aktivitäten werden
nach Markierung zwischengespeichert; fertige Produktnetze können freigegeben
werden. Zwei Tests vergleichen diese Berechnung mit dem unveränderten
`align_etconformance.apply`, einschließlich unterschiedlich häufiger Varianten
und nichtpassender Präfixe. Zusammen mit den übrigen Tests, der Prüfung der
Ergebniswiederverwendung, dem Vergleich serieller/paralleler Alignments auf
gemischten Varianten und drei Tests der Unerreichbarkeitsnachweise sind es 20 Tests.

## Selbst implementierte Simplicity-Maße

Die Implementierungen stehen in `src/simplicity.py` und delegieren keine Metrik
an PM4Py. Die Literatur unterscheidet strukturelle und verhaltensbezogene
Komplexität; ein einzelner Wert beschreibt nicht die gesamte Verständlichkeit.

1. **Modellgröße:** Anzahl aller Knoten `|P| + |T|` und Kanten `|F|`. Auch stille
   Transitionen zählen. Größenmaße werden von de San Pedro, Carmona und Cortadella
   (2015), Abschnitt 7.1, zur Bewertung von Simplicity verwendet.
2. **Extended Cardoso (ECaM):** Für jeden Platz `p` die Zahl verschiedener
   Ausgangsplatzmengen seiner ausgehenden Transitionen bestimmen; anschließend
   über alle Plätze summieren: `sum_p |{postset(t) : t in postset(p)}|`.
   Zwei Transitionen mit demselben Postset zählen an diesem Platz nur einmal.
   Definition 13 von Lassen und van der Aalst (2009).
3. **Extended Cyclomatic (ECyM):** Vollständigen erreichbaren Markierungsgraphen
   bilden und `|E| - |V| + Anzahl stark zusammenhängender Komponenten` berechnen.
   Kanten sind verschiedene Markierungspaare, keine mehrfach gezählten
   Transitionsnamen. Definition 15 derselben Quelle. NetworkX übernimmt nur die
   Standard-Graphoperationen; Markierungsraumsuche und Formel sind eigener Code.

Für alle drei gilt: kleinere Werte bedeuten geringere Komplexität nach diesem Maß.
Modellgröße und ECaM können für beide Baselines numerisch bestimmt werden.
ECyM setzt einen endlichen erreichbaren Zustandsraum voraus. Bei nachgewiesener
Unbeschränktheit ist der Wert **nicht endlich definiert** und wird nicht durch
einen Wert eines abgebrochenen Teilgraphen ersetzt.

## Prüfungen und bekannte Einschränkungen

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Die Tests enthalten handberechnete Sequenzen, XOR-Verzweigungen, zwei Transitionen
mit identischem Postset, parallele Zweige, eine Schleife, einen Deadlock, ein
unbeschränktes Netz und eine absichtlich begrenzte Zustandsraumsuche. Die vorhandenen
Datenaufbereitungstests bleiben zusätzlich aktiv. Die eigene ECaM-Berechnung wird
auch für beide echten Modelle mit PM4Py verglichen.

Ein zusätzlicher Integrationstest führt echte PM4Py-Alignments auf einem kleinen
Netz aus und prüft den JSON-Export einschließlich mehrfach vorkommender Varianten.
Ein weiterer Test erzwingt ein fehlendes Alignment und stellt sicher, dass kein
irreführender Durchschnitt über die übrigen Fälle entsteht.

Für ECyM ergibt die unabhängige Suche beim IM **484 Markierungen, 1.996 gerichtete
Markierungspaare und 40 stark zusammenhängende Komponenten**, also **1.552**.
Der separat von PM4Py konstruierte tatsächliche Markierungsgraph bestätigt das.
Alle erreichbaren Markierungen können zum exakten Ende gelangen, die Endmarkierung
ist sauber, und keine Transition ist tot: Das IM-Netz ist sound.

**Versionsspezifische Abweichung:** PM4Py 2.7.23.11 liefert für seine eigene
`extended_cyclomatic.apply`-Metrik **2.397**. Der installierte Quellcode setzt beim
Übertragen der Kanten in den NetworkX-Graphen `n2.name` als Ziel ein; `n2` ist
hier eine Transition des Zustandsgraphen. Das richtige Markierungsziel ist
`n2.to_state`. Damit verwendet diese Variante nicht den in Definition 15
geforderten Graphen. Der Unterschied wird dokumentiert und getestet; die
installierte Bibliothek wird nicht verändert. Beide Werte werden getrennt ausgewiesen.

Beim HM beweist die eigene Suche durch ein tatsächlich erreichbares Markierungspaar
mit strikter Tokenzunahme auf einem wiederholbaren Pfad **Unbeschränktheit**.
Das maschinenlesbare Zeugnis enthält den Weg zur Ausgangsmarkierung, die
Pumpsequenz und beide Markierungen. Dies ist mehr als eine Zeitüberschreitung
und schließt die Soundness eines WF-Netzes aus. Das vorhandene Modell wird für
den Vergleich beibehalten; Verbesserungen gehören zu 3.3.3.

Eine zusätzliche, vom Log unabhängige Prüfung weist **mindestens zwölf tote
Transitionen** im HM nach, darunter die sichtbaren Aktivitäten `O_Refused` und
`O_Sent (mail and online)`. Beim IM findet diese Prüfung keinen solchen
Nachweis; dessen vollständiger Zustandsraum bestätigt außerdem, dass keine
Transition tot ist. Die Prüfung verändert die Modelle nicht.

```powershell
.\.venv\Scripts\python.exe scripts/audit_dead_transitions.py
```

`src/validation.py` sucht nichtnegative Platzgewichte `w` mit `w*C <= 0`, wobei
`C` die Inzidenzmatrix ist. Die gewichtete Tokenzahl kann dann durch keinen
Schritt steigen. Benötigt eine Transition mehr gewichtete Tokens als die
Anfangsmarkierung enthält, kann sie niemals aktiviert werden. Der LP-Solver
liefert nur Kandidaten; sämtliche Ungleichungen werden anschließend mit
exakten rationalen Zahlen gegen **alle Originaltransitionen** geprüft.
Die Zertifikate sind hinreichende Nachweise, keine vollständige Aufzählung
aller möglicherweise toten Transitionen. Tests unterscheiden eine unmögliche
AND-Zusammenführung exklusiver Zweige von einer erlaubten parallelen
Zusammenführung und verwerfen fehlerhafte Gewichte.

**Beweisbare Fallabdeckung:** 31.098 der 31.509 Fälle enthalten eine Aktivität,
deren sämtliche Modelltransitionen unerreichbar sind. Diese Fälle können nicht
vollständig replaybar sein. Somit sind im HM höchstens **411 Fälle bzw. 1,3044 %**
vollständig replaybar. Das ist eine Obergrenze, kein gemessener Alignment-Anteil.
Die Zählung erfolgt auf allen Fällen derselben Projektion und ist mit deren
Cache-Prüfsumme im Struktur-Audit verbunden. Für das IM bestätigen die vollständigen
Alignments tatsächlich 100 % passende Fälle.

`scripts/verify_evaluation.py` prüft standardmäßig auch die Vollständigkeit aller
Alignment-Fitnesswerte. Mit `--allow-incomplete-alignment` kann eine dokumentierte
fehlende Zusatzmetrik bestehen bleiben; der Audit weist diese Lücke ausdrücklich
aus und prüft weiterhin alle tatsächlich berichteten Zahlen und Artefakt-Hashes.
Ein Fitnessmittelwert einer Teilmenge wird auch in diesem Modus nicht akzeptiert.

Ressourcengrenzen der übrigen Jobs: eigene Zustandsraumsuche höchstens
30.000 Zustände bzw. 90 s; Strukturjob höchstens 180 s; Precision-/Token-Jobs
höchstens 1.500 s. Für Fitness-Alignments gibt es standardmäßig **keine weitere
Zeitgrenze**, weder pro Variante noch für den Gesamtjob. Nur ein ausdrücklich
übergebenes `--alignment-trace-timeout` begrenzt einzelne Varianten.

Die früheren begrenzten HM-Läufe sind keine vollständigen Fitnessresultate:
Der serielle Lauf lieferte 21.501 vollständige Fallwerte; der anschließende
Acht-Prozess-Lauf wurde nach rund 66 Minuten ohne Gesamtergebnis beendet.
Die Kostenfunktion bleibt unverändert: optimale PM4Py-State-Equation-A*-Alignments,
sichtbare Log-/Modellschritte 10.000, unsichtbare Schritte 1, synchrone Schritte 0.

`src/alignment.py` bündelt identische Aktivitätsfolgen zu Varianten und verteilt
sie auf bis zu acht Prozesse. **Jede abgeschlossene Variante wird sofort atomar
als eigene JSON-Datei gespeichert**, unabhängig von noch laufenden Varianten.
Der vollständige Log wird anschließend in ursprünglicher Fallreihenfolge
rekonstruiert; mehrfach vorkommende Varianten behalten ihre Fallhäufigkeit.
PM4Pys Fitnessauswertung wird erst bei vollständigen Ergebnissen aufgerufen.
Fehlende Alignments führen zu `incomplete` und keinem Teilmengenmittelwert.

PM4Py-Threading ist deaktiviert. Der Standard begrenzt die HM-Worker auf die
Hälfte der logischen CPUs und höchstens acht. BLAS-/OpenMP-Threads werden nur
für die Auswertungsprozesse auf zwei begrenzt. Die Fortschrittsanzeige entsteht
aus abgeschlossenen Futures; PM4Pys aktive Warteschleife bleibt ausgeschaltet.
Es gibt keine Zufallsstichprobe und keinen relevanten Random Seed.

Ohne Zeitgrenze starten oder mit gespeicherten Varianten fortsetzen:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_models.py --model heuristics_miner --job alignment --alignment-workers 8
```

Die Checkpoints liegen unter `tmp/evaluation/heuristics_miner_variants/`.
Ein weiterer Aufruf verwendet nur vollständige Ergebnisse mit identischen
Log-/Modell-Prüfsummen, Aktivitätsfolgen, PM4Py-/CVXOPT-Versionen, Methode und
Kostenprofil. Workerzahl und Zeitgrenze beeinflussen den Wert eines bereits
vollständigen optimalen Alignments nicht. `--force` ignoriert diese Checkpoints.
Nach Abschluss: `--summarize`, Grafiken rendern und den Audit ohne
`--allow-incomplete-alignment` ausführen. Die ausgewählten Reportkopien werden
weiterhin ausdrücklich und getrennt aktualisiert.

Die getrennte Nachbereitung ist mit `scripts/finalize_evaluation.py` möglich.
Sie akzeptiert ausschließlich vollständige Alignment-Ergebnisse, führt den
strengen Audit aus, kopiert nur die drei bereits ausgewählten Qualitätsassets
nach `report/` und baut die PDF. `--wait-pid` wartet zuvor ohne Frist auf den
angegebenen Windows-Prozess. Für den unbegrenzten HM-Lauf wurde diese
Nachbereitung bereits vorgemerkt. Protokoll: `tmp/evaluation/finalization.log`;
Ergebnisstatus: `tmp/evaluation/finalization_status.json`. Eine abschließende
visuelle Prüfung der neu gebauten PDF bleibt darin getrennt ausgewiesen.

Am 2026-10-17 wurde der unbegrenzte Acht-Prozess-Lauf wegen tatsächlich
96 Prozent belegtem physischem RAM mit vier Prozessen fortgesetzt. 603 fertige
Varianten (22.426 Fälle) wurden aus geprüften Checkpoints übernommen; laufende,
noch nicht abgeschlossene Varianten werden erneut berechnet. Es wurde keine
weitere Zeitgrenze gesetzt. Die automatische Nachbereitung wurde an den neuen
Prozess gebunden. Das lokale Neustartprotokoll liegt unter
`tmp/evaluation/hm_memory_restart.json`.

## Quellen

- Carmona, van Dongen, Solti, Weidlich (2018): *Conformance Checking — Relating
  Processes and Models*. [Springer, DOI 10.1007/978-3-319-99414-7](https://link.springer.com/book/10.1007/978-3-319-99414-7).
  Überblick zur Konformitätsbewertung; Referenz [1] der Aufgabenstellung.
- Lassen, van der Aalst (2009): *Complexity Metrics for Workflow Nets*,
  Information and Software Technology 51(3), 610–626.
  [Autorenfassung, Definitionen 13 und 15](https://www.vdaalst.com/publications/p497.pdf),
  DOI 10.1016/j.infsof.2008.08.005.
- de San Pedro, Carmona, Cortadella (2015): *Log-Based Simplification of Process
  Models*, BPM 2015, 457–474, DOI 10.1007/978-3-319-23063-4_30.
  [Autorenfassung, Abschnitt 7.1](https://upcommons.upc.edu/server/api/core/bitstreams/6282edc9-be97-48eb-860e-b067f07ad181/content).
- Installierter PM4Py-Quellcode, Version 2.7.23.11: `pm4py/algo/evaluation/`
  und `pm4py/algo/conformance/`; für die exakte tatsächlich ausgeführte Definition.

Die Skripte und faktischen Tabellen sind mit KI-Unterstützung erstellt.
Die eigene wissenschaftliche Interpretation und die Formulierung des Berichtstexts
bleiben Aufgabe des Autors; siehe `docs/AI_USAGE.md`.
