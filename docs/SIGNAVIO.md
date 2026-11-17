# Finales Modell in SAP Signavio zeigen

Tutorium 29.10.: „At the end show the model with Signavio and add that to the report.“
Der Import braucht einen Signavio-Zugang und läuft deshalb manuell; die Dateien
sind vorbereitet und automatisch geprüft.

## Dateien (`results/signavio/`, erzeugt mit `scripts/export_signavio.py`)

Drei Varianten desselben Kontrollflusses. Sichtbar sind nur die Task-Namen und die unten
genannten Kantenbeschriftungen; Gateways und Events haben keine Namen.

| Datei | Name in Signavio | Beschriftung an den XOR-Kanten |
|---|---|---|
| `bpic17_final_plain.bpmn` | Control flow - BPIC-17 final model | keine |
| `bpic17_final_probabilities.bpmn` | Branch probabilities - BPIC-17 final model | Verzweigungswahrscheinlichkeit in Prozent (Schritt 1) |
| `bpic17_final_rules.bpmn` | Decision rules - BPIC-17 final model | ein Buchstabe je Kante (A–V); die gelernten Bedingungen stehen als Legende unter dem Diagramm |

Der Name steht als Prozess- und Diagrammname in der Datei; das unterscheidende Wort steht
vorn, weil der Signavio-Explorer lange Namen abschneidet.

Legende der Regel-Variante: ein Kasten je Entscheidung (D-Nummer wie in den Tabellen des
Berichts, Test-Accuracy), in Leserichtung des Diagramms. Zeilen mit demselben Buchstaben sind
Alternativen (ODER). Der Zweig mit den meisten Bedingungen steht als `otherwise`; das ist exakt,
weil die Blätter eines Entscheidungsbaums alle Fälle vollständig und überschneidungsfrei
aufteilen. Die Kanten behalten ihre vollständige `conditionExpression` (FEEL).

Layout (seit 14.11.2026, `src/bpmn_layout.py`): Die Layouts von PM4Py/Graphviz stellt Signavio
verzerrt dar (eigene Elementgrößen, geschwungene Kanten, negative Koordinaten). Alle Dateien
bekommen deshalb dasselbe blockstrukturierte Layout:

- Standardgrößen (Task 100×80, Gateway 40×40), nur rechtwinklige Kanten;
- Hauptlinie von links nach rechts, in vier Zeilen umbrochen (ca. 1430×1575; mit Legende
  ca. 1430×2353);
- an jedem XOR-Split bleibt der häufigste Zweig auf der Hauptlinie, Alternativen stehen
  darunter, Überspringen läuft als Umgehung unten;
- der leere Rückweg einer Schleife läuft unter dem Schleifenkörper zurück;
- die Legende steht in drei Spalten unter dem Diagramm, ohne Verbindungslinien.

Erste Fassung desselben Tages (Regelblöcke über den Gateways, Beschriftungen `B1: 64.8% (n=…)`,
Gateway-Namen) verworfen: im Signavio-Export unübersichtlich.

Prüfung je Datei (`results/signavio/manifest.json`): eindeutige IDs, jedes Element und jede
Annotation mit Diagrammform, jeder Pfeil rechtwinklig mit Wegpunkten, keine überlappenden
Formen, keine negativen Koordinaten, Kontrollflusssprache identisch zum finalen PNML.
In Signavio selbst nicht automatisch prüfbar: Position der Kantenbeschriftungen und
Zeilenumbruch in den Annotationen (legt Signavio fest).

## Import (Menünamen können je nach Signavio-Version abweichen)

1. SAP Signavio Process Manager öffnen, Zielordner im Explorer wählen. Ältere Importe
   derselben Dateien vorher löschen (gleiche oder frühere Namen: „diagram“,
   „BPIC-17 loan application …“).
2. Import für **BPMN 2.0 XML** wählen und die gewünschte Variante hochladen.
3. Diagramm im Editor öffnen; Darstellung prüfen (Pfeilbeschriftungen, Gateway-Namen).
4. Als Bild oder PDF exportieren und unter `report/figures/signavio_final_model.png`
   (bzw. `.pdf`) speichern.
5. In `report/sections/appendix.tex` den vorbereiteten, auskommentierten Block
   „Final Model in SAP Signavio“ einkommentieren und den Bericht bauen.

## Stichpunkte für den eigenen Text

- Werkzeugwechsel ohne Modelländerung: BPMN 2.0 als Austauschformat zwischen PM4Py und Signavio.
- Gleiches Modell, andere Darstellung: Signavio-Layout vs. Graphviz-Layout im Anhang.
- Signavio-Simulation wäre die Brücke zur nächsten Sitzung (Business Process Simulation).
- Falls Signavio die FEEL-Bedingungen nicht übernimmt: Regeln bleiben in der Legende sichtbar.
