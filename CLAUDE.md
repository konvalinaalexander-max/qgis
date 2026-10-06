# Feldkarte Gemüsebetriebe – Projektkontext für Claude Code

Dieses Projekt zeigt die landwirtschaftlichen Flächen ausgewählter Gemüsebetriebe (aktuell 4: Imhof,
Beerstecher, Gerber, Rathgeb) auf einer Karte. Grundlage sind die öffentlichen Geodaten
«Landwirtschaftliche Kulturflächen» der Kantone (geodienste.ch). Die Ergebnisse sind eine
Website (eine HTML-Datei, auch online über GitHub Pages, für Laptop und Handy), eine Excel-Tabelle,
ein GeoPackage und ein QGIS-Projekt.

Weiterführend: `docs/daten.md` (Quellen, Felder, Downloads) und `docs/betriebe.md`
(wie die Betriebsnummern zugeordnet wurden, offene Punkte).

## Arbeitsweise mit Alex

- Antworten auf Deutsch, Schweizer Schreibweise (ss statt ß).
- Alex arbeitet auf einem Mac (Apple Silicon) mit QGIS 3.44 LTR, deutsche Oberfläche.
  Anleitungen also mit macOS-Menüs und -Tastenkürzeln.
- PDF-Dokumente: objektiv und neutral, ohne Anrede, ohne Dialogstil, ohne Hinweise auf KI.
- Vor jedem PDF alles fact-checken. Werden dabei Fehler gefunden: kein PDF erzeugen, sondern
  die Fehler benennen und gemeinsam anschauen.
- Schritt-für-Schritt-Protokolle nur erstellen, wenn ausdrücklich verlangt.
- Rohdaten in `data/raw/` und `data/raw_zip/` nie verändern. Alles in `work/` und `output/` ist neu erzeugbar.
- Git-Repository: `github.com/konvalinaalexander-max/qgis`. Alex arbeitet zusätzlich mit einer
  lokalen Kopie in `~/Downloads/Feldkarte-Projekt` (dort liegen die Rohdaten schon entpackt).

## Ordner

```
config/projekt.json    Betriebe (Name, Betriebsnummern, Farbe, Hinweis, Bio-Status, Teilbetriebe), Kantone +
                       Datenversion, Kulturgruppen + Farben, Dateinamen, Startwert für @betrieb in QGIS
config/gemeinden.json  BFS-Nummer -> [Gemeindename, Kanton] (alle 381 Nummern, die in den
                       Daten ZH/TG/SH vorkommen; 3393 fehlt, wird als «BFS 3393» angezeigt)
data/raw_zip/          die 6 Downloads von geodienste.ch als ZIP (ca. 140 MB) – so im Git-Repo
data/raw/              entpackt (ca. 330 MB, nicht im Git). Fehlt ein Ordner, entpacken die
                       Skripte ihn automatisch aus data/raw_zip/
scripts/               Datenaufbereitung, nummeriert in Ausführungsreihenfolge
web/template.html      Vorlage der Website (Leaflet), web/vendor/leaflet/ = Leaflet 1.9.4,
                       web/vendor/fonts/ = IBM Plex Sans (variabel) + Mono, latin, OFL-Lizenz
web/online/            Dateien nur für die Online-Fassung: icon.svg (Quelle, auch Favicon), App-Icons,
                       vorschau.jpg (Link-Vorschau 1200×630)
.github/workflows/     website.yml: veröffentlicht die Website bei jedem Push auf main (GitHub Pages)
work/                  Zwischenstände (auswahl.gpkg, Screenshots, online/) – darf gelöscht werden
output/                Ergebnisse: Website, Excel, GeoPackage, QGIS-Projekt
anleitungen/           HTML-Quellen + Render-Skript der beiden QGIS-PDF-Anleitungen
docs/                  Hintergrund zu Daten und Betrieben
```

## Einrichtung (einmalig)

```bash
cd <Projektordner>
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
Falls `python3` fehlt: Xcode Command Line Tools (`xcode-select --install`) oder Homebrew-Python.

## Alles neu bauen

```bash
./run_all.sh          # Schritte 1–4 und 6: Auswahl, Website, GeoPackage, Excel, Online-Fassung (work/online)
```

| Schritt | Skript | liest | schreibt |
|---|---|---|---|
| 1 | `scripts/01_auswahl.py` | `data/raw/lwb_*` | `work/auswahl.gpkg` |
| 2 | `scripts/02_website.py` | `work/auswahl.gpkg`, `web/` | `output/Feldkarte_Gemuesebetriebe.html` |
| 3 | `scripts/03_gpkg.py` | `work/auswahl.gpkg` | `output/Feldkarte_Auswahl_4_Betriebe.gpkg` |
| 4 | `scripts/04_excel.py` | `output/*.gpkg` | `output/Feldkarte_Flaechen_4_Betriebe.xlsx` |
| 5 | `scripts/05_qgis_projekt.py` (PyQGIS) | `output/*.gpkg`, `data/raw/` | `output/QGIS_Feldkarte_lokal.qgz` |
| 6 | `scripts/06_online.py` (nur Standardbibliothek) | `output/*.html`, `web/online/` | `work/online/` (bzw. `--out`) |
| – | `scripts/pruefen_qgis.py` (PyQGIS) | `output/*.qgz` | Prüfausgabe |
| – | `scripts/screenshots.py` (optional, Playwright) | `output/*.html` | `work/screenshots/`; mit `--vorschau` auch `web/online/vorschau.jpg` |
| – | `scripts/icons.py` (optional, Playwright) | `web/online/icon.svg` | `web/online/*.png` |

**Schritt 5 braucht PyQGIS**, das nur im Python von QGIS steckt:
- Weg A (am einfachsten): In QGIS *Erweiterungen → Python-Konsole*, Symbol *Editor anzeigen*,
  Skript öffnen, *Skript ausführen*. Das offene Projekt bleibt unverändert. Danach
  `output/QGIS_Feldkarte_lokal.qgz` über *Projekt → Öffnen…* laden.
- Weg B (Terminal): das mit QGIS gelieferte Python verwenden. Pfad zuerst suchen, z. B.
  `find /Applications/QGIS*.app/Contents -maxdepth 3 -name 'python3*'`. Den Pfad nicht raten,
  er hängt vom QGIS-Paket ab. Ohne Bildschirm: `QT_QPA_PLATFORM=offscreen`.
- Falls `__file__` in der QGIS-Konsole fehlt, liest das Skript den Projektordner aus der
  Umgebungsvariable `FELDKARTE_DIR` (Standard `~/Downloads/Feldkarte-Projekt`).

**Kontrollwerte nach einem Neubau** (Bezugsjahr 2025; Hauptkulturen ohne überlagernde Elemente):

| Betrieb | Betriebsnummern | Flächen | ha |
|---|---|---|---|
| Imhof | ZH0197/ 1/  1, ZH0197/ 1/702 | 246 | 91.63 |
| Beerstecher | ZH0191/ 1/ 55 | 173 | 132.70 |
| Gerber | ZH0172/ 1/700 | 232 | 253.15 |
| Rathgeb | ZH0042/ 1/850, TG39621 | 441 | 550.31 |
| Total | | 1'092 | 1'027.79 |

Teilbetriebe (nach Betriebsnummer bzw. amtlicher Produktionsstätte, `01_auswahl.py` gibt sie aus):

| Teilbetrieb | Zuordnung | Flächen | ha |
|---|---|---|---|
| Imhofbio, Eichhof Schwerzenbach | Betriebsnummer ZH0197/ 1/  1 | 245 | 90.61 |
| Gewächshaus Eichhof | Betriebsnummer ZH0197/ 1/702 (Bio-Status `offen`) | 1 | 1.02 |
| Gerber Bio Greens AG | PS ZH0172/ 1/ 47 (Zürcherstrasse 75, Fehraltorf) | 161 | 106.07 |
| Gerber Gemüsebau AG | PS ZH4561/ 1/  4 (Rosenackerstr. 7, Felben-Wellhausen) | 71 | 147.08 |
| Rathgeb Bio, Unterstammheim | PS ZH0042/ 1/ 48 | 227 | 288.86 |
| Rathgeb Bio, Ellikon an der Thur | PS ZH0218/ 1/ 30 (Neue Horgenbachstrasse 2/4, ehem. Kellermann) + ZH0218/ 1/ 36 | 202 | 253.26 |
| BioFresh AG, Tägerwilen | Betriebsnummer TG39621 | 12 | 8.18 |

`pruefen_qgis.py` muss «absolute Pfade: 0», alle Layer gültig und für jede Betriebsnummer einen
Treffer melden (z. B. ZH0197/ 1/  1: 77 BE / 90.61 ha; TG39621: 9 BE / 10.17 ha).

## Häufige Aufgaben

- **Website online aktualisieren:** `./run_all.sh`, committen, auf `main` pushen. Der Workflow
  `.github/workflows/website.yml` baut mit `06_online.py --url <Pages-Adresse>` den Ordner `_site` aus der
  committeten `output/*.html` (baut die Daten nicht neu!) und veröffentlicht ihn. Von Hand: Actions →
  «Website veröffentlichen» → Run workflow. Adresse: https://konvalinaalexander-max.github.io/qgis/
  (Pages ist eingeschaltet, Quelle «GitHub Actions»).
- **Betrieb hinzufügen / ändern:** Eintrag in `config/projekt.json` → `betriebe` (key, name, sub,
  nrs, color, note, bio). Betriebsnummern exakt mit Leerzeichen übernehmen (`ZH0197/ 1/  1`).
- **Teilbetriebe:** Führt ein Betrieb mehrere Firmen/Standorte unter einer Betriebsnummer, steht das in
  den ZH-Rohdaten oft als Produktionsstätte (`ps_nr` an der Bewirtschaftungseinheit, Layer
  `produktionsstaette` mit Adresse; bei Gerber und Rathgeb gefüllt, in TG/SH nie). In `betriebe[].teile`
  je Teil: key, name, kurz, sub, `ps` (Liste ps_nr) oder `nrs` (Betriebsnummern) oder `rest: true`, bio,
  bio_text, color (Schattierung der Betriebsfarbe).
  `common.teil_of()` ordnet zu und bricht ab, wenn eine Fläche keinem Teil zugeordnet werden kann.
- **Bio-Status:** `bio` am Betrieb oder Teil: `deklariert` (Flächen als «Bioproduktion» gemeldet),
  `firma` (Bio laut Firma, in den Daten nicht gemeldet), `nein`, `offen` (nicht belegt). Je Fläche ergibt
  `common.bio_status()` «bio», «bio_betrieb» (Bio-Betrieb, Fläche nicht als Bio gemeldet: Wald,
  Gewächshäuser mit festem Fundament, oder Teil mit `firma`), «offen» oder «nein». Website (Farbmodus
  «Bio»), GeoPackage und Excel zeigen das. Achtung: In den ZH-Daten 2025 tragen Gewächshäuser mit festem
  Fundament (Codes 801–803) nie ein Programm, auch bei Bio-Betrieben (TG/SH schon). Belege und Quellen
  zu jedem Betrieb: `docs/betriebe.md`.
- **Standortpunkt:** Liegt der amtliche Betriebspunkt an einer Wohnadresse, setzt `standort_ps` am Betrieb
  den Standort im GeoPackage/QGIS auf eine Produktionsstätte (Gerber: ZH0172/ 1/ 47, Fehraltorf).
  Nach Änderungen an Betrieben: `./run_all.sh` und Schritt 5. Dateinamen mit «4_Betriebe» ggf. unter `dateinamen` anpassen.
- **Weiteren Kanton aufnehmen:** Downloads entpackt nach `data/raw/` legen (Ordnernamen
  unverändert) und für das Repo gezippt nach `data/raw_zip/`, Kanton + Version in `kantone` und Namen in `kantonsnamen` eintragen.
  Fehlende Gemeindenamen meldet `02_website.py` als Warnung (siehe unten).
- **Neuer Datenjahrgang:** neue ZIPs herunterladen (URLs in `docs/daten.md`), in
  `data/raw_zip/` ersetzen (ZIP mit dem Ordner `lwb_…_gpkg_lv95` als oberster Ebene; jede Datei
  unter 100 MB, sonst nimmt GitHub sie nicht an), `data/raw/` löschen, Version im Ordnernamen prüfen (ZH war v2_0, TG/SH v3_0) und in
  `kantone` nachführen, `stand` anpassen, alles neu bauen und Kontrollwerte neu festhalten.
- **Gemeindenamen ergänzen:** Punkt in der Gemeinde (LV95) abfragen über
  `https://api3.geo.admin.ch/rest/services/api/MapServer/identify?geometryType=esriGeometryPoint&geometry=<x>,<y>&sr=2056&layers=all:ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill&tolerance=0&returnGeometry=false&lang=de`.
  Die Antwort enthält alle Jahrgänge: den Eintrag nehmen, dessen `gde_nr` der gesuchten
  BFS-Nummer entspricht (nicht blind `is_current_jahr`, wegen Gemeindefusionen).

## Fachliche Regeln (bewusst so entschieden)

- **Sitzkanton-Prinzip:** Ein Betrieb meldet alle Flächen dem Kanton seines Sitzes, auch Flächen
  in Nachbarkantonen (Rathgeb hat z. B. Flächen in Ramsen SH und Basadingen TG im ZH-Datensatz).
  Darum wird jede Betriebsnummer nur im Datensatz ihres Kantons gesucht.
- Website, Excel und GeoPackage zeigen **Nutzungsflächen ohne überlagernde Elemente**
  (`ist_ueberlagernd = true`, z. B. Hochstammbäume, werden weggelassen).
- Die QGIS-Hervorhebung färbt **Bewirtschaftungseinheiten**. Deren Fläche kann grösser sein als
  die Summe der deklarierten Kulturen (Wege, Gebäude, nicht deklarierte Teile). Beispiel TG39621:
  10.2 ha Bewirtschaftungseinheiten gegenüber 8.2 ha Nutzungsflächen. Das ist kein Fehler.
- **Kulturgruppen:** 9 Gruppen, Regeln in `scripts/common.py → kulturgruppe()`. Reihenfolge der
  Regeln ist wichtig (z. B. «unproduktiv» vor allem anderen; 545–547 Freilandgemüse;
  800–849 Gewächshaus/geschützt; 524/525 Kartoffeln; Biodiversität über Stichworte; 601/602
  Kunstwiese; übrige 6xx Dauerwiese/Weide; übrige 5xx Ackerkulturen).
  Gemüse wird im Bundeskatalog nicht nach Art unterschieden.
- Die Betriebsnummer enthält Leerzeichen. Vergleiche in QGIS deshalb mit
  `replace("betriebsnummer", ' ', '') = replace(@betrieb, ' ', '')`.
- Die Daten enthalten **keine Personennamen und keine Eigentümer**. `betriebsname` ist in ZH die
  Adresse, in TG/SH ein Hof- oder Firmenname oder leer. Jede Zuordnung «Name ↔ Betriebsnummer»
  ist abgeleitet (siehe `docs/betriebe.md`). Eigentum gibt es nur über die offizielle
  Eigentumsauskunft des Kantons (ZH: GIS-Browser, grundstücksbezogen, SMS-Code, max. 5 Abfragen/Tag).

## Technische Eigenheiten

- Website = **eine** HTML-Datei: Leaflet, Schriften (IBM Plex, base64) und alle Flächen sind eingebettet,
  kein Server nötig. Aus dem Internet kommen nur die Hintergrundkarten und die Parzellen (keine Google Fonts).
  - Layout: Desktop = Seitenleiste links (Tabs Betriebe/Kulturen/Flächen/Info) + Karte; Details als Popup.
    Handy (≤ 760 px breit) = Karte bildschirmfüllend + ziehbares Panel unten (Stufen peek/half/full,
    Details im Panel, `Sheet` im JS). Kleine Fenster/Handy quer (≤ 540 px hoch): Seitenleiste schmal,
    Details in der Seitenleiste statt Popup. Eingabefelder auf Touch-Geräten 16 px (sonst zoomt iOS).
  - Link zu einer Fläche: `#flaeche=<Breite>,<Länge>` (WGS84-Bezugspunkt `la`/`lo` je Fläche, liegt sicher
    in der Fläche). Beim Öffnen: exakter Punkt, sonst Fläche, die den Punkt enthält, sonst nächster Punkt
    < 50 m. Auswahl schreibt den Hash per `history.pushState`, damit die Zurück-Taste die Details schliesst.
  - Teilbetriebe: Farbe des Teils (Schattierung), eigene Legenden-Schaltfläche je Teil, aufklappbar in der
    Betriebskarte (eigene Schalter + Zoom), Tabelle «Teilbetriebe» im Tab Kulturen; Daten-Feld `t` (Teil-ID).
  - Farbmodus «Bio» (Daten-Feld `bs`): Bio gemeldet / Bio-Betrieb, nicht als Bio gemeldet / nicht Bio /
    Bio-Status unklar (nur vorkommende Stufen); die Legenden-Schaltflächen filtern. Vergleichstabelle mit Zeilen «davon nach Bio-Status».
  - Wem gehört die Fläche: Details beginnen mit einem Band in Betriebsfarbe (Name, Teilbetrieb, Ort,
    Betriebsnummer, Bio-Kennzeichen).
    Bei einer Auswahl treten die Flächen der übrigen Betriebe zurück (`focus` im JS), die gewählte Fläche
    hat einen Rand in Betriebsfarbe; im Panel steht der Name zusätzlich als Schild auf der Fläche, und
    Kopf/Tabs sind ausgeblendet (Klasse `detail` an `#side`). Mit Maus: Betrieb schon beim Darüberfahren.
  - Standort-Knopf (`map.locate`, braucht https oder localhost), Route-Link (Apple Maps auf Apple-Geräten,
    sonst Google Maps), Teilen (Web Share API, sonst Zwischenablage; nur online sichtbar).
  - «Kultur»-Modus: Legenden-Schaltflächen filtern Kulturgruppen (gilt nur in diesem Modus); weit
    herausgezoomt Rand in Kulturfarbe, nah (ab Zoom 13) in Betriebsfarbe; Linien in der Übersicht dicker.
  - Platzhalter in `web/template.html`: `__TITEL__`, `__BESCHREIBUNG__`, `__ICON__`, `/*__FONTS__*/`,
    `/*__DATA__*/`, `<!--__ROBOTS__-->` (02_website.py) und `<!--__ONLINE__-->` (06_online.py: Manifest,
    apple-touch-icon, og:url/og:image).
  - Online: GitHub Pages, öffentlich für alle mit Link; `noindex`, solange `online.suchmaschinen` in
    `config/projekt.json` false ist.
  - swisstopo XYZ (EPSG:3857): Luftbild `ch.swisstopo.swissimage` bis Zoom 20; Landeskarte
    `ch.swisstopo.pixelkarte-farbe` / `-grau` nur bis Zoom 19 (z20 liefert HTTP 400) → in Leaflet
    `maxNativeZoom: 19`.
  - Parzellen ZH: WMS `https://wms.zh.ch/avwms`, Layer `Liegenschaften,OSNR_liegenschaften`,
    zeichnet erst ab Zoom 17 → `minZoom: 17`.
- Flächen für die Website werden mit 0.3 m vereinfacht und auf 6 Nachkommastellen gerundet
  (ca. 1.0 MB HTML inkl. Schriften; online mit gzip ausgeliefert).
- Excel rechnet in der Übersicht mit SUMIFS/COUNTIF auf dem Blatt «Flächen» (Spalte M = Teilbetrieb,
  N = Bio-Status). `04_excel.py` schreibt die in Python berechneten Ergebnisse zusätzlich als
  zwischengespeicherte Werte in die Formelzellen, damit Quick Look und Browser-Vorschauen Zahlen zeigen;
  Excel/Numbers rechnen beim Öffnen ohnehin neu.
- QGIS-Projekt: Pfade relativ zu `output/` (`../data/raw/…`, `./Feldkarte_Auswahl_4_Betriebe.gpkg`).
  Der ganze Projektordner kann deshalb verschoben werden. Projektvariable `betrieb` ändern unter
  *Projekt → Eigenschaften… → Variablen*.
- Die Kantonsdaten sind in LV95 (EPSG:2056); das QGIS-Projekt ebenfalls.

## Stand (6.10.2026)

Erledigt:
- Website für Handy optimiert (Panel unten, Tabs, Details, Standort, Route, Teilen-Link, Zurück-Taste),
  Schriften eingebettet, Online-Fassung + GitHub-Pages-Workflow vorbereitet; getestet mit Playwright
  (Desktop 1440/1280, iPhone 390/375, Android 360, iPad 768, Handy quer 844×390, Dunkelmodus).
  Online seit 5.10.2026: https://konvalinaalexander-max.github.io/qgis/ (Pages-Quelle «GitHub Actions»).
- Details zeigen zuoberst den Betrieb (Band in Betriebsfarbe), übrige Betriebe treten bei Auswahl zurück.
- 4 Betriebe identifiziert, Daten ZH (Sitz aller 4) plus TG/SH geprüft. In TG kam die
  BioFresh AG (TG39621, Tägerwilen, Gewächshäuser, Bio) zu Rathgeb dazu, in SH nichts.
- Website, Excel, GeoPackage und QGIS-Projekt mit ZH + TG + SH gebaut und geprüft.
- Faktencheck aller Betriebe (6.10.2026, Handelsregister, Firmenwebsites, Zertifikate, Presse; Ergebnisse
  und Quellen in `docs/betriebe.md`). Daraus: Teilbetriebe Imhof (2 Nummern), Gerber (Bio Greens AG /
  Gemüsebau AG nach Produktionsstätte), Rathgeb (Unterstammheim / Ellikon / BioFresh); Bio-Status je Teil,
  Farbmodus «Bio». Die Wohnadresse aus `betriebsname` von Gerber wird weder angezeigt noch als
  Standortpunkt verwendet (`standort_ps`).
- Zwei PDF-Anleitungen (Windows, Mac) für QGIS mit Online-Daten (Stand 28.09.2026), Quellen in
  `anleitungen/`. Die PDFs selbst liegen in `~/Downloads`.

Offen / Ideen (nur auf Wunsch angehen):
- ZH0218/ 1/  3 (Alte Horgenbachstr. 2, Ellikon): kein Beleg für eine Zugehörigkeit zu Rathgeb, nicht
  aufgenommen.
- Imhof ZH0197/ 1/702: Betreiber (Imhof Flora AG oder Imhofbio AG) und Bio-Status offen.
- Gerber Bio Greens: Bio laut Firma, aber keine Fläche als Bioproduktion gemeldet; wahrscheinliche
  Erklärung (Bio-Verordnung Art. 7 Abs. 5) in `docs/betriebe.md`, von Gerber nicht bestätigt.
- Die PDF-Anleitungen beschreiben den Online-Weg. Eine Fassung für dieses lokale Projekt
  (Rohdaten, QGIS-Projekt, @betrieb) gibt es noch nicht.
