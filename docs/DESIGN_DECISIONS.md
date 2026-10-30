# Designentscheidungen: Begründung, Evidenz und Grenzen

Dieses Protokoll dient als Grundlage für die eigene wissenschaftliche Diskussion.
Es trennt **Aufgabenanforderung**, **methodische Wahl**, **beobachtetes Ergebnis** und
**noch offene Validierung**. Die bestehende Implementierung wird rückblickend
dokumentiert; daraus folgt nicht, dass jede Begründung bereits vor dem ersten Lauf
formuliert war. Das neue Genetic-Budget wurde vor seinem Lauf gespeichert.

Die technischen Parameter stehen vollständig mit Bedeutung und Begründung in
[MINER_PARAMETERS.md](MINER_PARAMETERS.md). Der wissenschaftliche Bericht bleibt
vom Autor selbst zu formulieren; dieses Dokument ist keine fertige Berichtsvorlage.

## Daten und Vergleichbarkeit

### D01: Originaldatei unverändert aufbewahren

- **Wahl:** Komprimierte Original-XES und Metadaten herunterladen; Größe, Quell-MD5
  und SHA-256 prüfen. Rohdaten nicht durch eine „bereinigte“ Datei ersetzen.
- **Grund:** Herkunft und Integrität von späteren Modellierungsentscheidungen
  trennen; Wiederholung mit identischem Input ermöglichen.
- **Alternative/Preis:** Eine vorgefilterte Datei wäre kleiner, würde aber die
  Vergleichsbasis und den Umfang der analysierten Population verändern.
- **Nachweis:** `data/manifest.json`, `scripts/download_data.py`; Prüfung gegen
  Originaldatei in Statistik- und Discovery-Audits.

### D02: Completion-Projektion für Kontrollfluss, Rohlog für Statistik

- **Wahl:** Für Discovery und deren Metriken nur `lifecycle:transition=complete`;
  die Statistik aus 3.2 umfasst weiterhin alle Lifecycle-Zustände.
- **Grund:** Eine abgeschlossene Work-Item-Ausführung soll nicht als getrennte
  Aktivität für schedule/start/suspend/resume mehrfach repräsentiert werden.
- **Preis:** 726.961 Nicht-Completion-Events und zwei Aktivitätslabels entfallen.
  Abgebrochene Arbeit und Lifecycle-Verhalten sind damit nicht modelliert.
- **Nachweis:** Alle 31.509 Fälle bleiben erhalten; 475.306 Completion-Events,
  24 Labels. Vollständige Ausschlussliste im Discovery-Manifest.
- **Status:** Begründete Modellierungsperspektive, keine universell richtige
  Bereinigung. Andere Perspektiven erfordern einen neu abgeglichenen Vergleich.

### D03: Originale Labels und gespeicherte Fallreihenfolge erhalten

- **Wahl:** Keine Umbenennung oder Zusammenfassung von Aktivitäten, keine
  automatische Timestamp-Sortierung der EventLog-Baselines, kein Entfernen
  nachgestellter Leerzeichen. Schema-Fehler führen zum Abbruch.
- **Grund:** Veränderungen der Ereignisklassen und ihrer Reihenfolge können
  selbst Schleifen, Abhängigkeiten und Varianten verändern.
- **Alternative/Preis:** Ein fachlich abstrahiertes Modell wäre leichter lesbar,
  müsste aber mit eigener Mappingtabelle und eigener Evaluationsprojektion gelten.
- **Nachweis:** Preprocessing-Tests, XML-Audit, `src/discovery.py`.

### D04: Alle Fälle bewerten und Varianten mit Fallhäufigkeit gewichten

- **Wahl:** Ergebnisse auf allen 31.509 Fällen der gemeinsamen Projektion messen;
  gleiche Varianten intern wiederverwenden, aber nicht gleich gewichten.
- **Grund:** Eine seltene Variante darf nicht dasselbe Populationsgewicht wie eine
  Variante mit Tausenden Fällen erhalten. Eine Auswahl nur passender Fälle würde
  die geforderte Fallabdeckung nicht messen.
- **Preis:** Häufige Pfade dominieren natürliche Populationsmetriken; deshalb
  zusätzlich seltene und nach Ausgang getrennte Fälle prüfen.
- **Nachweis:** Fall-IDs, Cache-Hash, gewichtete Metriktests und Replay-CSV.

### D05: Petri-Netze für Baselines, BPMN für das finale Strukturmodell

- **Wahl:** Gemeinsame akzeptierende Petri-Netz-Semantik für den Miner-Vergleich;
  finale Process-Tree-Struktur zusätzlich nach BPMN exportieren.
- **Grund:** Explizite Anfangs-/Endmarkierungen ermöglichen Replay und
  Zustandsraumanalyse. BPMN erfüllt die Darstellungsanforderung der Aufgabe.
- **Preis:** Ein Syntaxexport beweist weder Soundness noch fachliche Richtigkeit.
- **Nachweis:** PNML-Roundtrips; gesamte Sprachäquivalenz des verfeinerten BPMN
  zu seinem Petri-Netz, nicht nur visuelle Ähnlichkeit.

## Miner und Suchraum

### D06: Inductive Miner mit Noise 0 als erste Vergleichsbasis

- **Wahl:** `noise_threshold=0.0`, `multi_processing=False`,
  `disable_fallthroughs=False`; IM statt IMf bei Noise 0.
- **Grund:** Zunächst kein zusätzlich angenommener Rauschanteil; standardmäßige
  strukturierte Zerlegung und verfügbare Fallbacks als transparente Referenz.
- **Beobachtung:** 100 % exakte Fallabdeckung, aber nur etwa 0,2926 Precision.
- **Preis:** Vollständige Reproduktion beobachteter Sequenzen kann mit viel
  zusätzlich erlaubtem Verhalten einhergehen. Noise 0 ist kein Qualitätsoptimum.
- **Nachweis:** Gespeichertes IM-Modell, Qualitäts- und Zustandsraum-Audit.

### D07: Heuristics Miner CLASSIC mit expliziten Standard-Schwellen

- **Wahl:** Dependency 0.5, AND 0.65, Zweierloop 0.5, Mindesthäufigkeiten jeweils
  1, relatives DFG-Pre-Cleaning 0.05.
- **Grund:** Einen lokalen, häufigkeitsbasierten Ansatz mit einer strukturierten
  Methode vergleichen. Die Standards bilden eine nachvollziehbare Baseline;
  sie werden nicht als auf BPIC-17 optimierte Werte dargestellt.
- **Beobachtung:** Das aktuelle HM-Netz ist unbeschränkt und hat zertifiziert
  unerreichbare Transitionen. Seine hohe Precision kompensiert diese Defekte nicht.
- **Preis:** Lokale Schwellen und Konvertierung garantieren kein soundes
  Simulationsmodell. Die Baseline bleibt als negatives Vergleichsergebnis erhalten.
- **Nachweis:** Parameter im Code/Manifest; unabhängig replaytes Pump-Witness;
  Dead-Transition-Zertifikate und Obergrenze vollständiger Fallabdeckung.

### D08: Genetic Miner als zusätzlicher global suchender Vergleich

- **Wahl:** Den vorhandenen PM4Py Genetic Miner CLASSIC verwenden; keine fremde
  unversionierte Python-Implementierung und keine selbst behauptete ProM-Replikation.
- **Grund:** Testen, ob evolutionäre Suche über kausale Matrizen einen anderen
  Kompromiss als die beiden konstruktiven Baselines liefert.
- **Methodenbezug:** Die installierte Implementierung verweist auf Frank (2026)
  und die genetischen/kausalen-Matrix-Ansätze von van der Aalst et al. (2005).
- **Preis:** Stochastische Suche kostet viele Modellbewertungen. Der kleine
  Versuch liefert weder globale Optimalität noch statistische Überlegenheit.
- **Nachweis:** Separater Seed-Ordner mit Parametern, nativer Evolutions-CSV,
  Software-/Input-Hashes, Modell und Qualitätsmessungen. Scheitern bleibt sichtbar.

### D09: Vorab begrenztes Genetic-Budget statt Case-Sampling

- **Wahl:** Population 10, maximal 6 Generationen; alle 31.509 Fälle. Elitismus
  0.1 erhält genau ein Individuum; Eltern-Turniersample 2; Crossover 1.0,
  Mutation 0.01. Maximal 60 Modellbewertungen in bis zu 6 Populationen, native Frühstopps möglich.
- **Grund:** Das neue Verfahren zunächst mit kleinerem Suchbudget als dem
  Default 500 × 100 testen, ohne seine Trainingsdaten gegenüber IM/HM zu ändern.
  Der Elitismus wird an die kleine Population angepasst; 1 % würde auf null runden.
- **Preis:** Geringere Suchraumabdeckung und mögliche frühe Stagnation. Andere
  Seeds, größere Populationen und Konvergenzanalysen bleiben Folgeexperimente.
- **Nachweis:** Vor Laufbeginn gespeicherte Konfiguration, tatsächliche statt
  nur maximaler Generationenzahl. Ausgewertet wird die native Fitnessfunktion,
  nicht nachträglich eine andere Zielfunktion als angeblich trainiertes Ziel.

### D10: Zufalls- und Hash-Seeds explizit setzen

- **Wahl:** Python-random, NumPy und `PYTHONHASHSEED` für den Genetic-Versuch
  kontrollieren; den Hash-Seed bereits beim Start eines eigenen Prozesses setzen.
- **Grund:** Zufälliges Ziehen aus Set-basierten Pools hängt auch von deren
  Iterationsreihenfolge ab. Nur `random.seed()` wäre hier unzureichend.
- **Preis:** Reproduzierbarkeit ist auf Input, Version und Implementierung
  bedingt. UUIDs/Dateibytes müssen trotzdem nicht zwischen allen Exporten identisch sein.
- **Nachweis:** Kleine native Wiederholungstests mit isomorphen Petri-Netzen;
  Seeds, Paketversionen und Code-Hashes im echten Laufmanifest.

### D11: Native Timestamp-Sortierung des Genetic Miners prüfen

- **Wahl:** Tatsächliche Zeitstempel verwenden und sämtliche nach nativer
  Sortierung erhaltenen Fallsequenzen mit dem Baseline-Cache vergleichen.
- **Grund:** Eine neue Reihenfolge bei Timestamp-Gleichständen wäre eine
  verdeckte zusätzliche Vorverarbeitung gegenüber den anderen Minern.
- **Beobachtung:** Für den vollständigen Input stimmen alle Fallsequenzen überein.
- **Nachweis:** `native_timestamp_sort_preserves_all_case_sequences=true` im
  Genetic-Inputmanifest; bei Abweichungen bricht der Versuch ab.

## Metriken und finale Modellauswahl

### D12: Exakte vollständige Fälle von Fitness unterscheiden

- **Wahl:** Für die 80-Prozent-Anforderung akzeptierende vollständige
  Prozessdurchläufe zählen; Token-Fitness und Token-Fitting-Quote separat berichten.
- **Grund:** Token Replay darf Tokens ergänzen und liefert auch für unpassende
  Modelle Zahlen. Hohe mittlere Fitness bedeutet nicht 80 % vollständig passende Fälle.
- **Beobachtung:** Im verfeinerten Modell 80,4532 % exakt passende Fälle gegenüber
  81,6243 % heuristischer Token-Fitting-Quote.
- **Nachweis:** Vollständig enumerierter endlicher Markierungsgraph,
  Fall-Replay-CSV und PM4Py-Alignment-Gegenprüfungen.

### D13: Soundness und Zielabdeckung als Bedingungen, Precision als Haupthebel

- **Wahl:** Kandidaten mit soundem Verhalten und 78--82 % exakter Coverage
  bevorzugen; innerhalb des Bands Präfixpräzision maximieren, bei Gleichstand
  weniger Knoten wählen. Abschließend PM4Py Align-ET separat berichten.
- **Grund:** Ein Simulationsmodell soll relevante Fälle abdecken und gleichzeitig
  zusätzliche unbelegte Abläufe begrenzen. IM besitzt bereits perfekte Fitness,
  weshalb weiteres reines Fitness-Maximieren kaum hilft.
- **Preis:** Das Zielband ist unsere Operationalisierung von „ungefähr 80 %“.
  Die Präfixpräzision der Kandidatenauswahl ist nicht identisch mit dem abschließend
  berichteten kostenbewussten PM4Py Align-ET.
- **Nachweis:** 40 Kandidaten und explizite Auswahlregel; keine Gleichsetzung
  verschiedener Precision-Implementierungen.

### D14: Ausschlüsse bei Precision und Grenzen der Generalization berichten

- **Wahl:** Precision nur mit Abdeckung, gleichem Input und ausgeschlossenen
  Präfixen interpretieren. PM4Py-Generalization als Häufigkeitsheuristik benennen.
- **Grund:** HM erreicht ungefähr 0.9975 Align-ET, schließt dabei aber 84,35 %
  der gewichteten nichtleeren Präfixe aus. Seine Replay-Obergrenze ist nur 1,30 %.
- **Preis:** Keine der vier Qualitätsdimensionen ist allein ein hinreichendes
  Optimierungsziel. Ein einzelner nachträglicher gewichteter Gesamtscore würde
  normative Gewichtungen verstecken.
- **Offen:** Zeitliche/äußere Validierung für Aussagen über neue Fälle;
  aktuell Discovery und Kontrollflussbewertung auf demselben Gesamtlog.

### D15: Mehrere eigene Komplexitätsmaße verwenden

- **Wahl:** Modellgröße, Extended Cardoso und Extended Cyclomatic selbst
  implementieren, zusätzlich PM4Pys Arc-Degree-Simplicity berichten.
- **Grund:** Unterschiedliche Maße erfassen unterschiedliche Aspekte und erfüllen
  die Aufgabenforderung nach mindestens zwei eigenen Implementierungen.
- **Preis:** Das verfeinerte Modell hat 89 statt 87 Knoten und Cardoso 52 statt
  47, trotz besserem Arc-Degree-Wert und kleinerem ECyM 551 statt 1552.
  Es ist daher nicht nach jedem Maß einfacher.
- **Nachweis:** Literaturdefinitionen, synthetische Tests und unabhängiger
  PM4Py-Markierungsgraph. Der dokumentierte PM4Py-ECyM-Implementierungsfehler wird
  nicht stillschweigend als Referenzwahrheit übernommen.

### D16: Unbeschränktheit von Rechenlimits unterscheiden

- **Wahl:** Bei vollständigem Zustandsraum numerische Komplexität berichten;
  bei exakt geprüftem Pump-Witness „unbounded“; bei Limit nur „unbekannt/Limit“.
- **Grund:** Ein Abbruch nach 30.000 Zuständen oder 90 Sekunden beweist keine
  Unbeschränktheit. Ein beobachteter streng überdeckter Vorfahr mit nachgespieltem
  Pump-Zyklus liefert dagegen ein prüfbares Zertifikat.
- **Preis:** Einige Modelle erhalten keine exakte numerische Coverage/ECyM.
  Diese Lücke wird nicht mit einer erfundenen Zahl oder Teilmengenquote ersetzt.

### D17: Häufige Varianten für IMf trainieren, alle Fälle evaluieren

- **Wahl:** Zusätzlich zu Voll-Log-IMf nach Variantenhäufigkeit fokussierte
  Discovery ausprobieren; gewähltes Ziel 60 %, tatsächlich 18.918 Fälle/73 Varianten.
- **Grund:** Die Voll-Log-Suche lieferte im gewünschten Coverage-Band schwächere
  Kompromisse. Der zusätzliche Suchraum soll dominante Prozessstrukturen abbilden.
- **Preis:** Seltene Pfade können unterrepräsentiert werden; die Trainingsauswahl
  ist eine echte zusätzliche Entscheidung und kein interner `noise_threshold`.
- **Nachweis:** Rangbildung nur nach Häufigkeit, stabiler Tie-Break, explizite
  Trainingsanteile; Evaluation auf denselben 31.509 Fällen wie zuvor.

### D18: Fachliche Abstriche des finalen Strukturmodells offenlegen

- **Beobachtung:** Die Completion-Labels `O_Sent (online only)`,
  `W_Assess potential fraud` und `W_Call after offers` sind nicht im Modell.
  Denied-Fälle werden schlechter abgedeckt als Pending-/Cancelled-Fälle.
- **Grund der Akzeptanz im Strukturversuch:** Besserer gemessener Kompromiss
  innerhalb des vorgegebenen Coverage-Ziels; keine Behauptung fachlicher Irrelevanz.
- **Preis/Offen:** Für Simulation können gerade seltene Betrugs-/Ablehnungswege
  wichtig sein. Verteilungen nach Ausgang und diese Ausschlüsse im Bericht
  diskutieren; Ressourcen, Dauern und Routingwahrscheinlichkeiten sind nicht kalibriert.

## Datenabhängige Entscheidungen

### D19: Alignments statt bloßer nächster Aktivität zur Zweigzuordnung

- **Wahl:** Jede Variante optimal vollständig auf das BPMN-Flussnetz ausrichten;
  auch stille Routing-Schritte einbeziehen. Einen stabil gewählten optimalen Pfad
  je Variante auf alle zugehörigen Fälle anwenden.
- **Grund:** Das vorgegebene Paper verarbeitet auch nicht passende Traces und
  unsichtbare Entscheidungen; einfache Positionszuordnung würde diese verwechseln.
- **Preis:** Alternative gleich optimale Alignments und die Reihenfolge paralleler
  Schritte können andere Entscheidungen oder verfügbare Variablen ergeben.
- **Nachweis:** Gesamte Sprachäquivalenz des Flussnetzes, alle Move-Replays,
  24 echte PM4Py-Kostenreferenzen und entsprechende Tests.

### D20: Nur vor der Entscheidung verfügbare Eingaben verwenden

- **Wahl:** Trace-Eingaben zu Beginn; Eventwerte erst nach synchronem Schritt
  aktualisieren; Outcome-Flags `Accepted`/`Selected` sowie IDs ausschließen.
- **Grund:** Zukunftsinformation könnte ansonsten scheinbar perfekte, für
  Simulation oder Vorhersage unbrauchbare Regeln erzeugen.
- **Preis:** Die Annahme, Trace-Attribute seien von Beginn an bekannt, bleibt
  fachlich zu prüfen. Letzte Angebotswerte können bei mehreren Offers zu einem
  anderen Objekt gehören; der flache Ansatz löst diese Korrelation nicht.
- **Nachweis:** Alle 453.820 Snapshots nochmals aus den Rohdaten rekonstruiert;
  synthetische Gegenbeispiele mit noch unbekannten zukünftigen Daten.

### D21: Fallweiser 70/30-Split und erklärbare CART-Bäume

- **Wahl:** Globaler Split mit Seed 20261018; alle Wiederholungen eines Falls
  über sämtliche XORs in derselben Gruppe. Tiefe 3, mindestens 50 Trainingszeilen
  pro Blatt; One-Hot-Kodierung nur aus Training, explizite Missingness.
- **Grund:** Train/Test-Leckage durch wiederholte Entscheidungen desselben Falls
  vermeiden; überschaubare Regeln statt unbeschränkt großer Bäume erhalten.
- **Preis:** Die 3/50-Werte sind begründete Regularisierungsannahmen, keine
  nachgewiesenen optimalen Hyperparameter. Kleine Zweige können nie vorhergesagt
  werden. Die Kontrollflussstruktur wurde bereits am Gesamtlog ausgewählt.
- **Nachweis:** Separate Testkennzahlen, Mehrheitsbaseline, Macro-F1 und
  Balanced Accuracy; keine Gleichsetzung mit einer unabhängigen Bewertung der
  gesamten Discovery-Pipeline. CART ersetzt ausdrücklich C4.5 aus dem Paper.

### D22: Harte Guards als gesonderten, nicht fertig validierten Versuch behandeln

- **Wahl:** Gelerntes Routing in einer separaten BPMN-Datei mit Bedingungen
  und sichtbar zugeordneten Regelblöcken exportieren; Originalstruktur erhalten.
- **Beobachtung:** Harte Guards reduzieren vollständige Fallabdeckung auf
  10,40 % insgesamt und 10,19 % im Test.
- **Schluss:** Das ist ein wesentlicher negativer Befund, kein kleiner technischer
  Restpunkt. Die 80,45 % des Strukturmodells dürfen diesem Modell nicht zugeschrieben
  werden. Das guardangereicherte Modell erfüllt das gleiche Coverage-Ziel derzeit nicht.
- **Offen:** Fachlich passendere Datenzustände/Offer-Korrelation, bessere
  validierte Regeln oder probabilistische Routingansätze prüfen und begründen.

## Ausführung, Darstellung und Bericht

### D23: Exakte Beschleunigung und vollständige Checkpoints statt Sampling

- **Wahl:** Endliche Markierungsgraphen für exaktes Replay/Align-ET nutzen,
  nach Variante wiederverwenden; bei teuren optimalen HM-Alignments fertige
  Varianten atomar speichern und nach Wiederstart wiederverwenden.
- **Grund:** Aufwand senken, ohne andere Fallgewichte oder eine andere Metrik
  unter demselben Namen einzuführen.
- **Preis:** Endliche Optimierung gilt nicht für nachweislich unbeschränkte Netze.
  Unfertige Alignments bleiben offen; kein Durchschnitt nur fertig gerechneter Fälle.
- **Nachweis:** Äquivalenztests, echte Referenzpräfixe, Quellen-/Input-Hashes und
  ausdrücklich dokumentierte Rechenlücken. Weniger Worker bei RAM-Druck ist eine
  Ressourcenentscheidung, keine fachliche Modelloptimierung.

### D24: Sichtbare Regeln und lesbare Vektorgrafiken ohne semantische Reduktion

- **Wahl:** Alle Originalknoten/-kanten darstellen; größere Vektor-Modelltafeln
  bzw. überlappende Panels. Bedingungen direkt neben XOR-Splits zeigen; Merges
  nicht fälschlich als zusätzliche Entscheidungen klassifizieren.
- **Grund:** Kontrolle und Erklärung der tatsächlichen Modelle ermöglichen;
  keine nur „schöne“ Handzeichnung mit anderem Verhalten abgeben.
- **Preis:** Der Anhang ist lang. Zur Regelanzeige werden nur gleich vorhersagende
  Teilbäume zusammengefasst: 117 Blattpfade zu 44 äquivalenten Regelpfaden.
- **Nachweis:** Vollständiger Präfixabgleich und unveränderte formale Guards;
  jede Modellform in mindestens einem Reportpanel vollständig sichtbar.

### D25: Code, generierte Ergebnisse und Autorenbericht trennen

- **Wahl:** Analysen unter `src/`/`scripts/`, Outputs unter `results/`, bewusste
  Auswahl faktischer Reportkopien unter `report/`; Dataset und große Caches nicht
  in Git. Wissenschaftliche Berichtstexte bleiben Autorenarbeit.
- **Grund:** Wiederholung einer Analyse soll keine Berichtsentwürfe überschreiben;
  der Report soll auch ohne Rohdaten/Python kompilieren. Öffentlicher Code,
  Parameter, Seeds, Quellen, Prüfsummen und KI-Nutzung sind nachvollziehbar.
- **Preis:** Reportkopien müssen explizit aktualisiert und geprüft werden.
  Das technische Protokoll ersetzt keine eigene begründete Diskussion im Bericht.

### D26: Eindeutige Export-IDs und unabhängige Prüfung des Genetic-Ergebnisses

- **Wahl:** Identifikatoren vor dem PNML-Export auf Eindeutigkeit prüfen und
  Kollisionen in einer Kopie umbenennen; Labels, Kanten und Markierungen erhalten.
- **Anlass:** Die native Genetic-Konvertierung vergab an 15 stille Transitionen
  denselben leeren Namen. PNML verwendete ihn mehrfach als ID; der Import änderte
  die Zuordnung der Kanten. Ein Vergleich nur über Knotennamen erkannte das nicht.
- **Korrektur:** Der vor dem Import gespeicherte Graphviz-Graph enthält eindeutige
  Objekt-IDs, alle 87 ungewichteten Kanten, 24 sichtbare Labels und beide Markierungen.
  Daraus wurde die native Struktur verlustfrei wiederhergestellt und korrekt exportiert.
  Die Suchpopulation wurde dabei nicht neu optimiert oder nachträglich ausgetauscht.
- **Nachweis:** Die interne Zielfunktion wird auf allen 31.509 Fällen nach dem
  korrigierten Import exakt reproduziert: 0.30489724447042077, Differenz 0.
  Ein Regressionstest prüft nun zwei namensgleiche stille Transitionen und
  vollständiges Replay nach dem Export. Ungültige Erstwerte sind nur unter
  `results/genetic/seed_20261025/audit/INVALID_*` erhalten und vom Vergleich ausgeschlossen.
- **Ergebnis:** Token-Fitness 0.7410, Token-Precision 0.5970, Generalization 0.9828,
  Arc-Simplicity 0.7755; 76 Knoten, 87 Kanten, Extended Cardoso 43.
  Ein mit PM4Py nachgeprüfter Pump-Zyklus beweist Unbeschränktheit.
  Exakte vollständige Fallabdeckung wurde deshalb nicht enumeriert; 0 % passende
  Token-Replays sind keine Aussage über exakt 0 % akzeptierte Fallsequenzen.
- **Entscheidung:** Dieses Modell erfüllt die strukturellen Voraussetzungen nicht
  und wird nicht als finales Simulationsmodell gewählt. Ein einzelner Lauf mit
  10 Individuen und 2 tatsächlich bewerteten Generationen erlaubt keine allgemeine
  Aussage, dass Genetic Miner ungeeignet seien. Das Abbruchverhalten gehört zum Befund.

## Tutor-Feedback (Branch `assignment-feedback`, 2026-10-29/30)

### D27: Alpha Miner und HM-Sweep als zusätzliche Baselines; ein Soundness-Gate für alle Modelle

- **Wahl:** Alpha (classic) und einen HM-Sweep (`dependency_thresh` 0.5/0.7/0.9/0.99) auf derselben
  Completion-Projektion ergänzen; jedes Modell durch dasselbe Gate (`scripts/assess_model.py`):
  WF-Netz-Struktur, klassische Soundness auf vollständigem Zustandsraum oder Unbeschränktheitszeuge,
  easy/relaxed Soundness, Safeness, Woflan-Gegenprüfung, alle vier Qualitätsdimensionen.
- **Grund:** Kette „Alpha → WF-Netz, Heuristics, Inductive“ belegen statt behaupten; ein WF-Netz ist
  strukturell, Soundness ist Verhalten.
- **Ergebnis:** Alpha und alle HM-Sweep-Netze sind WF-Netze, aber unbeschränkt; Alpha: ≥ 10 tote
  Transitionen, zertifiziert 0 Fälle replaybar; HM: ≥ 12 tote, ≤ 1,30 %; Genetic: Endmarkierung
  zertifiziert unerreichbar. Nur IM/IMf sind sound (Woflan stimmt überall zu).
- **Nachweis:** `results/comparison/model_comparison.md`, `docs/ALPHA_MINER.md`, `docs/HEURISTICS_SWEEP.md`.

### D28: Precision als Optimierungsziel; Fitness als Bedingung; Generalization und Simplicity als Leitplanken

- **Wahl:** Sound + 80–82 % exakte Fallabdeckung als Bedingung (bis 29.10.: 78–82 %, siehe D33); Align-ET-Precision maximieren;
  Leitplanken vor dem Screening fest: Alignment-Generalization −0,01, Arc-Degree −0,05, Knoten +25 %.
- **Grund:** Simulationsbasis: nie beobachtetes Verhalten erzeugt unrealistische simulierte Fälle;
  IM hat bereits perfekte Fitness, aber Precision 0,293. Generalization/Simplicity sollen nicht
  unbemerkt geopfert werden.
- **Alternative/Preis:** Gewichtete Summe der vier Kriterien wäre ein Gewichtungsproblem ohne
  fachliche Begründung; reine Precision-Maximierung belohnt nicht-fittende Netze (HM 0,998).

### D29: Manuelle Änderungen am Prozessbaum, Auswahl G2 + G3 + R3 + R4

- **Wahl:** Sieben benannte Blockänderungen (R1–R4 einschränkend, G1–G3 verallgemeinernd) am
  IMf-Prozessbaum; alle 128 Kombinationen bewertet; vorab fixierte Regel (D28).
- **Grund:** Einzelne Petri-Netz-Kanten zu ändern kann Soundness und Blockstruktur zerstören; der
  Prozessbaum garantiert beides, das Petri-Netz-Delta wird trotzdem je Kombination protokolliert.
  Wo geändert wird, bestimmen die Konformitätsdiagnosen (Escaping Edges, Log Moves).
- **Ergebnis:** G2+G3+R3+R4: Align-ET 0,598 → 0,695, exakte Abdeckung 80,45 % → 80,43 %,
  Alignment-Generalization 0,9911 → 0,9880, 98 statt 89 Knoten, ECyM 551 → 166.
  (Unter dem alten Band 78–82 %: G3+R3+R4 mit 79,39 % – durch D33 ersetzt.)
- **Offen gelegt:** Leitplankenstufe zuerst auf Top 5, dann Top 10 begrenzt; alle Top-10 enthalten R1 und
  scheitern an der Generalization → Stufe läuft jetzt bis zum ersten bestandenen Kandidaten (Regel unverändert).
- **Nachweis:** `docs/MANUAL_EDITS.md`, `results/manual_edits/screen.json`.

### D30: Generalization alignmentbasiert, wenn Labels doppelt vorkommen

- **Wahl:** PM4Py-Generalization-Formel auf Ausführungszahlen exakter optimaler Alignments statt Token Replay.
- **Grund:** PM4Py Token Replay ordnet jedes Label genau einer Transition zu; bei duplizierten Labels
  (R1) entstehen ungültige Werte (Token-Precision 0,997). Zusätzlich sind HM-Tokenwerte zwischen
  Läufen nicht reproduzierbar (Fitness 0,8334–0,8363, Generalization 0,834–0,861 für dasselbe Netz).
- **Preis:** Bei gleich teuren optimalen Alignments hängt die Zählung vom Tie-Break ab (Abweichung
  ≈ 5·10⁻⁵ zwischen PNML- und Baum-Import desselben Modells).

### D31: Decision Mining zweistufig: zuerst Verzweigungswahrscheinlichkeiten, dann Regeln

- **Wahl:** Schritt 1 nur Häufigkeiten je XOR-Ausgang aus optimalen Alignments (kein Datenmodell);
  Schritt 2 CART-Regeln nach de Leoni/van der Aalst (2013) wie in D19–D22.
- **Grund:** Wahrscheinlichkeiten sind die minimale, immer vollständige Simulationsparametrisierung;
  Regeln lohnen nur, wo sie die Mehrheitsbaseline schlagen. Schleifensplits zählen je Besuch.
- **Nachweis:** `results/decision_mining/branch_probabilities.*`, `scripts/render_branch_probabilities.py`.

### D32: Held-out-Prüfung der Control-Flow-Discovery

- **Wahl:** Discovery (Top-Varianten bis 60 %, IMf 0,03) nur auf den 70 % Trainingsfällen des
  Decision-Mining-Splits wiederholen.
- **Ergebnis:** identischer Prozessbaum (72 Varianten, 13.258 Fälle); exakte Abdeckung Training
  80,49 % vs. Test 80,37 % (IMf), finales Modell 80,48 % vs. 80,32 % → Discovery hängt nicht von den Testfällen ab.
- **Grenze:** Die manuellen Änderungen wurden auf allen Fällen bewertet; keine zeitliche Validierung.
- **Nachweis:** `results/comparison/holdout_check.json`, `scripts/holdout_check.py`.

### D33: „Mindestens 80 % aller Fälle“ statt „ungefähr 80 %“

- **Anlass:** Vorlesung 29.10., Folie 36: „Your process model should represent at least 80% of all
  cases and remain simple while ensuring generalization and precision.“
- **Wahl:** Untergrenze des Auswahlbands 78 % → 80 %; Obergrenze 82 % unverändert (eigene Wahl:
  nicht deutlich mehr als nötig abbilden, Precision und Einfachheit erhalten).
- **Folgen:** IMf-Auswahl unverändert (kein anderer Kandidat in [80, 82]); manuelle Änderungen
  G3+R3+R4 (79,39 %) → G2+G3+R3+R4 (80,43 %); Decision Mining neu gerechnet.
- **Begründung „nicht 100 %“ (Tutorium):** 100 % Konformität ist nicht automatisch gut – seltene
  Traces können Datenfehler sein und würden mitmodelliert. Beleg: IM 100 % Abdeckung, aber
  Align-ET-Precision 0,293; 5.623 Varianten, die häufigsten 73 decken bereits 60 % der Fälle (18.918).
- **Perspektiven (Folie 36):** akademisch: Soundness, Reproduzierbarkeit, Generalization (Held-out);
  Beratung: Einfachheit, Verständlichkeit für Stakeholder, Blockstruktur/BPMN; Automatisierung/
  Simulation: Precision (keine unbeobachteten Pfade) bei ausreichender Fitness, ausführbare Guards.

### D34: Messverfahren je Qualitätskriterium – was verwendet, warum

- **Wahl:** Fitness: exakte Fallabdeckung als Bedingung, Alignment-Fitness als Kennzahl, Token Replay
  nur zum Vergleich. Precision: Align-ET statt ETC. Generalization: alignmentbasiert + Held-out.
  Simplicity: Arc Degree, Größe, Extended Cardoso, ECyM gemeinsam.
- **Grund (Folien 15, 20):** Token Replay ist bei stillen Transitionen/Schleifen nicht deterministisch
  (HM: Fitness 0,833–0,836, Generalization 0,834–0,861 für dasselbe Netz) und bei doppelten Labels
  nicht anwendbar (finales Modell: `invalid`); Alignments sind global optimal und erklärbar.
- **Preis:** Alignments brauchen einen endlichen Zustandsraum; HM-Alignment-Lauf unvollständig.
- **Nachweis:** `results/comparison/metric_methods.md`, Literatur: Rozinat/van der Aalst 2008,
  van der Aalst/Adriansyah/van Dongen 2012, Rozinat 2010, Polančič/Cegnar 2017.

### D35: Decision Mining in Merkmalsstufen; Feature Engineering

- **Wahl (Tutorium):** pro XOR-Split drei Bäume mit identischem Split und identischen CART-Parametern:
  (A) nur Case-Attribute, (B) Case + letzte bekannte Event-Attribute (Primärmodell, BPMN-Guards),
  (C) B + Feature Engineering aus dem synchronisierten Präfix: Anzahl Events, Angebote, `A_Incomplete`,
  Besuche desselben Gateways (Schleifenzähler), verstrichene Tage seit Fallbeginn, letzte Aktivität.
- **Feature Engineering:** neue Eingangsgrößen aus Rohdaten ableiten, die fachliches Wissen kodieren
  (Folie 48: Häufigkeiten, Zeitaggregate, jüngste Muster). Nur Information vor der Entscheidung →
  kein Leakage; Log-Moves aktualisieren nichts (Test `test_engineered_features_use_only_the_synchronized_prefix`).
- **Ergebnis:** mittlere Balanced Accuracy (Test) 0,514 → 0,562 → 0,749; Splits über Zufallsniveau
  (1/Zweige) 5 → 8 → 14 von 18.
- **Grenze:** Verlaufsmerkmale (Schleifenzähler, letzte Aktivität) beschreiben teils den Prozesszustand,
  nicht Geschäftsregeln; Simulation braucht dann zustandsabhängiges Routing. Primärmodell bleibt B,
  weil seine Regeln direkt als BPMN-Bedingungen lesbar sind.
- **Modellwahl (Folien 49, 52):** CART wegen extrahierbarer Regeln (wie Rozinat/van der Aalst 2006,
  de Leoni/van der Aalst 2013); Alternativen NN + XAI (Park et al. 2023) oder Surrogatmodell:
  genauer, aber Regeln weniger direkt. Ausgabe entspricht Guards G(t) eines Colored Petri Net.
- **Nachweis:** `results/decision_mining/feature_stages.{csv,tex}`, `decision_mining.json` (`stages`).

## Nächste Schritte nach wissenschaftlicher Priorität

1. Den negativen Guard-Coverage-Befund fachlich bewerten/verbessern.
2. Die zentralen Trade-offs und alle entscheidenden Parameter im eigenen Bericht
   begründen; Standardwerte nicht nachträglich als optimale Werte bezeichnen.
3. Genetic-Ergebnis auf identischem Input mit den Baselines vergleichen;
   bei weitergehenden Aussagen mehrere Seeds und Suchbudgets untersuchen.
4. Die zusätzliche offene HM-Alignment-Fitness korrekt als solche kennzeichnen.
5. Vor Aussagen zur Zukunft separate, vorzugsweise zeitliche Validierung planen.

Quellen: [PM4Py-API](https://processintelligence.solutions/app/pm4py/api/api/pm4py.discovery.html),
[Genetic Process Mining (2005)](https://doi.org/10.1007/11494744_5),
[Genetic Process Mining: Experimental Evaluation (2007)](https://doi.org/10.1007/s10618-006-0061-7),
[IMf](https://doi.org/10.1007/978-3-319-06257-0_6),
[Decision Mining (2013)](https://doi.org/10.1145/2480362.2480633).
Konkrete Werte und Grenzen stammen aus den im Repository gespeicherten Modellen,
Kandidatenmanifesten und Audits, nicht aus fremden Ergebnissen auf anderer Projektion.
