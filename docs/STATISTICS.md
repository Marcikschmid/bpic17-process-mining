# Einfache Event-Log-Analyse: Assignment 3.2

Diese Auswertung verwendet `data/raw/BPI Challenge 2017.xes.gz` vollständig und
unverändert. Sie ist von der Completion-Projektion für Discovery und
Qualitätsbewertung getrennt. Die Eingabe-Prüfsumme muss mit `data/manifest.json`
übereinstimmen. Es gibt keine Stichprobe, Filterung oder Imputation.

**Stand:** vollständig berechnet; vier neue Unit-Tests und unabhängiger
XML-Audit über alle 31.509 Fälle und 1.202.267 Events bestanden.
Auch die gesamte Testsuite besteht (29 Tests). Der Bericht wurde kompiliert;
Statistik-Tabelle, Attributprofil und beide Abbildungen wurden in der PDF
visuell geprüft (Seiten 1, 4, 5 und 6 des aktuellen Builds).

| Kerngröße | Ergebnis |
|---|---:|
| Aktivitätsvarianten | 15.930 |
| (Aktivität, Lifecycle)-Varianten | 16.692 |
| Case-/Event-Attributnamen | 4 / 15 |
| Case-Länge: Mittelwert / Populations-SD | 38,156 / 16,715 Events |
| Case-Dauer: Mittelwert / Populations-SD | 21,900 / 13,169 Tage |
| Kategoriale Event-Attribute mit / ohne technische IDs | 9 / 7 |
| Unterschiedliche Ressourcenwerte | 149 |
| Case-Anteil der Top-10-Varianten | 15,33 % |

## Ausführen

```powershell
.\.venv\Scripts\python.exe scripts/analyze_log.py
.\.venv\Scripts\python.exe scripts/render_log_statistics.py
.\.venv\Scripts\python.exe scripts/verify_log_statistics.py
```

Der erste Aufruf lädt den gesamten Roh-Log über die bestehende PM4Py-Funktion
`load_event_log()`. Der zweite erzeugt faktische Tabellen und Abbildungen unter
`results/`. Der dritte liest die ursprüngliche gzip-XES-Datei mit einem
unabhängigen XML-Reader erneut, ohne PM4Py oder `src/log_statistics.py` aufzurufen.
Er vergleicht jeden einzelnen Fall und überprüft Variantenhäufigkeiten,
Attributprofile, Mittelwerte, Standardabweichungen, Quantile und Zeiteinheiten.

## Definitionen

- **Case:** ein XES-Trace mit eindeutiger `concept:name`-Fall-ID. Alle Cases
  bleiben enthalten. Leere Traces oder fehlende Pflichtwerte werden als Fehler
  behandelt und nicht stillschweigend weggelassen.
- **Event:** jedes ursprüngliche Event, einschließlich `schedule`, `start`,
  `suspend`, `resume`, `complete` und anderer Lifecycle-Zustände.
- **Variante:** die vollständige Folge von `concept:name`-Aktivitätsnamen in der
  ursprünglichen XES-Reihenfolge. Wiederholungen und Leerzeichen bleiben erhalten.
  Zusätzlich wird die alternative Anzahl von `(Aktivität, Lifecycle)`-Varianten
  exportiert. Diese Definitionen dürfen nicht mit der Discovery-Projektion
  vermischt werden.
- **Case-Länge:** Anzahl aller Events des Falls.
- **Case-Dauer:** spätester minus frühester Event-Zeitstempel, nach UTC
  umgerechnet. Das ist verstrichene Kalenderzeit; Wochenenden, Wartezeiten und
  Unterbrechungen bleiben enthalten. Die Dauer ist keine reine Bearbeitungszeit.
  Die Variante wird durch diese Min-/Max-Berechnung nicht umsortiert.
- **Standardabweichung:** im geforderten Vergleich die Populations-SD (`ddof=0`)
  über alle bereitgestellten Fälle. Die Stichproben-SD (`ddof=1`) steht zusätzlich
  im JSON. Dauerwerte werden aus Sekunden durch Division durch 60 bzw. 86.400
  umgerechnet; Mittelwerte und SDs werden identisch skaliert.
- **Attributnamen:** Vereinigung der tatsächlich vorkommenden Namen, getrennt
  nach Case- und Event-Ebene. Ein Name auf beiden Ebenen wird je Ebene gezählt.
  IDs und Standard-XES-Felder werden mitgezählt.
- **Kategorial:** beobachtete Nicht-Null-Werte sind Strings oder Booleans.
  `EventID` und `OfferID` zählen als nominale Kennungen mit; eine zweite Zahl
  schließt diese beiden technischen IDs aus. `org:resource` bleibt kategorial,
  weil die Ressource eine nominale Ausprägung ist. Hohe Kardinalität macht eine
  ID nicht zu einer metrischen Größe und begründet keine Verwendung als Feature.
- **Numerisch:** Integer-/Float-Größen einschließlich `NumberOfTerms` und
  `CreditScore`. Wenige verschiedene Werte reichen nicht für eine Umdeutung
  solcher Größen zu Kategorien. Zeitstempel bilden eine eigene Klasse.
- **Fehlender Wert:** Attribut fehlt am Case/Event oder ist explizit `null`.
  Leere Strings werden als vorhandene Werte erhalten. Anzahl und Anteil beziehen
  sich auf alle Cases bzw. alle Events, nicht nur auf den jeweiligen Eventtyp.
- **Quantile:** lineare Interpolation (Hyndman-Fan Typ 7). Alle Verteilungen und
  Histogramme umfassen sämtliche Fälle, ohne Ausreißer auszublenden.

## Zusätzliche Statistiken

Die Auswertung enthält mehr als die geforderten zwei zusätzlichen Statistiken:

- Häufigkeit aller Aktivitäten und aller Lifecycle-Zustände.
- Anzahl unterschiedlicher Ressourcen einschließlich Systemkennungen.
- Anteil der Cases in den häufigsten 1, 5 und 10 Varianten, Anzahl der nur einmal
  auftretenden Varianten und kumulierte Variantenabdeckung.
- Median, Quartile, 95%-Quantil, Minimum und Maximum von Länge und Dauer.
- Case-Starts je UTC-Kalendermonat und gesamter beobachteter Zeitbereich.
- Fehlende Attributwerte, Kardinalitäten und Zeitstempel-Reihenfolgefehler.

Aktivitätshäufigkeiten zählen Events. Wiederholte Lifecycle-Schritte derselben
Arbeitstätigkeit können diese Häufigkeiten stark erhöhen; sie sind keine Anzahl
von Anträgen mit dieser Aktivität. Ressourcenwerte sind beobachtete Kennungen
und werden nicht automatisch als Anzahl menschlicher Mitarbeitender interpretiert.

## Ergebnisse und Trennung zum Bericht

| Datei | Inhalt |
|---|---|
| `results/tables/raw_log_statistics.md` | Lesbarer Überblick und Attributprofil |
| `results/tables/raw_log_statistics.json` | Alle Kennzahlen, Definitionen, Versionen und Prüfsummen |
| `results/tables/raw_case_statistics.csv` | Jeder Fall: Länge, Dauer, UTC-Zeiten, Varianten-ID und Reihenfolgeprüfung |
| `results/tables/raw_variants.csv` | Alle Varianten: SHA-256-ID, Fallhäufigkeit, Länge und Rang |
| `results/tables/raw_attribute_profile.csv` | Case-/Event-Attributtypen, Kardinalitäten und fehlende Werte |
| `results/tables/raw_activity_counts.csv` | Häufigkeit jedes unveränderten Aktivitätsnamens |
| `results/tables/raw_lifecycle_counts.csv` | Häufigkeit aller Lifecycle-Zustände |
| `results/tables/raw_monthly_cases.csv` | Case-Starts nach UTC-Monat |
| `results/tables/raw_log_statistics_verification.json` | Unabhängiger vollständiger XML-Audit |
| `results/tables/raw_statistics_artifacts.json` | Prüfsummen der gerenderten Artefakte |
| `results/figures/raw_log_overview.*` | Länge, Dauer, Lifecycle-Häufigkeiten und Variantenabdeckung |
| `results/figures/raw_activity_frequencies.*` | Alle Aktivitätshäufigkeiten; tatsächliches nachfolgendes Leerzeichen markiert |

Die Analyseskripte schreiben ausschließlich unter `results/`. Ausgewählte PDFs
und LaTeX-Tabellen werden separat nach `report/figures/` und `report/tables/`
kopiert. Der Bericht lädt keine Rohdaten und führt kein Python aus. Faktische
Tabellen und Abbildungen ersetzen nicht die eigene wissenschaftliche
Interpretation des Autors.

Die vier Unit-Tests in `tests/test_log_statistics.py` prüfen insbesondere
Variantenhäufigkeiten, Lifecycle-Abgrenzung, Zeitstempel außerhalb der Reihenfolge,
Zeitzonen, fehlende Attribute und die SD-Konvention. Der vollständige XML-Audit
prüft die tatsächlich erzeugten Resultate zusätzlich direkt gegen die Quelldatei.
