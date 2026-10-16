# BPIC-17-Datensatz

Der vollständige BPIC-17 Event Log wurde am 16.10.2026 heruntergeladen und anhand der Dateigröße und der von der Quelle bereitgestellten MD5-Prüfsummen verifiziert. Für den Einstieg wird keine Datenbankinstallation benötigt.

- `raw/`: unveränderte Originaldatei, z. B. XES oder komprimiertes XES.
- `processed/`: reproduzierbar erzeugte Zwischenstände.

## Quelle und Dateien

- Titel: BPI Challenge 2017.
- Autor: Boudewijn van Dongen; veröffentlicht 2017.
- DOI: https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b
- Landingpage: https://data.4tu.nl/articles/dataset/BPI_Challenge_2017/12696884
- Öffentliche Metadaten-API: https://api.figshare.com/v2/articles/12696884
- Lizenzbezeichnung laut Metadaten: **4TU General Terms of Use**, https://doi.org/10.4121/resource:terms_of_use
- `raw/BPI Challenge 2017.xes.gz`: vollständiger Original-Log, 29.658.747 Bytes; keine Offer-only- oder vorgefilterte Variante.
- `raw/DATA.xml`: begleitende Original-Metadaten, 7.581 Bytes.
- `manifest.json`: Herkunft, Verifikationszeitpunkt, Dateigrößen, Quell-MD5 und lokal berechnete SHA-256-Prüfsummen.

Die Quelldatei bleibt komprimiert und unverändert. Das Gzip enthält XML im XES-Format. Ein Bibliografieeintrag liegt unter `report/references.bib`.

## Download reproduzieren

Aus dem Repository-Hauptordner, mit Python 3.9 oder neuer (keine zusätzlichen Pakete erforderlich):

```powershell
python scripts/download_data.py
```

Das Skript lädt beide Originaldateien, verifiziert sie und erstellt das Manifest. Vorhandene passende Dateien werden erneut verifiziert; abweichende Dateien werden nicht überschrieben.

Die Datendateien selbst sind in `.gitignore` ausgeschlossen. Im GitHub-Repository liegen das Skript, die Anleitung und das Manifest. Für die späteren Analysen müssen alle Filter und Vorverarbeitungsschritte zusätzlich dokumentiert werden.
