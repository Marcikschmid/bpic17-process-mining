# Assignment I: Arbeitscheckliste

## Repository und Setup
- [x] Öffentliches GitHub-Repository erstellen und lokalen Ordner verbinden.
- [x] Ersten Commit einschließlich aller ursprünglichen Kursdateien hochladen.
- [x] LaTeX-Projekt kompilieren und die PDF-Vorschau prüfen.
- [x] BPIC-17 beschaffen, Prüfsummen verifizieren und die Herkunft dokumentieren.
- [x] Python-Umgebung und verwendete Paketversionen dokumentieren und prüfen.
- [x] Graphviz-Rendering und lokalen Jupyter-Kernel prüfen; Kernel-Codeausführung erfolgreich.
- [x] Vollständigen Event Log laden und Vorschau eines Falls speichern.

## Einführung und technische Grundlagen
- [ ] Anwendungsbereich, Entstehung und Prozess des Logs anhand externer Quellen beschreiben.
- [x] Existierende BPIC-17-Berichte recherchieren und als Quellenvergleich referenzieren (drei Originalberichte).
- [ ] Literaturbefunde in der selbst geschriebenen Einführung einordnen.
- [ ] Bibliotheken, Visualisierungs- und Modellierungswerkzeuge mit Fußnoten angeben.

## Einfache Event-Log-Analyse
- [x] Anzahl Cases, Events und Varianten.
- [x] Anzahl unterschiedlicher Case- und Event-Attributnamen.
- [x] Mittelwert und Standardabweichung der Case-Länge.
- [x] Mittelwert und Standardabweichung der Case-Dauer in Tagen, Minuten und Sekunden.
- [x] Anzahl kategorialer Event-Attribute; Klassifikationsregel dokumentieren.
- [x] Mindestens zwei weitere Statistiken und geeignete Visualisierungen.

## Discovery und Validierung
- [x] Mindestens zwei Discovery-Algorithmen anwenden; Modelle in den Anhang aufnehmen (IM und Heuristics Miner, gemeinsame Completion-Projektion aller Fälle).
- [x] Fitness (Token Replay), Precision (Token/Align-ET), Generalization und Simplicity für beide Modelle auf allen Fällen berechnen; zusätzliche HM-Alignment-Fitness mit dokumentierter Berechnungslücke.
- [x] Mindestens zwei Simplicity-Metriken nach Literatur selbst implementieren (Modellgröße, Extended Cardoso, Extended Cyclomatic; Tests und Abgleich mit dem tatsächlichen Markierungsgraphen).
- [x] Alle entdeckten Modelle mit den Metriken bewerten; Eingabe, Parameter, Grenzen und exakte Struktur-Nachweise dokumentieren.
- [ ] Zusätzliche optimale HM-Alignment-Fitness vollständig berechnen (kein Mittelwert über Teilergebnisse; bisherige Laufgrenzen dokumentiert).
- [x] Finales Modell iterativ entwickeln und Designentscheidungen protokollieren (40 Kandidaten; docs/REFINEMENT.md).
- [x] Ungefähr 80 % replaybare Cases exakt prüfen: 25.350/31.509 (80,4532 %); Fitness separat berichten.
- [x] Zielkonflikte, Grenzen und Simulationseignung technisch dokumentieren; eigene Berichtsauswertung noch ausformulieren.
- [x] Finales BPMN-2.0-Modell und Qualitätswerte als ausgewählte Reportartefakte einbinden; lokale bpmn-js-Ansicht bereitstellen.
- [x] Decision Mining nach de Leoni und van der Aalst (2013) durchführen; CART-Abweichung, Datenverfügbarkeit, Fall-Split und Grenzen dokumentieren (docs/DECISION_MINING.md).
- [x] Entscheidungsblöcke für alle XOR-Splits des finalen Modells visualisieren; sämtliche XOR-Merges als Zusammenführungen ohne Auswahl kennzeichnen.
- [x] Lesbare Bedingungen direkt in den BPMN-Textblöcken an allen 16 XOR-Splits anzeigen; Pfeile B1/B2 zuordnen; äquivalente Vereinfachung aller 117 Blattpfade zu 44 Regelpfaden prüfen.
- [x] Harte Guards separat auf allen Fällen prüfen: 3.277/31.509 (10,40 %), im Test 963/9.453 (10,19 %); 80,45 % Strukturabdeckung nicht auf das Guard-Modell übertragen.
- [ ] Die Eignung des guardangereicherten Modells als finale Simulationsbasis klären: schwache Regeln fachlich verbessern oder den Abdeckungsverlust und die Grenzen begründet diskutieren.

- [x] Dritter Discovery-Versuch mit nativem Genetic Miner: gleicher vollständiger Completion-Log, Seeds, Budget, vier Qualitätsdimensionen und nachgeprüfter Unbeschränktheitsnachweis; keine unbelegte Gleichsetzung von Token-Replay und exakter Coverage.
- [x] Tatsächliche Miner-Parameter einschließlich IM/IMf mit Bedeutung, Begründung und Grenzen als Markdown, PDF, JSON und faktische LaTeX-Tabellen bereitstellen.
- [x] 26 Designentscheidungen mit Alternativen, Evidenz und offenen Grenzen im technischen Begleitprotokoll begründen; eigene Berichtsdiskussion bleibt offen.

## Tutor-Feedback (Branch `assignment-feedback`)
- [x] Python/PM4Py, README mit Reproduktion, klickbarer Repo-Link im LaTeX.
- [x] Alpha Miner → WF-Netz geprüft: strukturell WF-Netz, aber unbeschränkt, ≥ 10 tote Transitionen, zertifiziert 0 Fälle replaybar (docs/ALPHA_MINER.md).
- [x] Heuristics Miner: natives Heuristics-Netz als Abbildung, Dependency-Sweep 0.5–0.99, alle unbeschränkt (docs/HEURISTICS_SWEEP.md).
- [x] Genetic Miner als dritter Versuch inkl. Budget-Notizen (docs/GENETIC_BUDGET.md).
- [x] Parameterübersicht aller Miner mit PM4Py-Default, gewähltem Wert und Rolle (docs/MINER_PARAMETERS.md, LaTeX-Anhang Englisch).
- [x] Soundness und behavioural Soundness (klassisch, easy, relaxed, safe, Woflan) für alle 9 Modelle (results/comparison/).
- [x] Alle vier Qualitätskriterien für alle Modelle; Zielmetrik Precision unter Fitness-Bedingung begründet (D28).
- [x] Conformance Checking nach dem Mining: Escaping Edges und Log Moves des IMf-Modells → Ansatzpunkte der manuellen Änderungen.
- [x] Manuelle Änderungen: 7 Blockänderungen, 128 Kombinationen, vorab fixierte Regel; Auswahl G3+R3+R4 (Align-ET 0,598 → 0,697, Abdeckung 79,39 %) (docs/MANUAL_EDITS.md).
- [x] Finales BPMN mit Blockstruktur-Tabelle (17 XOR-, 2 AND-Paare), sprachäquivalent zum Petri-Netz.
- [x] Held-out-Prüfung: Discovery auf Trainingsfällen ergibt identischen Baum; Test 79,26 % vs. Training 79,45 %.
- [x] Decision Mining zweistufig: zuerst Wahrscheinlichkeitsgraph, dann Bedingungen; Neuberechnung auf dem finalen Modell (17 Splits, Guards Test 10,07 %).
- [x] Event vs. Case vs. Trace vs. Variante als Tabelle (README, report/tables/concepts.tex).
- [ ] Eigene Fließtexte zu allen neuen Tabellen schreiben (Stichpunkte als `%`-Kommentare in 04_process_model.tex).
- [ ] Entscheiden: Hybrid aus Regeln (nur wo besser als Mehrheit) und Wahrscheinlichkeiten für die Simulation umsetzen oder nur diskutieren.
- [ ] Änderungen committen und Branch pushen.

## Advanced: eine Option auswählen
- [ ] SAP Signavio: Abschnitt 3.3 wiederholen, Werkzeuge vergleichen und Simulation untersuchen.
- [ ] ODER eine begründete Data-Science-Analyse: Hypothese, Methode, Ergebnis, Visualisierung und Interpretation für Prediction/Simulation/Optimierung.

## Bericht und Reproduzierbarkeit
- [ ] Englischer Bericht mit höchstens fünf Seiten ohne Literatur und Anhang.
- [ ] Abstract in vier bis fünf selbst geschriebenen Sätzen.
- [x] Öffentlichen Repository-Link anklickbar im technischen LaTeX-Abschnitt eintragen.
- [ ] Die faktischen Parametertabellen und Seeds sind im Anhang; zentrale Designentscheidungen im eigenen Bericht erläutern.
- [ ] Literatur, Tools, Packages und Datensatz korrekt referenzieren.
- [ ] KI-Nutzung anhand des tatsächlichen Arbeitsprotokolls deklarieren.
- [x] Technischen Berichtsstand kompilieren und Abbildungen/Referenzen prüfen (47 Seiten einschließlich Anhang; eigene wissenschaftliche Texte noch offen).
- [ ] Abschließende Reproduzierbarkeit prüfen und die aktuellen lokalen Änderungen committen und ins öffentliche Repository hochladen.
