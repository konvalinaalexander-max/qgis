# Feldkarte Gemüsebetriebe

Flächen der Betriebe Imhof, Beerstecher, Gerber und Rathgeb aus den öffentlichen
Landwirtschaftsdaten der Kantone Zürich, Thurgau und Schaffhausen (Bezugsjahr 2025).

## Ergebnisse (Ordner `output/`)

- `Feldkarte_Gemuesebetriebe.html` – Karte im Browser (Doppelklick genügt; Hintergrundkarten brauchen Internet).
  Dieselbe Datei ist auch die Online-Website.
- `Feldkarte_Flaechen_4_Betriebe.xlsx` – Übersicht nach Kulturgruppe und Liste aller Flächen
- `Feldkarte_Auswahl_4_Betriebe.gpkg` – die Flächen der 4 Betriebe als GeoPackage
- `QGIS_Feldkarte_lokal.qgz` – QGIS-Projekt mit allen Betrieben ZH/TG/SH lokal; Betrieb hervorheben
  über die Projektvariable `betrieb` (Projekt → Eigenschaften… → Variablen)

## Website online

Adresse (sobald GitHub Pages eingeschaltet ist): **https://konvalinaalexander-max.github.io/qgis/**

Die Website läuft auf Laptop und Handy. Auf dem Handy füllt die Karte den Bildschirm, unten liegt ein
Bereich mit *Betriebe · Kulturen · Flächen · Info*, den man mit dem Griff hochziehen oder antippen kann.
Eine Fläche antippen zeigt die Details mit *Route* (Apple/Google Maps), *map.geo.admin.ch* und *Teilen*
(Link, der genau diese Fläche öffnet). Der Standort-Knopf zeigt die eigene Position und nennt die Fläche,
auf der man steht. Über *Teilen → Zum Home-Bildschirm* (iPhone) bzw. *⋮ → Zum Startbildschirm*
(Android) lässt sich die Karte wie eine App starten.

### Einmalig einschalten

1. Auf GitHub im Repository: **Settings → Pages → Build and deployment → Source: «GitHub Actions»**.
2. Die Änderungen auf den Branch `main` bringen (Pull Request mergen).
3. Unter **Actions** erscheint «Website veröffentlichen»; nach etwa einer Minute ist die Seite online.
   Falls der erste Lauf vor Schritt 1 gestartet ist: im Lauf **Re-run jobs** wählen.

### Aktualisieren

`./run_all.sh` ausführen, Änderungen committen und auf `main` pushen – GitHub veröffentlicht die neue
Fassung automatisch. Von Hand: *Actions → Website veröffentlichen → Run workflow*.

Lokal genau so ansehen wie online: `python3 -m http.server -d work/online 8000`, dann
http://localhost:8000 öffnen.

### Sichtbarkeit

Die Website ist öffentlich: Wer den Link hat, kann sie öffnen. Suchmaschinen sind ausgeschlossen
(`noindex`); einschalten in `config/projekt.json` → `online.suchmaschinen: true`. Das Repository selbst
ist ebenfalls öffentlich.

## Weiterarbeiten mit Claude Code

Claude Code mit diesem Repository bzw. diesem Ordner starten. Die Datei `CLAUDE.md` wird automatisch gelesen und enthält
den ganzen Projektkontext. Ein guter erster Auftrag:

> Lies CLAUDE.md, richte die Python-Umgebung ein, baue mit ./run_all.sh alles neu und vergleiche
> die Zahlen mit den Kontrollwerten.

Der ganze Ordner kann verschoben werden (z. B. nach Dokumente); alle Pfade sind relativ.
Die Rohdaten liegen als ZIP in `data/raw_zip/` und werden beim ersten Lauf automatisch entpackt.

Datenquelle: Kantone Zürich, Thurgau und Schaffhausen, «Landwirtschaftliche Kulturflächen»
(Nutzungsflächen, Bewirtschaftungseinheiten), bezogen über geodienste.ch.
Hintergrundkarten © swisstopo. Schriften: IBM Plex (SIL Open Font License, `web/vendor/fonts/OFL.txt`).
