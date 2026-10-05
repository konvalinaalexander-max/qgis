# Feldkarte Gemüsebetriebe

Flächen der Betriebe Imhof, Beerstecher, Gerber und Rathgeb aus den öffentlichen
Landwirtschaftsdaten der Kantone Zürich, Thurgau und Schaffhausen (Bezugsjahr 2025).

## Ergebnisse (Ordner `output/`)

- `Feldkarte_Gemuesebetriebe.html` – Karte im Browser (Doppelklick genügt; Hintergrundkarten brauchen Internet)
- `Feldkarte_Flaechen_4_Betriebe.xlsx` – Übersicht nach Kulturgruppe und Liste aller Flächen
- `Feldkarte_Auswahl_4_Betriebe.gpkg` – die Flächen der 4 Betriebe als GeoPackage
- `QGIS_Feldkarte_lokal.qgz` – QGIS-Projekt mit allen Betrieben ZH/TG/SH lokal; Betrieb hervorheben
  über die Projektvariable `betrieb` (Projekt → Eigenschaften… → Variablen)

## Weiterarbeiten mit Claude Code

Claude Code mit diesem Repository bzw. diesem Ordner starten. Die Datei `CLAUDE.md` wird automatisch gelesen und enthält
den ganzen Projektkontext. Ein guter erster Auftrag:

> Lies CLAUDE.md, richte die Python-Umgebung ein, baue mit ./run_all.sh alles neu und vergleiche
> die Zahlen mit den Kontrollwerten.

Der ganze Ordner kann verschoben werden (z. B. nach Dokumente); alle Pfade sind relativ.
Die Rohdaten liegen als ZIP in `data/raw_zip/` und werden beim ersten Lauf automatisch entpackt.

Datenquelle: Kantone Zürich, Thurgau und Schaffhausen, «Landwirtschaftliche Kulturflächen»
(Nutzungsflächen, Bewirtschaftungseinheiten), bezogen über geodienste.ch.
