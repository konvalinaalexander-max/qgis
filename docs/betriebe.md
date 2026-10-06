# Betriebe und Betriebsnummern

Die Geodaten enthalten keine Personennamen. Die Zuordnung «Betriebsname ↔ Betriebsnummer» ist
deshalb abgeleitet: über die Adresse im Feld `betriebsname` (ZH), die Adressen der Produktionsstätten,
die Lage der Flächen (Gemeinden) und Plausibilität (Anteil Gemüse, Bio-Deklaration). Sie ist nicht
amtlich bestätigt. Geprüft im Oktober 2026 mit Handelsregister (Zefix/SHAB), Firmenwebsites,
Bio-Zertifikaten und Fachpresse (Quellen unten).

| Betrieb | Betriebsnummer | `betriebsname` in den Daten | Grundlage der Zuordnung |
|---|---|---|---|
| Imhof | ZH0197/ 1/  1 | Eichhof, 8603 Schwerzenbach | Adresse = Sitz der Imhofbio AG und der Imhof Flora AG |
| Imhof | ZH0197/ 1/702 | Eichhof, 8603 Schwerzenbach | gleiche Adresse; 1 Fläche, 1.0 ha Gewächshaus |
| Beerstecher | ZH0191/ 1/ 55 | Hochbordstrasse 15, 8600 Dübendorf | Adresse = Sitz der Beerstecher AG |
| Gerber | ZH0172/ 1/700 | Wohnadresse in Pfäffikon ZH (kein Firmensitz; hier bewusst ohne Strasse) | Produktionsstätten Fehraltorf und Felben-Wellhausen = Adressen der beiden Gerber-Firmen |
| Rathgeb | ZH0042/ 1/850 | Rohräcker 414, 8476 Unterstammheim | Adresse |
| Rathgeb | TG39621 | BioFresh AG | Gewächshäuser in Tägerwilen; Firma der Rathgeb-Gruppe |

## Teilbetriebe

Eine Betriebsnummer kann mehrere **Produktionsstätten** umfassen (Landwirtschaftliche
Begriffsverordnung, Art. 2 Abs. 2: Führt ein Bewirtschafter mehrere Produktionsstätten, gelten sie
zusammen als ein Betrieb). In den Zürcher Daten 2025 tragen die Bewirtschaftungseinheiten vieler solcher
Betriebe eine Produktionsstätte (`ps_nr`, Layer `produktionsstaette` mit Adresse), so bei Gerber und
Rathgeb; in TG und SH ist `ps_nr` nie gefüllt. Danach sind Gerber und Rathgeb aufgeteilt; bei Imhof und
bei der BioFresh AG (TG) trennt die Betriebsnummer.

| Teilbetrieb | Zuordnung | Flächen | ha | Bio |
|---|---|---|---|---|
| Imhofbio, Eichhof Schwerzenbach | ZH0197/ 1/  1 | 245 | 90.61 | 84.70 ha als Bioproduktion gemeldet |
| Gewächshaus Eichhof | ZH0197/ 1/702 | 1 | 1.02 | unklar |
| Gerber Bio Greens AG | PS ZH0172/ 1/ 47, Zürcherstrasse 75, Fehraltorf | 161 | 106.07 | Bio laut Firma, nicht gemeldet |
| Gerber Gemüsebau AG | PS ZH4561/ 1/  4, Rosenackerstr. 7, Felben-Wellhausen | 71 | 147.08 | nicht Bio |
| Rathgeb Bio, Unterstammheim | PS ZH0042/ 1/ 48 | 227 | 288.86 | Bio gemeldet |
| Rathgeb Bio, Ellikon an der Thur | PS ZH0218/ 1/ 30, Neue Horgenbachstrasse, + ZH0218/ 1/ 36 | 202 | 253.26 | Bio gemeldet |
| BioFresh AG, Tägerwilen | TG39621 | 12 | 8.18 | Bio gemeldet |

## Befunde je Betrieb (Faktencheck Oktober 2026)

### Imhof (Eichhof, Schwerzenbach)
- Auf dem Eichhof sind drei Einheiten tätig: Imhofbio AG (Handelsregister seit 2010, Zweck Produktion und
  Handel mit Bioprodukten), «Hansjürg Imhof Bio-Produkte» (Bio-Zertifikat auf die Person, nicht im
  Handelsregister) und die Imhof Flora AG (seit 2014, Beet- und Balkonpflanzen im Gewächshaus).
- Bio: Knospe seit 1997, Gemüse seit 2017 nach Demeter; Zertifikate gültig bis Ende 2027. In den Daten
  84.7 ha als Bioproduktion gemeldet. Die nicht gemeldeten 5.9 ha der Hauptnummer sind Wald,
  Ruderalflächen, nicht beitragsberechtigte Flächen und Gewächshäuser mit festem Fundament.
- **ZH0197/ 1/702** (1 Fläche, 1.02 ha, Code 802 «Übrige Spezialkulturen in Gewächshäusern mit festem
  Fundament»): Betreiber nicht belegt. Möglich sind die Imhof Flora AG (Blumen, Swiss GAP, nicht Bio)
  oder ein Kräuter-Gewächshaus der Imhofbio AG (Bio). Das fehlende Programm sagt nichts: In den Zürcher
  Daten 2025 tragen alle Gewächshäuser mit festem Fundament (Codes 801–803) «Kein Programm», auch bei
  Bio-Betrieben. Auf der Karte darum «Bio-Status unklar».
- **Thalheim an der Thur** (12.1 ha mit Gewächshäusern beim Weiler Weidler, Gütighausen): keine Quelle
  verbindet Imhof mit diesem Standort. Vermutung: Pacht oder Übernahme eines früheren Gemüsebetriebs.
- Flächenangaben der Presse (2018: 68 ha LN; «70 ha Gemüse») sind älter als die Daten 2025 (91.6 ha).
  Die grossen Glashäuser (Kräuter rund 4 ha, Anlage Altwiesen in Wangen) sind in den Daten nur teilweise
  enthalten (2.9 ha Gewächshaus/geschützt) – vermutlich, weil sie nicht als landwirtschaftliche
  Nutzfläche deklariert sind.

### Beerstecher (Dübendorf)
- Beerstecher AG, Hochbordstrasse 15, Dübendorf (Handelsregister seit 2003).
- **Nicht Bio:** «Auf eine Bio-Zertifizierung hat die Beerstecher AG bisher verzichtet» (Schweizer
  Bauer, 8.1.2023). Produktionsart ÖLN, Swiss GAP, Migros «Aus der Region». In den Daten 0 ha Bio.
- Fläche laut Presse 130 ha (2023) bzw. 150 ha Freiland + 5 ha Gewächshaus (2024); Daten 2025: 132.7 ha.
  Gewächshaus Hinwil (Abwärme KEZO, rund 3.4 ha) passt zu 3.9 ha in Hinwil.
- Verwechslungsgefahr: Der Biohof Hermikon (Hermikonstrasse 113, Dübendorf) ist ein eigener
  Knospe-Betrieb, nicht Beerstecher.
- Am Firmensitz Hochbord ist eine Überbauung geplant (Gestaltungsplan 2023); diese Flächen dürften in
  späteren Jahrgängen fehlen.

### Gerber (Fehraltorf, Felben-Wellhausen)
- Zwei Aktiengesellschaften: **Gerber Bio Greens AG** (Sitz Fehraltorf, Domizil Rütihof bzw.
  Zürcherstrasse 75; Zweck Produktion von und Handel mit biologischen Produkten) und **Gerber Gemüsebau
  AG** (Sitz Felben-Wellhausen, Rosenackerstrasse 9; bis 2021 «Gerber Logistik AG» in Fehraltorf;
  2021 Sacheinlage des «Betriebsteils B, Betriebsstätte Felben-Wellhausen»). Laut Presse gehört beides
  demselben Inhaber.
- Die beiden Produktionsstätten der Betriebsnummer ZH0172/ 1/700 liegen an den Adressen der beiden
  Firmen: Zürcherstrasse 75, Fehraltorf (Bio Greens) und Rosenackerstr. 7, Felben-Wellhausen (Firmensitz
  der Gemüsebau AG: Rosenackerstrasse 9, Nachbaradresse). Die Zuordnung «Produktionsstätte = Firma» ist
  daraus abgeleitet.
- Der amtliche Betriebspunkt von ZH0172/ 1/700 liegt an der Wohnadresse in Pfäffikon ZH. Im GeoPackage
  und im QGIS-Projekt steht der Gerber-Standort deshalb auf der Produktionsstätte Fehraltorf
  (`standort_ps` in `config/projekt.json`).
- **Bio Greens:** Bio-Suisse-Richtlinien laut Firma, Zertifikate Bio Suisse und bio.inspecta auf der
  Website. Bio seit 1996 (Bioaktuell 2023, «Knospe-Betrieb seit 1996») bzw. 1999 (BauernZeitung 2024,
  ganzer Betrieb Fehraltorf umgestellt). Fläche laut Presse «rund 80 ha» (Ackerfläche bzw. Nutzfläche,
  2023/24). Daten 2025: 106.1 ha, davon 57.5 ha Freilandgemüse, 3.4 ha Gewächshaus/geschützt,
  19.7 ha Kunstwiese, 8.9 ha Weizen, 14.8 ha Biodiversitätsflächen; Ackerfläche rund 87 ha.
  Gemeinden: Fehraltorf 63.0, Flaach 22.4, Volketswil 6.4, Wildberg 5.9, Gossau 5.3, Mönchaltorf 3.1.
- **Gemüsebau AG:** konventionell nach Suisse Garantie (Website; Zertifikate Suisse Garantie, SwissGAP,
  kein Bio). Daten 2025: 147.1 ha, davon 128.2 ha im Thurgau (Wigoltingen 60.4, Felben-Wellhausen 31.2,
  Hüttlingen 26.9, Frauenfeld 9.7) und 18.9 ha in Zürich (Altikon 9.0, Andelfingen 3.8, Elgg 3.0,
  Elsau 1.7 – Gewächshäuser Schnasberg –, Dinhard 1.3).
- **Nach Kanton** sind es 125.0 ha ZH und 128.2 ha TG. Die Kantonsgrenze trennt die Firmen also nicht
  genau; die Produktionsstätte schon.
- **Keine Fläche als Bioproduktion gemeldet.** Erklärung (nicht von Gerber bestätigt): Der Bio-Beitrag
  ist ein Beitrag für gesamtbetriebliche Produktionsformen (Direktzahlungsverordnung Art. 65), und ein
  Biobetrieb muss als Ganzes biologisch bewirtschaftet werden (Bio-Verordnung Art. 6). Die
  Zertifizierungsstelle kann aber eine einzelne Produktionsstätte eines nicht biologischen Betriebs als
  selbstständigen Biobetrieb anerkennen (Bio-Verordnung Art. 7 Abs. 5; Bio Suisse: bestehende
  Anerkennungen gelten bis 31.12.2037). So kann Bio Greens zertifiziert sein, ohne dass die
  Betriebsnummer Bio meldet.
- Datenfehler: Der Punkt der Produktionsstätte ZH4561/ 1/  4 (Felben-Wellhausen) liegt in den Rohdaten
  in Fehraltorf. Die Karte zeigt keine Produktionsstätten-Punkte.
- In der ZH-Tabelle `betrieb` gibt es zwei leere Nummern an der Adresse Zürcherstrasse 75, Fehraltorf:
  ZH0172/ 1/600 und ZH0172/ 1/602 (ohne Flächen).

### Rathgeb (Unterstammheim, Ellikon an der Thur, Tägerwilen)
- Gültige Bio-Suisse-Zertifikate (bis Ende 2026) für die Rathgeb BioProdukte AG, die Thurtaler Gemüse AG
  und die ThurBio AG (beide Ellikon) sowie die BioFresh AG (Tägerwilen). 2025 rund 9.6 ha in Umstellung.
- Ellikon: seit April 2023 Nachfolgeregelung mit dem früheren Betrieb Kellermann, keine Fusion.
  Nicht alles am Standort ist Bio (z. B. Purnatur-Tomaten 2024 nicht bio-zertifiziert).
- Produktionsstätte ZH0218/ 1/ 36 (Adresse Rohräcker 414, Unterstammheim, Punkt aber in Ellikon; eine
  Hecke von 0.19 ha in Frauenfeld TG, zwischen den Ellikoner Flächen) ist nach der Lage dem Teil Ellikon
  zugeordnet.
- BioFresh AG: Verwaltungsrat aus der Familie Rathgeb; Gewächshäuser in Tägerwilen.

## Kennzahlen (Bezugsjahr 2025, Hauptkulturen)

| Betrieb | Flächen | ha total | ha Freilandgemüse | ha geschützt | Bioproduktion |
|---|---|---|---|---|---|
| Imhof | 246 | 91.6 | 43.5 | 2.9 | 84.7 ha |
| Beerstecher | 173 | 132.7 | 102.8 | 5.8 | keine deklariert |
| Gerber | 232 | 253.2 | 192.4 | 6.6 | keine deklariert |
| Rathgeb | 441 | 550.3 | 280.0 | 8.7 | 547.4 ha |

Wichtigste Gemeinden (ha):
- Imhof: Schwerzenbach 27.6, Volketswil 13.5, Wangen-Brüttisellen 12.4, Thalheim an der Thur 12.1
- Beerstecher: Dübendorf 45.2, Mönchaltorf 30.2, Fällanden 26.2, Pfäffikon 16.6
- Gerber: Fehraltorf 63.0, Wigoltingen (TG) 60.4, Felben-Wellhausen (TG) 31.2, Hüttlingen (TG) 26.9
- Rathgeb: Ramsen (SH) 52.3, Stammheim 47.7, Ellikon an der Thur 43.1, Basadingen-Schlattingen (TG) 42.0;
  BioFresh AG: Tägerwilen (TG) 8.2

## Suche in TG und SH (Oktober 2026)

Die Daten TG und SH wurden nach weiteren Betriebsnummern der vier Betriebe durchsucht:
- TG: BioFresh AG (TG39621), 12 Flächen / 8.2 ha in Tägerwilen, davon rund 7.5 ha Gewächshäuser
  mit festem Fundament (Codes 801, 848), als Bioproduktion deklariert → zu Rathgeb.
- Für Gerber in TG/SH keine weitere Betriebsnummer gefunden.
- SH: nichts zu den vier Betrieben.

## Offene Punkte

- **ZH0218/ 1/  3** (Alte Horgenbachstr. 2, Ellikon): Recherche ohne Beleg für eine Zugehörigkeit zu
  Rathgeb; vermutlich eigenständig. Nicht aufgenommen.
- **Imhof ZH0197/ 1/702:** Betreiber (Imhof Flora AG oder Imhofbio AG) und Bio-Status offen.
- **Imhof Thalheim an der Thur:** seit wann und auf welcher Grundlage bewirtschaftet, offen.
- **Gerber:** Bio-Zertifikat der Bio Greens AG selbst nicht eingesehen (Zertifikatsdatenbank nicht
  abfragbar); Grund für die fehlende Bio-Meldung nicht bestätigt.

## Quellen (abgerufen Oktober 2026)

- Handelsregister: Zefix (www.zefix.ch), SHAB-Meldungen; moneyhouse.ch als Sekundärquelle.
- Firmenwebsites: imhofbio.ch, gerber.ch (/bio-greens/, /gemuesebau/, je /zertifikate/), beerstecher.ch.
- Bio Suisse / bio.inspecta / easy-cert (Zertifikate Rathgeb-Firmen, Imhof).
- Presse: BauernZeitung 23.07.2024 («Wir können nicht für die Galerie produzieren», Gerber);
  Bioaktuell 7|23 (1.9.2023, Gerber); Schweizer Bauer 08.01.2023 («Zwischen Beton und Baustellen»,
  Beerstecher); Zürcher Oberländer 2024 (Beerstecher); Coopzeitung 2018 und Migros Magazin 2024 (Imhof).
- Recht: Bio-Verordnung (SR 910.18) Art. 6, 7; Direktzahlungsverordnung (SR 910.13) Art. 65, 67;
  Landwirtschaftliche Begriffsverordnung (SR 910.91) Art. 2; Bio Suisse Richtlinien 2026, Teil II Art. 1.2.1.3.
