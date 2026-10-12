# Karte der Region – alle Betriebe im Gebiet

Startseite der Website (seit 12.10.2026): alle landwirtschaftlichen Flächen im Gebiet. Ein Klick auf eine Fläche
hebt alle Flächen desselben Betriebs hervor (auch ausserhalb des Gebiets und in anderen Kantonen) und zeigt Hof,
Flächen, Kulturen und Gemeinden. Die vier Favoriten (Imhof, Beerstecher, Gerber, Rathgeb) stehen in der Liste zuoberst;
Imhof ist grün. Die bisherige Detailansicht der Favoriten bleibt als `betriebe.html` erreichbar.

## Gebiet

Konvexe Hülle aller Flächen der Favoriten (`config/projekt.json` → `betriebe`) plus `region.puffer_km` (20 km), nur
Schweiz (swissBOUNDARIES3D). Ergebnis 2025: rund 4'350 km², etwa Spreitenbach–Amriswil und Pfäffikon SZ–Thayngen.

Ein Betrieb gehört dazu, wenn eine seiner Nutzungsflächen das Gebiet berührt. Weil jeder Betrieb alle Flächen
seinem Sitzkanton meldet, werden die Daten **aller** Kantone durchsucht, die geodienste.ch frei abgibt. So erscheinen
auch Betriebe aus AG, LU, BE usw., die im Gebiet Felder haben. Nicht frei erhältlich (Registrierung/Freigabe) und
deshalb nicht enthalten: Nutzungsflächen NE, TI, NW, OW, VD.

Kontrollwerte (Bezugsjahr 2025, GL und GR nur 2026 erhältlich):

| | Wert |
|---|---|
| Betriebe mit Flächen im Gebiet | 10'685 aus 18 Kantonen |
| Flächen im Gebiet | 300'503 (212'916 ha) |
| alle Flächen dieser Betriebe | 316'283 (deckungsgleiche Doppelflächen AG nur einmal) |
| Betriebe nach Sitzkanton | ZH 3'011, TG 2'832, SG 2'278, AG 825, SZ 602, SH 601, ZG 311, AR 186, übrige 39 (LU 9, AI 8, GL 8, BE 4, BL 3, FR 2, SO 2, GR 1, JU 1, UR 1) |

## Ablauf (`./run_region.sh`)

| Schritt | Skript | liest | schreibt |
|---|---|---|---|
| 11 | `11_kantone.py` | geodienste.ch, data.geo.admin.ch | `data/kantone/<KT>/`, `data/basis/` (nicht im Git, ca. 3.5 GB) |
| 12 | `12_region.py` | `work/auswahl.gpkg`, Kantonsdaten | `work/region.gpkg` (Gebiet, Flächen, Betriebspunkte, Produktionsstätten) |
| 13 | `13_betriebe.py` | `work/region.gpkg`, Gemeindegrenzen, Gebäudeadressen | `work/betriebe.gpkg`, `work/betriebe.csv` |
| 14 | `14_namen.py` | Handelsregister (LINDAS), OpenStreetMap | `data/intern/namen.csv` (vertraulich) |
| 15 | `15_adr.py` | `data/intern/adr/*.xls(x)` (vertraulich), PLZ-Gebiete | `work/adr.gpkg`, `work/adr_anteile.csv` |
| 16 | `16_karte.py` | alles oben, `web/karte/`, `web/vendor/` | `output/karte/` |
| 6 | `06_online.py` | `output/karte/`, `output/*.html` | `work/online/` bzw. `_site/` (Startseite = Karte, `betriebe.html` = Favoriten) |

Lokal ansehen: `python3 scripts/server.py` → http://localhost:8000 (nur dieser Computer; `--netz` auch für andere
Geräte im Netz, z. B. das Handy im WLAN). Die Vektorkacheln (PMTiles) brauchen einen Webserver mit Range-Anfragen;
`python3 -m http.server` kann das nicht.

## Hof und Adresse

- Hof = amtlicher Betriebsstandort (Layer `betrieb` der Kantonsdaten).
- Adresse: der `betriebsname` der Kantonsdaten, wenn er eine Adresse ist (ZH immer, AG/SG/AR/AI meist im Format
  «Strasse Nr, PLZ Ort»). Enthält der Text vor der PLZ Personenangaben, wird er nicht übernommen (`common.hat_person`:
  c/o, z. Hd., Familie, Fam., Herr, Frau, Dr., Initiale + Name, Vorname aus der Schweizer Vornamenliste des Pakets
  gender-guesser, auch die für beide Geschlechter, ausser Flurwörtern wie «Linde», «Moos», «Alp»; Stand 2025:
  46 Einträge). Dann und in TG/SH/SZ/ZG u. a. gilt die nächste amtliche Gebäudeadresse am Standort (swisstopo,
  höchstens 60 m entfernt, sonst keine Adresse; Abstand in `adresse_dist_m`). Stand 2025: 5'882 Adressen aus den
  Kantonsdaten, 4'767 nächste Gebäudeadresse, 36 ohne Adresse.
  Amtliche Strassennamen nach Personen («Hans-…-Strasse») sind keine Personenangaben und bleiben.
- `bezeichnung`: der `betriebsname`, wenn er weder Adresse noch Personenangabe ist (Hof-, Flur- oder Firmenname, v. a. TG/SH).
- Produktionsstätten: öffentlich nur Nummer und Adresse (Text mit PLZ, ohne Personenangaben und ohne Firmennamen mit
  Rechtsform vor der PLZ). Bezeichnungen ohne PLZ (TG, ZG, SZ u. a., z. B. «Pouletstall <Name>») enthalten oft Namen
  und stehen nur im verschlüsselten Teil. Dasselbe gilt für `betriebsname`: «Muster AG, 8000 Ort» wird nicht als
  Adresse übernommen.
- Favoriten mit `standort_ps` (Gerber): Standort, Adresse und Gemeinde der Produktionsstätte statt der Wohnadresse
  (schon in `13_betriebe.py`).
- Ungültige Standorte (ausserhalb der Schweiz, z. B. ein Ersatzpunkt in Frankreich, oder mehr als 50 km von allen
  eigenen Flächen): Ersatz durch die amtlich verortete Adresse aus `betriebsname` («Adresse (amtlich verortet)», 19
  Betriebe), sonst einen Punkt in der grössten eigenen Fläche («grösste eigene Fläche (Standort fehlt)», 6 Betriebe;
  ohne Route-Knopf). Die Karte zeichnet diese Höfe gestrichelt und nennt die Herkunft (`standort_quelle`, in
  `betriebe.json` als `sq`).
- Liegt der Standort mehr als 3 km von den eigenen Flächen entfernt (rund 105 Betriebe), zeigt die Karte einen Hinweis.
- AG meldet bei einigen Flächen zusätzlich Code 595 auf genau derselben Geometrie wie die Hauptkultur, ohne sie als
  überlagernd zu kennzeichnen; solche deckungsgleichen Doppelflächen zählen nur einmal (`12_region.py`).

## Namen (vertraulich, nur verschlüsselt auf der Website)

Die Kantonsdaten enthalten keine Namen. `14_namen.py` ordnet Namen über Adresse und Lage zu, jeweils mit Quelle,
Abstand zum Betriebspunkt und Sicherheit (`wahrscheinlich`: gleiche Adresse bzw. allein am Punkt; `unsicher`:
mehrere Betriebe am selben Punkt oder weiter weg; `amtlich`: Kantonsdaten; `geprüft`: Favoriten).

Standard (ohne `--personen`): keine Namen natürlicher Personen als solche:
- Firmen mit eigener Rechtspersönlichkeit (AG, GmbH, Genossenschaft, Verein, Stiftung) aus dem Handelsregister
  (offene Daten des Bundes über LINDAS), deren Name oder Zweck landwirtschaftlich ist, an der Hofadresse (≤ 60 m);
  Firmennamen können Familiennamen enthalten;
- Hofnamen aus OpenStreetMap (`place=farm` u. ä., ≤ 150 m) und die Bezeichnung in den Kantonsdaten – ohne Einträge
  mit Personenangaben (dieselbe Prüfung wie bei der Adresse, also auch «Vorname Name»); Hofnamen wie «Hof Muster»
  enthalten trotzdem oft einen Familiennamen.
Alle Namen stehen nur im verschlüsselten Teil, nie in den öffentlichen Dateien (auch die Bezeichnung der Kantonsdaten nicht).

Mit `--personen` zusätzlich Einzelunternehmen und Kollektivgesellschaften aus dem Handelsregister, die Hofsuche des
Schweizer Bauernverbands (freiwilliger Eintrag: Hofname, Betriebsleitung), die Betreiber von Hofläden (OSM) und
Bezeichnungen der Kantonsdaten mit Personenangaben. Ein späterer Lauf mit `--personen` lädt die im Standardlauf
gekürzten Abzüge automatisch neu.
Das sind Personendaten; nur auf ausdrücklichen Wunsch verwenden (Stand 12.10.2026: noch nicht freigegeben).
Ebenso Ergebnisse einer Web-Recherche (`data/intern/namen_recherche.csv`). Ohne `--personen` bewahrt das Skript auch
keine Personendaten auf: der Handelsregister-Abzug wird auf juristische Personen gekürzt, Betreiberangaben in den
OSM-Daten werden entfernt, eine alte Hofsuche-Datei wird gelöscht.

Bewusst nicht verwendet:
- UID-Register als Massenabfrage: Das Gesetz beschränkt öffentliche Abfragen auf einzelne Unternehmen
  (UIDG Art. 11), Sammelabfragen mit Merkmalen sind nicht vorgesehen.
- Private Telefonbucheinträge, Angaben zu Familienmitgliedern.
- Eigentümer: nur über die Eigentumsauskunft des Kantons (grundstücksbezogen).

## Interne Regionen (vertraulich)

Regionsdefinitionen als Excel-Dateien (eine Datei je Region, je Zeile PLZ und Ort) in `data/intern/adr/`, nicht im Git.
`15_adr.py` bildet jede Zeile auf die amtlichen PLZ-Gebiete ab und berechnet je Betrieb den Anteil der Fläche pro
Region (Lage des Flächenpunkts, jede Fläche je Region einmal). Regionen können sich überschneiden, die Summe kann
dann über 100 % liegen. Flächen im Ausland liegen in keiner Region. Regeln im Kopf von `15_adr.py`. Auf der Website
erscheinen der Schalter «Regionen (intern)» (Tab Karte) und die Tabelle in den Details erst nach dem Entsperren.

## Verschlüsselung

Repo und Website sind öffentlich. Vertrauliches liegt unverschlüsselt nur in `data/intern/` (nicht im Git).
`16_karte.py` schreibt mit gesetztem `FELDKARTE_PASSWORT` (mindestens 16 Zeichen, z. B. vier zufällige Wörter) die
Datei `output/karte/intern.bin`: Namen + Regionen, gzip, AES-256-GCM, Schlüssel per PBKDF2-SHA256 mit 600'000 Runden
(Zahl im Dateikopf). Wer intern.bin herunterlädt, kann das Passwort offline durchprobieren – darum ein langes,
zufälliges Passwort wählen und es nur intern weitergeben; ein neues Passwort schützt ältere intern.bin in der
Git-Historie nicht. Die Website entschlüsselt im Browser (WebCrypto) nach Eingabe des Passworts (Tab Info). Den
Schlüssel hält sie standardmässig nur für die laufende Sitzung; mit «Auf diesem Gerät 30 Tage merken» auch länger
(«Sperren» löscht ihn). Ohne Passwort wird die Karte ohne Namen und ohne Regionen gebaut.

`python3 scripts/intern.py sichern|entpacken` legt bzw. holt eine verschlüsselte Sicherung von `data/intern/`
(`data/intern.enc`, ebenfalls nicht im Git – privat aufbewahren, nicht ins öffentliche Repo).

## Website (technisch)

- MapLibre GL JS 4.7.1 + PMTiles 3.2.1 (in `web/vendor/`), Schriften IBM Plex lokal. Keine Daten von Dritten ausser den
  Hintergrundkarten (swisstopo) und den Parzellen ZH (WMS, ab Zoom 17).
- Zwei Kachelsätze: `grob-<Kennung>.pmtiles` (Zoom 10–11, Flächen ab 0.3 ha, vereinfacht) und
  `flaechen-<Kennung>.pmtiles` (Zoom 12–14, alle Flächen mit Nutzung, Fläche, Gemeinde, Bio). Darunter (Zoom < 10)
  keine Flächen. Die Kennung ist ein Fingerabdruck des Inhalts (Attribute, Geometrien, Reihenfolge der Betriebe,
  Gemeinden, Kulturgruppen) und steht auch in `index.html` und `betriebe.json`: Nach einem Update findet eine noch
  offene alte Seite ihre Kacheln nicht mehr und bietet «Neu laden» an, statt Flächen falschen Betrieben zuzuordnen.
  `16_karte.py --schnell` schreibt die Kacheln nur neu, wenn sich die Kennung geändert hat.
- `betriebe.json`: ein Eintrag je Betrieb (Betriebsnummer, Adresse ohne Personenangaben mit Quelle `aq` und Abstand
  `ad`, Gemeinde, Kennzahlen, alle Gemeinden der Flächen, Ausdehnung `bbox` und – wenn anders – `bbox_gebiet` der
  Flächen im Gebiet; keine Namen). `meta.intern` sagt, ob es `intern.bin` gibt; ohne fragt die Seite nicht danach und
  zeigt keine Passwort-Hinweise. Link auf einen Betrieb: `#b=<Betriebsnummer>`, auf einen Favoriten `#b=imhof`.
  Links der früheren Startseite (`#flaeche=…`) leitet die Karte an `betriebe.html` weiter.
- Passt ein Betrieb bei Zoom 10 nicht ins Bild, zeigt die Karte die Flächen ohne Hof, sonst die Flächen im Gebiet
  (mit Hinweis). Details: die 4 grössten Gemeinden, die übrigen aufklappbar.
- Suche: Treffer am Wortanfang vor Treffern mitten im Wort (Ellikon vor Bellikon); Enter öffnet den ersten Treffer;
  die Listen sind mit der Tastatur bedienbar. Direktlinks legen einen Verlaufseintrag ohne Auswahl an (Zurück schliesst
  die Details).
- Version `?v=` = Kachel-Kennung + Prüfsumme von app.js, app.css und betriebe.json: Ein reines Datenupdate bekommt so
  neue Adressen. GitHub Pages liefert index.html mit `max-age=600`, ein neu geöffneter Tab kann also bis 10 Minuten den
  alten Stand zeigen.
- Link-Vorschau: `web/online/vorschau.jpg` zeigt die Karte der Region (neu erzeugen: `scripts/screenshots.py --vorschau`).
- Handy: Karte bildschirmfüllend, Panel unten (ziehen: klein / halb / voll).
