# Daten

## Quelle

geodienste.ch, Geodatenmodell «Landwirtschaftliche Kulturflächen» (MGDM Nr. 153).
Öffentlich zugänglich (Zugangsberechtigungsstufe A) sind u. a.:

- **Nutzungsflächen** (153.1): eine Fläche pro deklarierter Kultur, mit LNF-Code, Nutzung,
  Programmen (z. B. Bioproduktion), Beitragsberechtigung, Fläche.
- **Bewirtschaftungseinheiten** (153.6): die Einheiten eines Betriebs, mit Betriebsnummer,
  Gemeinde (BFS-Nr.) und Fläche; dazu die Layer `betrieb` (Standortpunkt) und `produktionsstaette`.

Stand der Daten im Projekt: Bezugsjahr 2025, publiziert Januar 2026.

## Direkte Downloads (GeoPackage, LV95)

Muster: `https://www.geodienste.ch/downloads/geopackage/<thema>/<KT>/deu/<thema>_<version>_<KT>_gpkg_lv95.zip`

| Kanton | Version | Nutzungsflächen | Bewirtschaftungseinheiten |
|---|---|---|---|
| ZH | v2_0 | `…/lwb_nutzungsflaechen/ZH/deu/lwb_nutzungsflaechen_v2_0_ZH_gpkg_lv95.zip` | `…/lwb_bewirtschaftungseinheit/ZH/deu/lwb_bewirtschaftungseinheit_v2_0_ZH_gpkg_lv95.zip` |
| TG | v3_0 | `…/lwb_nutzungsflaechen/TG/deu/lwb_nutzungsflaechen_v3_0_TG_gpkg_lv95.zip` | `…/lwb_bewirtschaftungseinheit/TG/deu/lwb_bewirtschaftungseinheit_v3_0_TG_gpkg_lv95.zip` |
| SH | v3_0 | `…/lwb_nutzungsflaechen/SH/deu/lwb_nutzungsflaechen_v3_0_SH_gpkg_lv95.zip` | `…/lwb_bewirtschaftungseinheit/SH/deu/lwb_bewirtschaftungseinheit_v3_0_SH_gpkg_lv95.zip` |

Die Version kann sich mit einem neuen Jahrgang ändern. Wenn ein Link nicht mehr geht, auf
geodienste.ch beim Thema «Landwirtschaftliche Kulturflächen» den aktuellen Download suchen.
Die ZIPs entpackt (Ordnername unverändert) nach `data/raw/` legen.

Grösse im Projekt: ZH ca. 220 MB, TG ca. 85 MB, SH ca. 27 MB.

## Inhalt der GeoPackages

`lwb_bewirtschaftungseinheit_*.gpkg`
- `betrieb` (Punkt): betriebsnummer, betriebsname, bur_nr, kanton
- `bewirtschaftungseinheit` (Fläche): betriebsnummer, identifikator_be, gemeinde (BFS-Nr.),
  flaeche_m2, ist_definitiv, zone_ausland …
- `produktionsstaette` (Punkt)

`lwb_nutzungsflaechen_*.gpkg`
- `nutzungsflaechen` (Fläche): lnf_code, nutzung, programm (mehrere mit «;» getrennt),
  code_programm, beitragsberechtigt, bewirtschaftungsgrad, ist_ueberlagernd,
  identifikator_be (Verknüpfung zur Bewirtschaftungseinheit), flaeche_m2, bezugsjahr …

Verknüpfung: Nutzungsfläche → `identifikator_be` → Bewirtschaftungseinheit → `betriebsnummer`.

Anzahl Objekte (Bezugsjahr 2025):

| Kanton | Betriebe | Bewirtschaftungseinheiten | Nutzungsflächen |
|---|---|---|---|
| ZH | 8'367 | 72'395 | 138'637 |
| TG | 6'618 | 26'863 | 71'971 |
| SH | 1'490 | 12'108 | 25'406 |

## Besonderheiten

- **Sitzkanton-Prinzip:** Alle Flächen eines Betriebs stehen im Datensatz des Kantons, in dem der
  Betrieb seinen Sitz hat, auch Flächen in anderen Kantonen.
- `betriebsname`: in ZH die Adresse (z. B. «Eichhof, 8603 Schwerzenbach»), in TG/SH ein Hof- oder
  Firmenname oder leer. Personennamen kommen nicht vor.
- Betriebsnummern ZH haben das Format `ZH0197/ 1/  1` (mit Leerzeichen), TG z. B. `TG39621`.
- Gemeinde-Codes: neben echten BFS-Nummern kommen `2981` (SH-Datensatz) und `9998`
  (TG-Datensatz) vor; beide liegen in Büsingen am Hochrhein (DE). `3393` (1 Einheit im
  TG-Datensatz) liess sich keiner Gemeinde eindeutig zuordnen.
- Eigentümer sind nicht enthalten.

## Weitere Dienste (online)

- swisstopo Kacheln (EPSG:3857):
  `https://wmts.geo.admin.ch/1.0.0/<layer>/default/current/3857/{z}/{x}/{y}.jpeg`
  mit `ch.swisstopo.swissimage` (bis z20), `ch.swisstopo.pixelkarte-farbe` / `-grau` (bis z19).
- WMS Bund: `https://wms.geo.admin.ch/` (u. a. `ch.blw.landwirtschaftliche-nutzungsflaechen`,
  `ch.blw.bodeneignung-*`, `ch.blw.landwirtschaftliche-zonengrenzen`).
- WMS Kanton Zürich, amtliche Vermessung: `https://wms.zh.ch/avwms`, Layer `Liegenschaften`,
  `OSNR_liegenschaften` (zeichnet erst bei starkem Hineinzoomen, ab Zoom 17).
- Gemeindegrenzen/-namen: `api3.geo.admin.ch` identify, Layer
  `ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill` (siehe CLAUDE.md).
