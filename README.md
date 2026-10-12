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

Adresse: **https://konvalinaalexander-max.github.io/qgis/** (GitHub Pages, seit 5.10.2026)

**Startseite: Karte der Region** (seit 12.10.2026, Details in `docs/region.md`). Sie zeigt alle landwirtschaftlichen
Flächen der rund 10'700 Betriebe, die im Gebiet (Flächen der 4 Betriebe + 20 km) Land bewirtschaften – aus allen
Kantonen, deren Daten frei erhältlich sind. Eine Fläche antippen: Alle Flächen desselben Betriebs leuchten auf,
dazu Hof (amtlicher Standort mit Adresse), Fläche, Kulturen und Gemeinden. Die Liste zeigt die Favoriten zuoberst
(Imhof grün, Beerstecher, Gerber, Rathgeb), darunter die Betriebe im Kartenausschnitt; Suche nach Nummer, Ort,
Adresse oder Name, Filter Gemüse / Gewächshaus / Bio. Namen der Betriebe und interne Regionen
(mit Anteil jedes Betriebs je Region) sind verschlüsselt und erscheinen erst nach Eingabe des Passworts (Tab Info).
Neu bauen: `./run_region.sh`, ansehen: `python3 scripts/server.py`.

Die bisherige Detailansicht der 4 Betriebe liegt unter `betriebe.html` (Link im Tab Info):

Die Website läuft auf Laptop und Handy. Auf dem Handy füllt die Karte den Bildschirm, unten liegt ein
Bereich mit *Betriebe · Kulturen · Flächen · Info*, den man mit dem Griff hochziehen oder antippen kann.
Eine Fläche antippen zeigt zuoberst den Betrieb (farbig, mit Ort und Betriebsnummer), darunter Kultur,
Fläche, *Route* (Apple/Google Maps), *map.geo.admin.ch* und *Teilen* (Link, der genau diese Fläche öffnet).
Die Flächen der übrigen Betriebe treten dabei zurück; am Computer erscheint der Betrieb schon beim
Darüberfahren mit der Maus. Der Standort-Knopf zeigt die eigene Position und nennt die Fläche,
auf der man steht. Über *Teilen → Zum Home-Bildschirm* (iPhone) bzw. *⋮ → Zum Startbildschirm*
(Android) lässt sich die Karte wie eine App starten.

**Teilbetriebe und Bio:** Gerber und Rathgeb führen mehrere Firmen bzw. Standorte unter einer
Betriebsnummer, Imhof hat zwei Betriebsnummern. Bei Gerber und Rathgeb ordnen die Zürcher Daten jede
Fläche einer Produktionsstätte zu; danach (bzw. nach Betriebsnummer) sind sie auf der Karte getrennt (gleiche Farbe, verschiedene Schattierungen,
eigene Schaltflächen in der Legende, aufklappbar in der Betriebskarte). Der Farbmodus **Bio** zeigt,
welche Flächen als Bio gemeldet sind, welche zu einem Bio-Betrieb gehören, aber nicht als Bio gemeldet
sind (z. B. Gerber Bio Greens), welche nicht Bio sind und wo der Bio-Status unklar ist. Belege zu jedem
Betrieb: `docs/betriebe.md`. Excel und GeoPackage enthalten dazu die Spalten «Teilbetrieb» und «Bio-Status».

GitHub Pages ist eingeschaltet (Settings → Pages → Source: «GitHub Actions»). Bei einem neuen
Repository wäre das der einzige Schritt von Hand; danach einen Push auf `main` machen oder den Workflow
von Hand starten.

### Aktualisieren

`./run_all.sh` ausführen, Änderungen committen und auf `main` pushen – GitHub veröffentlicht die neue
Fassung automatisch. Von Hand: *Actions → Website veröffentlichen → Run workflow*.

Lokal genau so ansehen wie online: `python3 scripts/server.py`, dann http://localhost:8000 öffnen
(`python3 -m http.server` reicht nicht: die Vektorkacheln der Karte brauchen Range-Anfragen).

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
