# Modellverfeinerung: Assignment 3.3.3

**Ergebnis:** `frequent_0.60_imf_0.03`, als BPMN 2.0 exportiert. Exakt
**25.350 von 31.509 Fällen (80,4532 %)** sind vollständig replaybar. Bewertet
wird weiterhin die gemeinsame Completion-Projektion mit 475.306 Events.
Der vollständige Audit und alle 36 Tests sind bestanden. Reporttabellen,
Iterationsgrafik und finale BPMN-Modelltafel wurden visuell geprüft.

## BPMN ansehen und bearbeiten

Die offizielle Software **bpmn-js 18.31.0** ist projektlokal unter
`.tools/bpmn-js/` installiert. Paketquelle, npm-SHA-512 und Dateien-Prüfsummen
stehen in `docs/bpmn_viewer_manifest.json`. Die bpmn.io-Kennzeichnung bleibt erhalten.
Beim Anzeigen werden keine Bibliotheken von einem CDN geladen.

```powershell
.\.venv\Scripts\python.exe -m http.server 8787 --bind 127.0.0.1
```

Dann im Browser öffnen:
<http://127.0.0.1:8787/results/refinement/index.html>

Die Ansicht unterstützt Zoomen, Verschieben, Modellbearbeitung und Download als
BPMN oder SVG. Die Anfangsansicht zeigt das gesamte Modell; mit `+` lassen sich
die Beschriftungen lesen. Bei Bearbeitung oder Import eines anderen Modells
werden die ursprünglichen Kennzahlen ausgeblendet. Neue Änderungen sind erst
nach erneuter Bewertung belastbar. Die gespeicherten Analyseartefakte werden
durch Bearbeitung im Browser nicht automatisch verändert.

Das BPMN wurde in Chrome Headless mit separatem Profil geladen und als echte
bpmn-js-Darstellung überprüft. Die zusätzliche eingebettete Browserautomation
war wegen eines fehlenden Laufzeitpfads nicht verfügbar; die lokale Anwendung
und der Chrome-Import funktionieren. Die vollständigen statischen Exporte liegen
unter `results/refinement/final_bpmn.pdf`, `.svg` und `.png`.

## Schritte und Designentscheidungen

1. **IM als strukturelle Basis.** Die IM-Baseline ist sound und akzeptiert alle
   Fälle, hat aber nur 0,2926 Align-ET-Präzision. Der HM hat nachgewiesene tote
   Transitionen und einen unbeschränkten Zustandsraum. Seine hohe bedingte
   Präzision rechtfertigt ihn deshalb nicht als Simulationsbasis.
2. **Ziel vorher definieren.** Das operative Zielband beträgt 78–82 % vollständig
   replaybare Fälle. Innerhalb dieses Bands wird die höchste exakte
   Präfix-Präzision gewählt, bei Gleichstand die kleinere Knotenzahl. Die Zahl
   0,8 einer durchschnittlichen Fitness wird nicht als 80 % Fallabdeckung verwendet.
3. **IMf auf dem vollständigen Log.** Grobe und feinere Rauschschwellen wurden
   ausprobiert. Sie führen zu wechselnden Strukturentscheidungen und treffen das
   Zielband nicht überzeugend. Ein höherer Parameterwert bedeutet hier nicht
   automatisch ein in jeder Hinsicht besseres oder einfacher strukturiertes Modell.
4. **Häufige Varianten als Discovery-Eingabe.** Als zweite Familie werden ganze
   Varianten allein nach Häufigkeit sortiert; bei Gleichstand entscheidet die
   lexikografische Aktivitätsfolge. Variantsätze bis 60, 65, 70, 75 und 80 % der
   Fallhäufigkeit werden dokumentiert. Im ausgewählten Modell beträgt die
   Trainingszielabdeckung 60 %, die IMf-Rauschschwelle 0,03. Die tatsächlich
   verwendete Fall-/Variantenanzahl steht in `final_metrics.json`.
5. **Alle Fälle zur Bewertung behalten.** Die eingeschränkte Discovery-Eingabe
   wird offen ausgewiesen. Jede Qualitäts- und Replay-Auswertung verwendet
   anschließend sämtliche 31.509 Fälle. Das Ergebnis ist kein Durchschnitt über
   die gefilterte Trainingsmenge. Die Modellauswahl nutzt den Evaluationslog;
   es handelt sich nicht um ein unabhängiges Testset oder eine Vorhersagevalidierung.
6. **Domänenstruktur prüfen.** Das gewählte Modell besitzt Antragsaufnahme,
   Angebotserstellung mit Wiederholungen, Dokumentprüfung mit Nachforderungen
   sowie alternative Antragsausgänge. `A_Concept` liegt in allen Fällen vor
   `A_Accepted`; die drei terminalen A-Zustände treten in diesem Log nicht gemeinsam
   in einem Fall auf. Diese beobachteten Regeln werden vom gewählten Modell
   unterstützt. Mehrere Angebote bleiben möglich: im Log haben 27,164 % der Fälle
   mehr als ein `O_Create Offer`. `O_Cancelled` wird nicht mit dem Abbruch des
   gesamten Antrags gleichgesetzt; andere Angebote können trotz erfolgreichem
   Antrag storniert werden.
7. **BPMN ohne Verhaltenswechsel.** Der ausgewählte Prozessbaum liefert sowohl
   das bewertete Petri-Netz als auch das BPMN. Nach XML-Export und Neuimport wird
   das BPMN zurück in ein Petri-Netz konvertiert. Eine vollständige
   Epsilon-Automaten-Sprachäquivalenzprüfung bestätigt dieselben erlaubten
   Aktivitätsfolgen, einschließlich Schleifen und Parallelität.

Alle 40 Kandidaten stehen in `results/refinement/iteration_metrics.csv`.
Die beiden Kandidatenmanifeste enthalten Parameter, Trainingsumfang, Modelle,
exakte Abdeckung, Präfix-Präzision und Komplexität. Die ursprünglichen IM-/HM-
Dateien werden nicht verändert. Dieser Lauf enthält keine manuell nachgezeichnete
BPMN-Grafik mit abweichender Semantik.

## Qualitätsvergleich

| Maß | IM-Baseline | Verfeinert |
|---|---:|---:|
| Exakt vollständig replaybare Fälle | 100 % | 80,4532 % |
| Token-Log-Fitness | 1,0000 | 0,9875 |
| PM4Py Align-ET-Präzision | 0,2926 | 0,5977 |
| Token-Generalization | 0,9757 | 0,9912 |
| Arc-Degree-Simplicity | 0,6170 | 0,7008 |
| Knoten / Kanten | 87 / 114 | 89 / 108 |
| Extended Cardoso | 47 | 52 |
| Extended Cyclomatic | 1.552 | 551 |

Die Präzision steigt deutlich und der Zustandsraum wird kleiner. Die Knotenzahl
und Cardoso-Komplexität steigen leicht; es verbessern sich also nicht sämtliche
Komplexitätsmaße. Präzision 0,5977 ist weiterhin moderat und belegt keine perfekte
Prozessabbildung. Align-ET schließt 40.338 von 443.797 gewichteten nichtleeren
Präfixen aus; dieser Anteil muss bei der Interpretation mitberücksichtigt werden.

Token Replay meldet 81,6243 % passende Fälle, die exakte Sprachprüfung dagegen
80,4532 %. Token Replay ist heuristisch; PM4Pys Standard kann insbesondere
Aktivitäten außerhalb des Modells bei seinem Fit-Flag ignorieren. Für das
80-%-Kriterium wird deshalb ausschließlich die vollständige exakte Sprachprüfung
verwendet. Fitness und Fallanteil bleiben getrennte Größen.

## Beschleunigung ohne Stichproben-Metrik

Der vollständige Zustandsgraph besitzt 187 Markierungen. `src/finite_precision.py`
berechnet darin dieselben optimalen Präfix-Endmarkierungen wie PM4Pys
Align-ET-Suche: synchrone Schritte kosten 0, unsichtbare Schritte 1; sichtbare
Modell-/Log-Abweichungen sind in der Präfixsuche ausgeschlossen. Gewichtete
Epsilon-Abschlüsse ersetzen das wiederholte Erzeugen synchroner Produktnetze.

Alle 27.816 Präfixe gehen in den Gesamtwert ein, einschließlich globaler
Häufigkeiten und der PM4Py-Korrektur für den leeren Präfix. Tests vergleichen den
optimierten Solver direkt mit unverändertem PM4Py, auch bei unpassenden Präfixen,
Mehrfachhäufigkeiten und unterschiedlich teuren Tau-Pfaden. Zusätzlich wurden
191 Präfixe des tatsächlichen Modells mit der originalen PM4Py-Suche verglichen.
Diese Gegenprüfungen ersetzen nicht den Log; die berechnete Metrik verwendet
weiterhin alle Präfixe. Das Audit steht in `fast_alignment_precision.json`.

## Vergleich mit veröffentlichten BPIC-17-Arbeiten

Die recherchierten Originalberichte sind unter `literature/` getrennt abgelegt;
ihre Quellen und Prüfsummen stehen in `literature/bpic2017/sources.json`.

- **Rodrigues et al., akademischer Gewinner:** 19 Petri-Netz-Versionen; berichtet
  werden 97,28 % Fitness und 98,72 % Präzision. 100 Fälle werden entfernt und
  Aktivitäten im Modellierungsprozess abstrahiert. Die Werte sind keine direkte
  Rangliste gegenüber unserer Completion-Projektion oder unserer exakten
  Fallabdeckung. Übernommen wird das Prinzip protokollierter Verfeinerungen.
  [Original, PDF-Seiten 3 und 7–9](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_academic.pdf).
- **Povalyaeva et al., studentischer Gewinner:** BPMN 2.0 mit Celonis; die
  Darstellung beschreibt die Phasen Antrag, Angebote und Dokumentprüfung.
  Sie dient als strukturelle Domänenreferenz. Ein unmittelbar vergleichbarer
  Qualitätswert wird daraus nicht übernommen.
  [Original, PDF-Seite 3](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_student.pdf).
- **Blevi, Delporte und Robbrecht, KPMG:** ungefähr 22 Tage mittlere Durchlaufzeit
  und 27 % Fälle mit mehreren Angeboten. Unser Rohdatenmittel 21,900 Tage und
  27,164 % Mehrfachangebotsfälle sind damit konsistent. Das ist ein Vergleich
  des Datenverständnisses, kein Beleg besserer Modellqualität.
  [Original, PDF-Seiten 2–3](https://ais.win.tue.nl/bpi/2017/bpi2017_winner_professional.pdf).

Maschinenlesbarer Vergleich: `results/refinement/literature_comparison.json`;
lesbare Zahlenübersicht: `results/refinement/refinement_summary.md`.

## Grenzen und weitere Arbeit

Nicht repräsentiert sind `O_Sent (online only)`, `W_Assess potential fraud` und
`W_Call after offers` in der Completion-Projektion. Betroffene Fälle bleiben in
der Bewertung. Die Replay-Anteile sind nach Ausgang unterschiedlich: Pending
82,69 %, Cancelled 82,28 %, Denied 67,19 % und Fälle ohne terminalen A-Zustand
0 %. Das Modell unterschätzt daher insbesondere bestimmte Ablehnungs- und
Ausnahmeabläufe. Für Simulation sind diese Ausschlüsse zu prüfen; zusätzlich
fehlen kalibrierte Zeit-/Ressourcenverteilungen und Entscheidungswahrscheinlichkeiten.

Die berichtete Generalization ist eine Häufigkeitsheuristik auf dem verwendeten
Log. BPMN-Soundness und gute Kennzahlen allein validieren noch keine realistische
Simulation. Die Ausrichtung auf ungefähr 80 % Abdeckung folgt der Aufgabe und
ist keine empirisch begründete Vollständigkeitsgrenze des Kreditprozesses.

3.3.4 (Alignment-basiertes Decision Mining an allen finalen XORs) ist separat in
`docs/DECISION_MINING.md` implementiert und geprüft. Harte Guards reduzieren die
vollständige Testfallabdeckung auf 10,19 %; die 80,45 % hier beziehen sich auf die
Struktur ohne Guards. Die Advanced-Analyse bleibt offen. Wissenschaftliche
Interpretation und Berichtstexte werden weiterhin vom Autor selbst verfasst;
im Bericht werden hier nur faktische Tabellen, Grafiken und Quellen ergänzt.

## Reproduzieren und prüfen

```powershell
.\.venv\Scripts\python.exe scripts/refine_model.py
.\.venv\Scripts\python.exe scripts/refine_model.py --thresholds .155 .16 .165 .17 .18 .19
.\.venv\Scripts\python.exe -m scripts.refine_frequent
.\.venv\Scripts\python.exe -m scripts.refine_frequent --training-coverage .60 .65 --thresholds .03 .05 .06 .07 .08
.\.venv\Scripts\python.exe -m scripts.export_refined_model --prepare-only
.\.venv\Scripts\python.exe -m scripts.accelerate_refinement
.\.venv\Scripts\python.exe -m scripts.export_refined_model
.\.venv\Scripts\python.exe -m scripts.render_refinement
.\.venv\Scripts\python.exe -m scripts.verify_refinement
```

Der erste Export legt das Modell an und prüft die BPMN-Konvertierung. Nach Erzeugung
des schnellen Präzisions-Audits übernimmt ein erneuter Export dessen vollständig
geprüfte Kennzahl und berechnet die übrigen Qualitätsdimensionen.
