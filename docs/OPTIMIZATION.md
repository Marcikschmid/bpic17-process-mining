# Was wurde optimiert, nach welchem Kriterium, warum und wie?

Übersicht für den eigenen Berichtstext (Stichpunkte). Drei Ebenen wurden optimiert,
jede mit einer **vorab festgelegten** Regel; alle Werte auf denselben 31.509 Fällen.

| Ebene | Stellgrößen (Parameter) | Zielgröße | Nebenbedingungen | Verfahren | Ergebnis |
|---|---|---|---|---|---|
| 1. Discovery (IMf) | `noise_threshold`, Trainingsmenge der häufigsten Varianten (`training_coverage`) | Precision (exakte Präfix-Precision; für das gewählte Modell identisch mit Align-ET 0,5977) | sound; 80–82 % exakt abspielbare Fälle | Raster aus 40 Kandidaten, jeder auf allen Fällen bewertet | `frequent_0.60_imf_0.03`: 80,45 %, Precision 0,598 |
| 2. Modellstruktur (manuelle Änderungen) | 7 Blockänderungen am Prozessbaum (R1–R4, G1–G3), alle 128 Kombinationen | Align-ET-Precision | sound; 80–82 %; Generalization −0,01; Arc Degree −0,05; Knoten +25 % | vollständige Enumeration, danach Leitplankenprüfung in Rangfolge | G2+G3+R3+R4: 80,43 %, Precision 0,695 |
| 3. Decision Mining (CART je XOR) | Merkmalssatz (Case / +Event / +Verlauf); `max_depth`, `min_samples_leaf`, `class_weight` | Balanced Accuracy | Baumtiefe ≤ 5 (lesbare Regeln); nur Trainingsfälle | Stufenvergleich mit festen Parametern; Rastersuche mit gruppierter 5-fach-Kreuzvalidierung | Verlaufsmerkmale; Balanced Accuracy 0,562 → 0,810; 18 / 18 Splits über Zufallsniveau |
| 0. Eingabe (Event-Abstraktion, 12.11., D37) | welche Roh-Events Artefakte sind (Spiegel, W_-Completion, gleichzeitige Wiederholungen) | – (Belegregel, keine Metrik-Optimierung) | Edge Cases bleiben; alle Fälle bleiben | Zeitstempel-/Nachbarschaftsevidenz; danach Ebenen 1–3 neu: 55 IMf-Settings (≥ 80 %, max. Align-ET), 32 Edit-Kombinationen, CART je Split | Final 85,35 %, Align-ET 0,826, 56 Knoten; Decision Mining 11 Splits, 0,790; Zeilen 1–3 = Vorgängermodell |

## 1. Discovery: warum Precision, warum IMf, wie

- **Warum Precision:** Ziel ist ein Simulationsmodell. Nie beobachtete Pfade erzeugen unrealistische simulierte Fälle. IM erreicht schon 100 % Fitness, aber nur 0,293 Precision → Precision ist der Engpass.
- **Warum Fitness nur als Bedingung:** Vorgabe „mindestens 80 % aller Fälle“ (Folie 36); 100 % würde seltene, evtl. fehlerhafte Traces mitmodellieren (Tutorium).
- **Warum IMf:** garantiert sound und blockstrukturiert; `noise_threshold` ist der Hebel für Precision. Alpha, HM und Genetic liefern unbeschränkte Netze (keine Simulationsbasis).
- **Wie:** 19 Rauschschwellen auf dem ganzen Log + 21 Kandidaten auf häufigen Varianten (Abdeckung 0,60–0,80 × Rauschen 0–0,10); Auswahl: höchste Precision im Band, bei Gleichstand weniger Knoten.
- **Nicht optimiert:** HM (nur Sweep der `dependency_thresh`, um zu zeigen, dass jede Einstellung unbeschränkt bleibt), Genetic (festes Budget), Alpha (keine Parameter).

## 2. Manuelle Änderungen: warum diese Zielgröße, wie

- **Warum weiter optimieren:** Konformitätsdiagnose des IMf-Modells zeigt konkrete Precision-Lecks (z. B. `A_Complete` parallel zur ganzen Angebotsschleife) → gezielte Blockänderungen statt weiterer Parameter.
- **Wie:** jede Kombination exakt bewertet (Abdeckung, Align-ET, Soundness, Größe); Leitplanken für Generalization und Simplicity vorab fixiert; erster Kandidat in Precision-Rangfolge, der alle Leitplanken besteht.
- Details: [MANUAL_EDITS.md](MANUAL_EDITS.md).

## 3. Decision Mining: warum Balanced Accuracy, wie

- **Vorher:** feste Parameter (Tiefe 3, Blatt ≥ 50), Merkmale Case + Event → 10 von 18 Bäumen sagten nur die Mehrheit vorher (Bedingung „immer Weg B1“ ist keine Entscheidungsregel).
- **Warum Balanced Accuracy:** Zweige sind unausgewogen (Mehrheit oft 70–92 %); Accuracy belohnt Mehrheitsbäume. Balanced Accuracy = mittlerer Recall je Zweig → jeder Weg muss erkannt werden. Zufallsniveau = 1/Anzahl Zweige.
- **Merkmalssatz:** Stufenvergleich (gleiche Parameter, gleiche Testfälle) Case → +Event → +Verlauf (Feature Engineering); Verlaufsmerkmale nur aus Events vor der Entscheidung, im Log beobachtbar.
- **Hyperparameter:** Raster `max_depth` {2, 3, 4, 5} × `min_samples_leaf` {25, 50, 100, 200} × `class_weight` {keine, balanced} = 32 Einstellungen je Split.
- **Wie:** gruppierte 5-fach-Kreuzvalidierung nur auf Trainingsfällen (alle Entscheidungen eines Falls im selben Fold, kein Leakage zwischen Folds); Auswahl der besten mittleren Balanced Accuracy; innerhalb von 0,005 des Besten der Baum mit den wenigsten Blättern (Lesbarkeit der BPMN-Bedingungen). Testfälle erst ganz am Ende einmal verwendet.
- **Warum Tiefe ≤ 5:** Regeln müssen als XOR-Bedingungen im BPMN lesbar bleiben (≤ 5 Bedingungen je Pfad).
- **Ergebnis:** mittlere Balanced Accuracy (Test) Case 0,514 → +Event 0,562 → +Verlauf 0,744 (feste Parameter) → final optimiert 0,810; kein Zweig mehr unvorhergesagt; Kreuzvalidierung ≈ Test.
- **Preis:** bei 5 Splits einfache Accuracy unter der Mehrheitsquote; harte Guards bilden nur 7,09 % der Testfälle vollständig ab (vorher 9,46 %), weil jede Entscheidung eines Falls stimmen muss.
- Ergebnis je Split: `results/decision_mining/decision_tuning.tex`, Vergleich der Stufen: `feature_stages.csv`.
