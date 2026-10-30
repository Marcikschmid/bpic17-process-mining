# Finales Modell in SAP Signavio zeigen

Tutorium 29.10.: „At the end show the model with Signavio and add that to the report.“
Der Import braucht einen Signavio-Zugang und läuft deshalb manuell; die Dateien
sind vorbereitet und automatisch geprüft.

## Dateien (`results/signavio/`, erzeugt mit `scripts/export_signavio.py`)

| Datei | Inhalt | Empfohlen für |
|---|---|---|
| `bpic17_final_probabilities.bpmn` | finaler Kontrollfluss; XOR-Gateways `D01…`/`M01…`; jeder ausgehende XOR-Pfeil mit Wahrscheinlichkeit und Anzahl (Decision Mining Schritt 1) | Abbildung im Bericht |
| `bpic17_final_rules.bpmn` | gleiches Modell mit gelernten Bedingungen (`conditionExpression`, FEEL) und Regelblöcken als Textannotation (Schritt 2) | Zusatz/Anhang |

Prüfung je Datei (`results/signavio/manifest.json`): eindeutige IDs, jedes Element mit
Diagrammform, jeder Pfeil mit Wegpunkten, Kontrollflusssprache identisch zum finalen PNML.

## Import (Menünamen können je nach Signavio-Version abweichen)

1. SAP Signavio Process Manager öffnen, Zielordner im Explorer wählen.
2. Import für **BPMN 2.0 XML** wählen und `bpic17_final_probabilities.bpmn` hochladen.
3. Diagramm im Editor öffnen; Darstellung prüfen (Pfeilbeschriftungen, Gateway-Namen).
4. Als Bild oder PDF exportieren und unter `report/figures/signavio_final_model.png`
   (bzw. `.pdf`) speichern.
5. In `report/sections/appendix.tex` den vorbereiteten, auskommentierten Block
   „Final Model in SAP Signavio“ einkommentieren und den Bericht bauen.

## Stichpunkte für den eigenen Text

- Werkzeugwechsel ohne Modelländerung: BPMN 2.0 als Austauschformat zwischen PM4Py und Signavio.
- Gleiches Modell, andere Darstellung: Signavio-Layout vs. Graphviz-Layout im Anhang.
- Signavio-Simulation wäre die Brücke zur nächsten Sitzung (Business Process Simulation); Wahrscheinlichkeiten aus Schritt 1 als Verzweigungsparameter.
- Falls Signavio die FEEL-Bedingungen nicht übernimmt: Regeln bleiben als Textannotationen sichtbar.
