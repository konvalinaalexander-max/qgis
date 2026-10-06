"""Übersicht der Betriebe als PDF (A4, eine Seite je Betrieb): Firmen, Betriebsnummern, Labels, Flächen.

Aufruf:  python scripts/uebersicht_pdf.py          -> work/uebersicht/uebersicht.html und Vorschaubilder (PNG)
         python scripts/uebersicht_pdf.py --pdf    -> zusätzlich output/<dateinamen.uebersicht>
Zahlen (Flächen, Kulturen, Gemeinden, Bio) kommen aus work/auswahl.gpkg (Schritt 1) und werden wie für die
Website berechnet. Die Angaben zu Firmen, Labels und Standorten stehen unten in SEITEN (Belege: docs/betriebe.md).
Vor dem PDF alles fact-checken (CLAUDE.md, Arbeitsweise). Benötigt Playwright mit Chromium (wie screenshots.py).
"""
import asyncio
import base64
import json
import sys
from html import escape

import geopandas as gpd
from shapely.geometry import mapping

from common import AUSWAHL, CFG, FARMS, OUT, ROOT, WEB, WORK, gemeinde, kulturgruppe, programme, teil_of, teile

STAND = "6. Oktober 2026"
DATEI = CFG["dateinamen"].get("uebersicht", "Betriebe_Firmen_Flaechen.pdf")
ZIEL = WORK / "uebersicht"
GRUPPEN = CFG["kulturgruppen"]
GFARBE = dict(map(tuple, GRUPPEN))
GKURZ = {"Gewächshaus / geschützt": "Gewächshaus, geschützt", "Beeren & Spezialkulturen": "Beeren, Spezialkulturen",
         "Dauerwiese / Weide": "Dauerwiese, Weide", "Biodiversitätsfläche": "Biodiversität", "Wald & übrige Flächen": "Wald, übrige"}
# Kurznamen der Kulturen (Bundeskatalog-Code -> Text in der Übersicht)
KULTUR = {545: "Freilandgemüse", 601: "Kunstwiese", 611: "extensive Wiesen", 613: "übrige Dauerwiesen", 516: "Dinkel",
          524: "Kartoffeln", 513: "Winterweizen", 504: "Hafer", 508: "Körnermais", 521: "Silo- und Grünmais",
          551: "Erdbeeren (einjährige Beeren)", 709: "Rhabarber", 547: "Chicorée-Wurzeln", 572: "Nützlingsstreifen",
          617: "extensive Weiden", 556: "Buntbrache", 801: "Gemüse im Gewächshaus", 802: "Spezialkulturen im Gewächshaus",
          811: "Gemüse geschützt, ohne festes Fundament", 848: "übrige Kulturen im Gewächshaus", 902: "unproduktive Flächen",
          904: "Gräben, Tümpel", 901: "Wald"}

# ---------------------------------------------------------------------------------------------------------------
# Inhalt je Seite. «teil» verweist auf die Teil-IDs aus config/projekt.json (Betrieb-Key + Teil-Key).
# Verbindungen: belegt = Name/Adresse stimmt überein bzw. im Handelsregister belegt; vermutet = nicht belegt.
SEITEN = [
    {
        "key": "imhof", "ort": "Eichhof, Schwerzenbach ZH",
        "profil": "Bio-Gemüse nach Demeter, Topfkräuter und Zierpflanzen; Familienbetrieb auf dem Eichhof.",
        "firmen_titel": "Firmen (alle Eichhof, 8603 Schwerzenbach)",
        "firmen": [
            {"id": "hib", "name": "Hansjürg Imhof Bio-Produkte", "meta": "Einzelperson, nicht im Handelsregister",
             "text": "Gemüsebau; im Bio-Zertifikat als Produktion eingetragen", "labels": ["Demeter", "Knospe"]},
            {"id": "iba", "name": "Imhofbio AG", "meta": "im Handelsregister seit 2010",
             "text": "Bio-Topfkräuter und Zierpflanzen, Aufbereitung und Handel", "labels": ["Demeter", "Knospe", "SwissGAP"]},
            {"id": "ifa", "name": "Imhof Flora AG", "meta": "im Handelsregister seit 2014",
             "text": "Beet- und Balkonpflanzen aus dem Gewächshaus", "labels": ["SwissGAP", "Suisse Garantie"], "kein_bio": True},
        ],
        "betriebe": [
            {"nr": "ZH0197/ 1/  1", "teile": [{"teil": "imhof-haupt",
              "zuordnung": "vermutlich Hansjürg Imhof Bio-Produkte (Produktion laut Zertifikat)"}]},
            {"nr": "ZH0197/ 1/702", "teile": [{"teil": "imhof-gewaechshaus", "art": "1 Gewächshaus mit festem Fundament",
              "zuordnung": "Betreiber nicht belegt: Imhof Flora AG oder Imhofbio AG"}]},
        ],
        "betriebsname": "Betriebsname beider Nummern in den Daten: «Eichhof, 8603 Schwerzenbach»",
        "links": [("hib", "imhof-haupt", "vermutet"), ("iba", "imhof-gewaechshaus", "vermutet"),
                  ("ifa", "imhof-gewaechshaus", "vermutet")],
        "nutzung": ["imhof-haupt", "imhof-gewaechshaus"],
        "hinweise": [
            "Bio Suisse (Knospe) seit 1997; das Gemüse wird seit 2017 nach Demeter angebaut (Firmenangaben). Demeter ist "
            "kein Direktzahlungsprogramm und erscheint nicht in den Daten.",
            "In den Daten sind für beide Nummern zusammen 2.9 ha Gewächshaus und geschützter Anbau erfasst. Laut "
            "Migros-Magazin (2024) umfasst allein die Kräuterproduktion 4 ha Treibhausfläche; ein Teil der Glashäuser ist "
            "offenbar nicht als landwirtschaftliche Nutzfläche deklariert.",
            "In den Zürcher Daten 2025 tragen Gewächshäuser mit festem Fundament nie ein Programm, auch bei Bio-Betrieben. "
            "Der Bio-Status von ZH0197/ 1/702 bleibt deshalb offen.",
            "Thalheim an der Thur (12.1 ha beim Weiler Weidler, Gütighausen, mit Gewächshäusern): keine Quelle zur "
            "Verbindung mit Imhof gefunden.",
        ],
    },
    {
        "key": "beerstecher", "ort": "Hochbord, Dübendorf ZH",
        "profil": "Gemüse, Salate und Beeren nach ÖLN rund um den Greifensee; Gewächshaus mit Abwärme der KEZO in Hinwil.",
        "firmen_titel": "Firmen",
        "firmen": [
            {"id": "bag", "name": "Beerstecher AG", "meta": "im Handelsregister seit 2003 · Hochbordstrasse 15, Dübendorf",
             "text": "Produktion, Handel, Transport und Vertrieb von landwirtschaftlichen Produkten (Zweck laut Handelsregister)",
             "labels": ["SwissGAP", "Migros «Aus der Region»", "Suisse Garantie", "ÖLN"], "kein_bio": True},
            {"id": "bhk", "name": "Beerstechers Hofgarten KLG", "meta": "gleiche Adresse, eingetragen 2024", "klein": True,
             "text": "Zweck: Grossüberbauung auf zwei Grundstücken im Hochbord; kein Landwirtschaftsbetrieb"},
        ],
        "betriebe": [
            {"nr": "ZH0191/ 1/ 55", "teile": [{"teil": "beerstecher", "zuordnung": "Beerstecher AG: Adresse = Firmensitz"}]},
        ],
        "betriebsname": "Betriebsname in den Daten: «Hochbordstrasse 15, 8600 Dübendorf»",
        "links": [("bag", "beerstecher", "belegt")],
        "standorte": [
            ("Hochbord, Dübendorf", "Firmensitz; dort nur noch rund 3 ha Anbau, Überbauung geplant (Gestaltungsplan genehmigt Dezember 2023)"),
            ("Maihof, Hermikon (Dübendorf)", "seit 2004 Teil des Betriebs; Hofladen an der Hermikonstrasse 123"),
            ("Gewächshaus Hinwil-Stocken", "rund 3.4 ha, in Betrieb seit 2015, geheizt mit Abwärme der Kehrichtverwertung KEZO; "
             "Tomaten, Gurken und Peperoni auf Kokossubstrat"),
        ],
        "nutzung": ["beerstecher"],
        "hinweise": [
            "«Auf eine Bio-Zertifizierung hat die Beerstecher AG bisher verzichtet» (Schweizer Bauer, 8.1.2023). Keine Fläche "
            "ist 2025 als Bio gemeldet.",
            "Fläche laut Presse: 130 ha (2023) bzw. 150 ha Freiland (2024); Daten 2025: 132.7 ha.",
            "In Hinwil sind weitere 72’000 m² Gewächshaus geplant (Gestaltungsplan 2024 öffentlich aufgelegt); ein Entscheid ist nicht bekannt.",
            "Nicht verwechseln: Der Biohof Hermikon (Hermikonstrasse 113, ZH0191/ 1/ 53) ist ein eigener Knospe-Betrieb.",
        ],
    },
    {
        "key": "gerber", "ort": "Fehraltorf ZH · Felben-Wellhausen TG",
        "profil": "Zwei Aktiengesellschaften: Bio-Gemüse in Fehraltorf und Flaach, konventionelles Frisch- und Lagergemüse im Thurtal.",
        "firmen_titel": "Firmen",
        "firmen": [
            {"id": "gbg", "name": "Gerber Bio Greens AG", "meta": "im Handelsregister seit 2001 · Zürcherstrasse 75, Fehraltorf",
             "text": "Bio-Gemüse in Fehraltorf und Flaach; bio seit 1996 bzw. 1999 (Quellen uneinheitlich)",
             "labels": ["Knospe (laut Firma)", "bio.inspecta"]},
            {"id": "ggb", "name": "Gerber Gemüsebau AG", "meta": "seit 2000, bis 2021 Gerber Logistik AG · Rosenackerstrasse 9, Felben-Wellhausen",
             "text": "Frisch- und Lagergemüse im Thurtal, Gewächshäuser in Elsau; übernahm 2021 die «Betriebsstätte Felben-Wellhausen»",
             "labels": ["Suisse Garantie", "SwissGAP", "Culinarium"], "kein_bio": True},
            {"id": "gch", "name": "gerber.ch", "meta": "Einzelunternehmen, eingetragen Dezember 2025 · Zürcherstrasse 75, Fehraltorf", "klein": True,
             "text": "Zweck Gemüsebau; Rolle für die Flächen 2025 offen"},
        ],
        "betriebe": [
            {"nr": "ZH0172/ 1/700", "kopf": "eine Betriebsnummer, zwei Produktionsstätten", "teile": [
                {"teil": "gerber-biogreens", "ps": "ZH0172/ 1/ 47", "adresse": "Zürcherstrasse 75, 8320 Fehraltorf",
                 "zuordnung": "Gerber Bio Greens AG: gleiche Adresse"},
                {"teil": "gerber-gemuesebau", "ps": "ZH4561/ 1/  4", "adresse": "Rosenackerstr. 7, 8552 Felben-Wellhausen",
                 "zuordnung": "Gerber Gemüsebau AG: Betriebsstätte Felben-Wellhausen (SHAB 2021)"},
            ]},
        ],
        "betriebsname": "Der Betriebsname in den Daten ist eine Wohnadresse; er wird hier nicht genannt.",
        "links": [("gbg", "gerber-biogreens", "belegt"), ("ggb", "gerber-gemuesebau", "belegt")],
        "nutzung": ["gerber-biogreens", "gerber-gemuesebau"],
        "hinweise": [
            "Keine Gerber-Fläche ist 2025 als Bioproduktion gemeldet. Wahrscheinliche Erklärung, von Gerber nicht bestätigt: Der "
            "Bio-Beitrag gilt für den ganzen Betrieb (Direktzahlungsverordnung Art. 65); eine einzelne Produktionsstätte kann aber "
            "als eigener Biobetrieb anerkannt werden (Bio-Verordnung Art. 7 Abs. 5).",
            "«Rund 80 ha» Bio-Gemüse (BauernZeitung 2024, Bioaktuell 2023) passt zur Ackerfläche der Produktionsstätte Fehraltorf "
            "von rund 87 ha (Gemüse, Kunstwiese, Weizen, Nützlingsstreifen).",
            "Nach Kanton getrennt wären es 125.0 ha ZH und 128.2 ha TG. Das entspricht nicht der Trennung nach Firma: Die Gemüsebau AG "
            "hat auch 18.9 ha in Zürich.",
            "Das Bio-Zertifikat der Bio Greens AG selbst war nicht einsehbar.",
        ],
    },
    {
        "key": "rathgeb", "ort": "Unterstammheim ZH · Marke «Rathgeb Bio»",
        "profil": "Bio-Gemüse, Kartoffeln und Gewächshauskulturen in den Kantonen Zürich, Schaffhausen und Thurgau.",
        "firmen_titel": "Firmen der Rathgeb-Gruppe mit Flächen",
        "firmen": [
            {"id": "rbp", "name": "Rathgeb BioProdukte AG", "meta": "seit 2016 · Rohräcker 414, Unterstammheim",
             "text": "Anbau; vorher Einzelunternehmen «Rathgeb's Bioprodukte»; 2025 waren 9.6 ha in Umstellung",
             "labels": ["Knospe bis 2026"]},
            {"id": "ttg", "name": "Thurtaler Gemüse AG", "meta": "Langbreiten, Ellikon an der Thur",
             "text": "Früher Kellermann-Gruppe, seit 2023 Rathgeb-Gruppe", "labels": ["Knospe bis 2026"]},
            {"id": "tbi", "name": "ThurBio AG", "meta": "Neue Horgenbachstrasse 4, Ellikon an der Thur",
             "text": "Bis 2025 Berryfresh AG (2016 in Menzengrüt gegründet); betreibt das neue Gewächshaus in Ellikon",
             "labels": ["Knospe"]},
            {"id": "bfr", "name": "BioFresh AG", "meta": "seit 2005 · Poststrasse 29, Tägerwilen TG",
             "text": "Gewächshäuser, 2005 von der Biotta AG übernommen", "labels": ["Knospe bis 2026"]},
        ],
        "firmen_weitere": "Weitere Firmen der Gruppe, ohne Flächen in den Daten: Rathgeb Holding AG (Beteiligungen) · Rathgeb BioLog AG "
                          "(Aufbereitung, Vertrieb, Import) · Rathgeb Natura AG · kellermann.ch ag (Verarbeitung, Ellikon) · Purnatur AG "
                          "(Tomaten, Ellikon; 2024 nicht bio-zertifiziert)",
        "betriebe": [
            {"nr": "ZH0042/ 1/850", "kopf": "Betriebsname «Rohräcker 414, 8476 Unterstammheim»", "teile": [
                {"teil": "rathgeb-unterstammheim", "ps": "ZH0042/ 1/ 48", "adresse": "Rohräcker 414, Unterstammheim",
                 "zuordnung": "Rathgeb BioProdukte AG: gleiche Adresse"},
                {"teil": "rathgeb-ellikon", "ps": "ZH0218/ 1/ 30 + 36", "adresse": "Neue Horgenbachstrasse 2/4, Ellikon an der Thur",
                 "zuordnung": "ThurBio AG: gleiche Adresse; Thurtaler Gemüse AG: Standort Ellikon"},
            ]},
            {"nr": "TG39621", "kopf": "Betriebsname «BioFresh AG»", "teile": [
                {"teil": "rathgeb-biofresh", "zuordnung": "BioFresh AG: Name im Datensatz"}]},
        ],
        "links": [("rbp", "rathgeb-unterstammheim", "belegt"), ("tbi", "rathgeb-ellikon", "belegt"),
                  ("ttg", "rathgeb-ellikon", "vermutet"), ("bfr", "rathgeb-biofresh", "belegt")],
        "nutzung": ["rathgeb-unterstammheim", "rathgeb-ellikon", "rathgeb-biofresh"],
        "hinweise": [
            "Kellermann: seit April 2023 Nachfolgeregelung, keine Fusion; die Kellermann-Firmen bestehen weiter und gehören zur Rathgeb-Gruppe.",
            "Nicht als Bio gemeldet sind 2.9 ha: Wald, unproduktive Flächen, Gräben, Hecken und ein Gewächshaus von 0.3 ha.",
            "Laut Bioaktuell (Juli 2024) rund 600 ha Gesamtfläche, dazu rund 80 Betriebe der Region, die für Rathgeb produzieren oder "
            "Flächen verpachten; die Daten zeigen nur die Flächen der beiden Betriebsnummern.",
            "Das neue Gewächshaus in Ellikon (rund 4 ha, Bio-Tomaten und -Gurken in Erdkultur) erscheint in den Daten 2025 noch nicht.",
        ],
    },
]


# ---------------------------------------------------------------------------------------------------------------
def daten():
    nf = gpd.read_file(AUSWAHL, layer="nutzungsflaechen")
    nf = nf[nf.ist_ueberlagernd != True].copy()
    nf["teil"] = [teil_of(n, ps)["id"] for n, ps in zip(nf.betriebsnummer, nf.ps_nr)]
    nf["gruppe"] = [kulturgruppe(c, n) for c, n in zip(nf.lnf_code, nf.nutzung)]
    nf["bio"] = ["Bioproduktion" in programme(p) for p in nf.programm]
    gk = [gemeinde(b) for b in nf.gemeinde]
    nf["gname"] = [g[0] for g in gk]
    nf["gkt"] = [g[1] for g in gk]
    nf["ha"] = nf.flaeche_m2 / 1e4
    return nf


def zahl(x, d=1):
    s = f"{x:,.{d}f}".replace(",", "’")
    return s


def ha(x):
    return zahl(x) + " ha"


def einheit(nf, tid):
    d = nf[nf.teil == tid]
    gr = d.groupby("gruppe").ha.sum()
    ku = d.groupby("lnf_code").agg(ha=("ha", "sum"), name=("nutzung", "first")).sort_values("ha", ascending=False)
    ge = d.groupby(["gname", "gkt"]).ha.sum().sort_values(ascending=False)
    return {"n": len(d), "ha": d.ha.sum(), "bio": d[d.bio].ha.sum(), "gruppen": gr, "kulturen": ku, "gemeinden": ge,
            "kantone": d.groupby("kanton").ha.sum()}


def bar(gruppen, total):
    segs = []
    for g, farbe in GRUPPEN:
        v = gruppen.get(g, 0)
        if v <= 0:
            continue
        w = 100 * v / total
        lab = zahl(v) if w >= 7 else ""
        segs.append(f'<span class="seg" style="width:{w:.3f}%;background:{farbe}" title="{escape(g)} {zahl(v)} ha">'
                    f'<i>{lab}</i></span>')
    return '<div class="bar">' + "".join(segs) + "</div>"


def kulturen_text(e, n=6):
    out = []
    for code, r in e["kulturen"].head(n).iterrows():
        if r.ha < 0.05:
            continue
        out.append(f"{escape(KULTUR.get(int(code), r['name']))} {zahl(r.ha)}")
    return " · ".join(out)


def gemeinden_text(e, n=5):
    ge = e["gemeinden"]
    out = [f"{escape(g)}{' ' + k if k and k != 'ZH' and not g.endswith(')') else ''} {zahl(v)}" for (g, k), v in ge.head(n).items()]
    rest = len(ge) - n
    if rest > 0:
        out.append(f"{rest} weitere")
    return " · ".join(out)


def tags(f):
    t = "".join(f'<span class="tag{" bio" if any(k in l for k in ("Knospe", "Demeter", "Bio")) else ""}">{escape(l)}</span>'
                for l in f.get("labels", []))
    if f.get("kein_bio"):
        t += '<span class="tag nb">kein Bio</span>'
    return f'<span class="tags">{t}</span>' if t else ""


def seite(s, nf, nr_seite, n_seiten):
    farm = next(f for f in FARMS if f["key"] == s["key"])
    tk = {t["id"]: t for t in teile(farm)}
    ein = {tid: einheit(nf, tid) for tid in tk}
    tot = nf[nf.teil.isin(list(tk))]
    total, bio = tot.ha.sum(), tot[tot.bio].ha.sum()
    n_nr = len(farm["nrs"])
    n_ps = sum(len(b["teile"]) for b in s["betriebe"])
    nr_text = f"{n_nr} Betriebsnummer{'n' if n_nr > 1 else ''}"
    zusatz = ""
    if n_ps > n_nr:
        zusatz = f"{n_ps} Standorte" if n_nr > 1 else f"{n_ps} Produktionsstätten"
    bio_txt = (f"{ha(bio)} <small>{bio / total * 100:.0f} %</small>" if bio > 0.05 else "0 ha")
    kz = [("Fläche 2025", ha(total)), ("Flächen", zahl(len(tot), 0)),
          ("Betriebsnummern", f"{n_nr}" + (f" <small>· {zusatz}</small>" if zusatz else "")), ("Bio gemeldet", bio_txt)]
    kz_html = "".join(f'<div><dt>{a}</dt><dd>{b}</dd></div>' for a, b in kz)

    # Firmen
    fh = []
    for f in s["firmen"]:
        fh.append(f'<div class="firma{" klein" if f.get("klein") else ""}" id="f-{s["key"]}-{f["id"]}">'
                  f'<div class="fh"><span class="fn">{escape(f["name"])}</span>{tags(f)}</div>'
                  f'<div class="fm">{escape(f["meta"])}</div><div class="ft">{escape(f["text"])}</div></div>')

    # Amtliche Betriebe
    bh = []
    for b in s["betriebe"]:
        mehr = len(b["teile"]) > 1 or "ps" in b["teile"][0]
        inner = []
        for t in b["teile"]:
            e = ein[t["teil"]]
            kopf = (f'<div class="psk">Produktionsstätte <span class="mono">{escape(t["ps"])}</span></div>'
                    f'<div class="psa">{escape(t["adresse"])}</div>') if t.get("ps") else ""
            art = f' · {escape(t["art"])}' if t.get("art") else ""
            code = tk[t["teil"]].get("bio", "nein")
            if e["bio"] > 0.05:
                biozeile = f'<span class="nb2"><i class="dot bio"></i>{ha(e["bio"])} Bio gemeldet</span>'
            elif code == "firma":
                biozeile = '<span class="nb2"><i class="dot firma"></i>Bio laut Firma, keine Fläche als Bio gemeldet</span>'
            elif code == "offen":
                biozeile = '<span class="nb2"><i class="dot offen"></i>Bio-Status unklar</span>'
            else:
                biozeile = '<span class="nb2"><i class="dot"></i>keine Fläche als Bio gemeldet</span>'
            inner.append(f'<div class="einheit{" ps" if t.get("ps") else ""}" id="u-{t["teil"]}">{kopf}'
                         f'<div class="ez"><span><b>{ha(e["ha"])}</b> · {zahl(e["n"], 0)} Fläche{"n" if e["n"] != 1 else ""}{art}</span>'
                         f'{biozeile}</div><div class="zu">{escape(t["zuordnung"])}</div></div>')
        if mehr:
            d = nf[nf.teil.isin([t["teil"] for t in b["teile"]])]
            bh.append(f'<div class="nrgrp"><div class="nrk"><span class="mono big">{escape(b["nr"])}</span>'
                      f'<span class="nrh">{escape(b.get("kopf", ""))}</span></div>'
                      f'<div class="ez sum">{ha(d.ha.sum())} · {zahl(len(d), 0)} Flächen</div>{"".join(inner)}</div>')
        else:
            bh.append(f'<div class="nrgrp single"><div class="nrk"><span class="mono big">{escape(b["nr"])}</span>'
                      f'<span class="nrh">{escape(b.get("kopf", ""))}</span></div>{"".join(inner)}</div>')
    if s.get("betriebsname"):
        bh.append(f'<p class="bn">{escape(s["betriebsname"])}</p>')
    links = [{"von": f"f-{s['key']}-{a}", "nach": f"u-{b}", "art": c} for a, b, c in s["links"]]

    # Nutzung
    used = set()
    nh = []
    for tid in s["nutzung"]:
        e, t = ein[tid], tk[tid]
        used |= {g for g, v in e["gruppen"].items() if v > 0}
        name = escape(t["name"] if len(tk) > 1 else farm["name"])
        kant = ""
        if len(e["kantone"]) > 1:
            kant = " · " + " · ".join(f"{k} {zahl(v)}" for k, v in e["kantone"].sort_values(ascending=False).items())
        if e["ha"] < 10:   # kleine Einheit: eine Zeile statt Balken
            nh.append(f'<div class="nu klein"><div class="nuk"><b>{name}</b><span>{ha(e["ha"])} · {kulturen_text(e, 4)}'
                      f'{" · " + gemeinden_text(e, 1) if len(e["gemeinden"]) == 1 else ""}</span></div></div>')
            continue
        nh.append(f'<div class="nu"><div class="nuk"><b>{name}</b><span>{ha(e["ha"])}{kant}</span></div>{bar(e["gruppen"], e["ha"])}'
                  f'<div class="nul"><span class="l">Kulturen</span>{kulturen_text(e)}</div>'
                  f'<div class="nul"><span class="l">Gemeinden</span>{gemeinden_text(e)}</div></div>')
    leg = "".join(f'<span><i style="background:{c}"></i>{escape(GKURZ.get(g, g))}</span>' for g, c in GRUPPEN if g in used)
    karte_leg = ("".join(f'<span><i style="background:{t["color"]}"></i>{escape(t["kurz"] if len(tk) > 1 else farm["name"])}</span>'
                         for t in tk.values()) + '<span class="q">Landeskarte © swisstopo</span>')

    std = ""
    if s.get("standorte"):
        std = ('<section class="std"><h2>Standorte</h2><dl>' +
               "".join(f"<dt>{escape(a)}</dt><dd>{escape(b)}</dd>" for a, b in s["standorte"]) + "</dl></section>")
    hin = "".join(f"<li>{escape(h)}</li>" for h in s["hinweise"])
    return f"""
<section class="page" style="--fc:{farm['color']}">
  <div class="run"><span>Gemüsebetriebe · Firmen, Betriebsnummern und Flächen</span><span>Stand {STAND}</span></div>
  <header class="kopf">
    <div class="titel"><h1><span class="sw"></span>{escape(farm['name'])}</h1><p class="ort">{escape(s['ort'])}</p></div>
    <dl class="kz">{kz_html}</dl>
  </header>
  <p class="profil">{escape(s['profil'])}</p>
  <section class="struktur" data-links='{escape(json.dumps(links))}'>
    <div class="col"><h2>{escape(s['firmen_titel'])}</h2>{''.join(fh)}</div>
    <div class="gap"></div>
    <div class="col"><h2>Amtliche Betriebe 2025</h2>{''.join(bh)}</div>
    <svg class="links" aria-hidden="true"></svg>
  </section>
  {f'<p class="weitere">{escape(s["firmen_weitere"])}</p>' if s.get("firmen_weitere") else ''}
  {std}
  <section class="nutzung"><h2>Nutzung und Lage 2025</h2>
    <div class="nugrid"><div><div class="leg">{leg}</div>{''.join(nh)}</div>
    <figure class="karte"><img src="__KARTE_{s['key']}__" alt="Lage der Flächen"><figcaption>{karte_leg}</figcaption></figure></div>
  </section>
  <section class="hinweise"><h2>Hinweise</h2><ul>{hin}</ul></section>
  <footer class="fuss">
    <p><b>Linien</b> durchgezogen: Name oder Adresse stimmt überein bzw. im Handelsregister belegt · gestrichelt: vermutet, nicht belegt.
    <b>Betriebsnummer</b>: amtliche Nummer eines Landwirtschaftsbetriebs (Direktzahlungen); <b>Produktionsstätte</b>: Standort innerhalb
    eines Betriebs; <b>Bio gemeldet</b>: Fläche mit dem Direktzahlungsprogramm Bioproduktion 2025. Labels wie die Knospe stehen nicht in den Daten.</p>
    <p><b>Quellen</b> Flächen: Kantone ZH, TG und SH, Landwirtschaftliche Kulturflächen, Bezugsjahr 2025 (geodienste.ch), deklarierte
    Hauptkulturen. Firmen: Handelsregister (Zefix, SHAB), Zertifikate, Firmenwebsites, Fachpresse; abgerufen am {STAND}.</p>
    <span class="pn">{nr_seite} / {n_seiten}</span>
  </footer>
</section>"""


KARTE_MM = 52
KARTE_PX = 400          # Kartengrösse beim Rendern in CSS-Pixeln (wird auf KARTE_MM verkleinert: kleinere Schrift der Landeskarte)


def dunkler(hex_, f):
    n = int(hex_[1:], 16)
    return "#" + "".join(f"{round(((n >> k) & 255) * f):02x}" for k in (16, 8, 0))


def karte_html(nf, farm):
    """Kleine Karte: Flächen in den Farben der Teile auf der Landeskarte grau (swisstopo, aus dem Internet)."""
    tk = {t["id"]: t for t in teile(farm)}
    d = nf[nf.teil.isin(list(tk))].to_crs(4326)
    feats = [{"type": "Feature", "geometry": mapping(g.simplify(0.00002)),
              "properties": {"c": tk[t]["color"], "r": dunkler(tk[t]["color"], .8)}} for g, t in zip(d.geometry, d.teil)]
    leaflet = WEB / "vendor" / "leaflet"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{(leaflet / "leaflet.css").read_text(encoding="utf-8")}
html,body{{margin:0;background:#fff}} #m{{width:{KARTE_PX}px;height:{KARTE_PX}px;background:#fff}}
.leaflet-tile-pane{{opacity:.5}}
.leaflet-control-scale-line{{font:11px/1.2 Arial,sans-serif;padding:0 3px;border-width:0 1px 1px;background:rgba(255,255,255,.85)}}
.leaflet-bottom.leaflet-left .leaflet-control{{margin:0 0 4px 4px}}</style></head>
<body><div id="m"></div><script>{(leaflet / "leaflet.js").read_text(encoding="utf-8")}</script><script>
const m=L.map('m',{{zoomControl:false,attributionControl:false,zoomSnap:1,fadeAnimation:false,zoomAnimation:false,markerZoomAnimation:false}});
const t=L.tileLayer('https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-grau/default/current/3857/{{z}}/{{x}}/{{y}}.jpeg',
  {{maxNativeZoom:19,maxZoom:20}});
const g=L.geoJSON({json.dumps({"type": "FeatureCollection", "features": feats})},
  {{style:f=>({{color:f.properties.r,weight:2.6,opacity:1,fillColor:f.properties.c,fillOpacity:1}})}});
m.fitBounds(g.getBounds(),{{padding:[18,18]}});
t.addTo(m); g.addTo(m);
L.control.scale({{imperial:false,position:'bottomleft',maxWidth:60}}).addTo(m);
t.on('load',()=>setTimeout(()=>document.body.dataset.fertig='1',400));
</script></body></html>"""


async def karten(ctx, nf):
    bilder = {}
    for s in SEITEN:
        farm = next(f for f in FARMS if f["key"] == s["key"])
        src = ZIEL / f"karte_{s['key']}.html"
        src.write_text(karte_html(nf, farm), encoding="utf-8")
        pg = await ctx.new_page()
        await pg.set_viewport_size({"width": KARTE_PX, "height": KARTE_PX})
        await pg.goto(src.as_uri())
        await pg.wait_for_selector("body[data-fertig='1']", timeout=60000)
        jpg = await pg.locator("#m").screenshot(type="jpeg", quality=88)
        (ZIEL / f"karte_{s['key']}.jpg").write_bytes(jpg)
        bilder[s["key"]] = "data:image/jpeg;base64," + base64.b64encode(jpg).decode()
        await pg.close()
    return bilder


def schrift(name):
    return base64.b64encode((WEB / "vendor" / "fonts" / name).read_bytes()).decode()


CSS = """
@font-face{font-family:"Plex";src:url(data:font/woff2;base64,__SANS__) format("woff2");font-weight:100 700}
@font-face{font-family:"PlexMono";src:url(data:font/woff2;base64,__MONO__) format("woff2");font-weight:400}
@page{size:A4;margin:0}
:root{--ink:#1c2420;--muted:#5d6862;--faint:#8d9691;--line:#d6dcd8;--soft:#f3f5f3;--bio:#1d7a45}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
body{font-family:"Plex",sans-serif;font-size:8.4pt;line-height:1.36;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact;
  font-variant-numeric:tabular-nums}
.page{width:210mm;height:297mm;padding:10mm 14mm 9mm;position:relative;overflow:hidden;break-after:page;display:flex;flex-direction:column}
.page:last-child{break-after:auto}
.mono{font-family:"PlexMono",monospace;white-space:pre;letter-spacing:-.01em}
h2{font-size:9pt;font-weight:600;color:var(--ink);margin:0 0 2.4mm;padding-bottom:1.1mm;border-bottom:.6pt solid var(--line)}
.run{display:flex;justify-content:space-between;font-size:7pt;color:var(--faint);padding-bottom:4.2mm}
.kopf{display:flex;justify-content:space-between;align-items:flex-end;gap:8mm;padding-bottom:3mm;border-bottom:1.4pt solid var(--ink)}
h1{font-size:27pt;line-height:1;font-weight:600;letter-spacing:-.015em;margin:0;display:flex;align-items:center;gap:3mm}
h1 .sw{width:5mm;height:5mm;border-radius:1mm;background:var(--fc);display:inline-block}
.ort{margin:1.6mm 0 0;font-size:10pt;color:var(--muted)}
.kz{display:grid;grid-template-columns:repeat(4,auto);gap:0 6mm;margin:0}
.kz div{min-width:17mm}
.kz dt{font-size:6.8pt;color:var(--muted);letter-spacing:.04em}
.kz dd{margin:.6mm 0 0;font-size:13pt;font-weight:600;white-space:nowrap}
.kz dd small{font-size:8pt;font-weight:500;color:var(--muted)}
.profil{font-size:9.6pt;margin:2.4mm 0 4.2mm;color:#2c3530}
.struktur{position:relative;display:grid;grid-template-columns:86mm 12mm 1fr;margin-bottom:3.6mm}
.struktur .gap{}
svg.links{position:absolute;left:0;top:0;pointer-events:none;overflow:visible}
.firma{border-left:2.2pt solid var(--fc);padding:.3mm 0 .3mm 3mm;margin-bottom:3mm;background:#fff;position:relative}
.fh{display:flex;flex-wrap:wrap;align-items:center;gap:1mm 2.4mm}
.firma.klein{border-left-color:var(--line)}
.firma.klein .fn{font-size:8.6pt}
.fn{font-size:10pt;font-weight:600;line-height:1.2}
.fm{font-size:7.4pt;color:var(--muted);margin-top:.4mm}
.ft{margin-top:.8mm}
.tags{display:inline-flex;flex-wrap:wrap;gap:1mm}
.tag{font-size:6.8pt;line-height:1.3;padding:.25mm 1.4mm;border:.5pt solid #b7c0bb;border-radius:.8mm;color:#3b4540;white-space:nowrap}
.tag.bio{border-color:#7fbf98;color:var(--bio)}
.tag.nb{border-style:dashed;color:var(--muted)}
.weitere{font-size:7.4pt;color:var(--muted);margin:-1.2mm 0 3.8mm;padding-left:3.8mm;max-width:172mm}
.nrgrp{border:.6pt solid #c9d1cc;border-radius:1.2mm;padding:2mm 2.6mm 1.2mm;margin-bottom:3mm;background:#fff;position:relative}
.nrk{display:flex;flex-direction:column;gap:.3mm;margin-bottom:1mm}
.mono.big{font-size:9.6pt;font-weight:400}
.nrh{font-size:7pt;color:var(--muted)}
.ez{font-size:8.2pt;display:flex;flex-wrap:wrap;align-items:center;gap:.3mm 2.6mm}
.ez b{font-weight:600}
.ez.sum{color:var(--muted);font-size:7.4pt;margin:-.6mm 0 1.4mm}
.einheit{padding:0 0 1.2mm}
.einheit.ps{border-top:.5pt solid var(--line);padding-top:1.4mm;margin-top:.4mm}
.nrgrp.single .einheit{padding-top:0}
.psk{font-size:7.2pt;color:var(--muted)}
.psk .mono{color:var(--ink);font-size:8pt}
.psa{font-size:7.2pt;color:var(--muted);margin-bottom:.6mm}
.nb2{font-size:7.4pt;color:var(--muted);display:inline-flex;align-items:center;gap:1.2mm}
.dot{width:1.8mm;height:1.8mm;flex:none;border-radius:50%;background:#e39b2d;display:inline-block}
.dot.bio{background:#12a150}
.dot.firma{background:#8ee07a}
.dot.offen{background:#9aa1a9}
.zu{font-size:7.2pt;margin-top:.5mm;color:#3b4540}
.bn{font-size:7pt;color:var(--muted);margin:.4mm 0 0}
.std{margin-bottom:4.5mm}
.std dl{display:grid;grid-template-columns:44mm 1fr;gap:1.1mm 4mm;margin:0}
.std dt{font-weight:600}
.std dd{margin:0}
.nutzung{margin-bottom:3.4mm}
.leg{display:flex;flex-wrap:wrap;gap:.6mm 2.6mm;font-size:6.5pt;color:var(--muted);margin:-.6mm 0 2.4mm}
.leg span{display:inline-flex;align-items:center;gap:1mm;white-space:nowrap}
.leg i{width:2.2mm;height:2.2mm;border-radius:.4mm;display:inline-block}
.nu{margin-bottom:2.8mm}
.nugrid{display:grid;grid-template-columns:1fr 52mm;gap:5mm;align-items:start}
.karte{margin:0}
.karte img{display:block;width:52mm;height:52mm;border:.5pt solid #c9d1cc;border-radius:1mm}
.karte figcaption{display:flex;flex-wrap:wrap;gap:.5mm 2.4mm;font-size:6.5pt;color:var(--muted);margin-top:1.2mm}
.karte figcaption span{display:inline-flex;align-items:center;gap:1mm}
.karte figcaption i{width:2.2mm;height:2.2mm;border-radius:.4mm;display:inline-block}
.karte figcaption .q{margin-left:auto}
.nuk{display:flex;justify-content:space-between;gap:4mm;margin-bottom:.9mm;font-size:8.4pt}
.nuk span{color:var(--muted);font-size:7.6pt}
.nu.klein .nuk{justify-content:flex-start;gap:2.5mm;font-size:7.6pt}
.nu.klein .nuk span{font-size:7.6pt}
.nu.klein b{color:var(--ink);font-weight:600}
.bar{display:flex;height:4.6mm;border-radius:.6mm;overflow:hidden;margin-bottom:1.2mm}
.seg{display:flex;align-items:center;justify-content:center;min-width:.4mm}
.seg i{font-style:normal;font-size:6.4pt;color:#fff;font-weight:600;text-shadow:0 0 1.5px rgba(0,0,0,.45)}
.nul{font-size:7.6pt;line-height:1.38;display:grid;grid-template-columns:17mm 1fr;gap:2mm}
.nul .l{color:var(--muted)}
.hinweise ul{margin:0;padding:0;list-style:none}
.hinweise li{position:relative;padding-left:3.2mm;margin-bottom:1.1mm;font-size:7.9pt}
.hinweise li::before{content:"–";position:absolute;left:0;color:var(--muted)}
.fuss{margin-top:auto;padding-top:2.4mm;border-top:.6pt solid var(--line);font-size:6.4pt;line-height:1.38;color:var(--muted);position:relative;padding-right:12mm}
.fuss p{margin:0 0 .8mm}
.fuss b{font-weight:600;color:#4a544f}
.pn{position:absolute;right:0;bottom:.8mm;font-size:7pt;color:var(--ink)}
"""

JS = r"""
function linien(){
  for (const sec of document.querySelectorAll('.struktur')){
    const svg=sec.querySelector('svg.links'), R=sec.getBoundingClientRect(), mm=96/25.4;
    svg.setAttribute('width',R.width); svg.setAttribute('height',R.height);
    svg.innerHTML='';
    const links=JSON.parse(sec.dataset.links), nOut={}, nIn={}, iOut={}, iIn={};
    links.forEach(l=>{nOut[l.von]=(nOut[l.von]||0)+1; nIn[l.nach]=(nIn[l.nach]||0)+1;});
    const farbe=getComputedStyle(sec.closest('.page')).getPropertyValue('--fc').trim();
    for (const l of links){
      const a=document.getElementById(l.von), b=document.getElementById(l.nach);
      if(!a||!b) continue;
      const A=a.getBoundingClientRect(), B=(b.closest('.nrgrp.single')||b).getBoundingClientRect();
      const io=iOut[l.von]=(iOut[l.von]||0)+1, ii=iIn[l.nach]=(iIn[l.nach]||0)+1;
      const y1=A.top-R.top+3.2*mm+(io-1-(nOut[l.von]-1)/2)*1.6*mm;
      const y2=B.top-R.top+(b.closest('.nrgrp.single')?4.4:2.6)*mm+(ii-1-(nIn[l.nach]-1)/2)*1.8*mm;
      const x1=A.right-R.left+1.2*mm, x2=B.left-R.left-1.2*mm, xm=(x1+x2)/2;
      const p=document.createElementNS('http://www.w3.org/2000/svg','path');
      p.setAttribute('d',`M${x1},${y1} C${xm},${y1} ${xm},${y2} ${x2},${y2}`);
      p.setAttribute('fill','none'); p.setAttribute('stroke',l.art==='vermutet'?'#7d8782':'#2b3530');
      p.setAttribute('stroke-width',0.9);
      if(l.art==='vermutet') p.setAttribute('stroke-dasharray','3 2.2');
      svg.appendChild(p);
      for (const [x,y] of [[x1,y1],[x2,y2]]){
        const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
        c.setAttribute('cx',x); c.setAttribute('cy',y); c.setAttribute('r',1.6);
        c.setAttribute('fill',l.art==='vermutet'?'#fff':'#2b3530'); c.setAttribute('stroke',l.art==='vermutet'?'#7d8782':'#2b3530');
        c.setAttribute('stroke-width',0.8); svg.appendChild(c);
      }
    }
  }
}
document.fonts.ready.then(()=>{linien(); document.body.dataset.fertig='1';});
"""


def html(nf):
    seiten = "".join(seite(s, nf, i + 1, len(SEITEN)) for i, s in enumerate(SEITEN))
    css = CSS.replace("__SANS__", schrift("ibm-plex-sans-latin-var.woff2")).replace("__MONO__", schrift("ibm-plex-mono-latin-400.woff2"))
    return f"""<!doctype html>
<html lang="de-CH"><head><meta charset="utf-8"><title>Gemüsebetriebe – Firmen, Betriebsnummern und Flächen</title>
<style>{css}</style></head><body>{seiten}<script>{JS}</script></body></html>"""


async def rendern(nf, pdf):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 794, "height": 1123}, device_scale_factor=2)
        bilder = await karten(ctx, nf)
        text = html(nf)
        for k, v in bilder.items():
            text = text.replace(f"__KARTE_{k}__", v)
        src = ZIEL / "uebersicht.html"
        src.write_text(text, encoding="utf-8")
        await ctx.close()
        ctx = await b.new_context(viewport={"width": 794, "height": 1123}, device_scale_factor=2)
        pg = await ctx.new_page()
        await pg.goto(src.as_uri())
        await pg.wait_for_selector("body[data-fertig='1']")
        n = await pg.locator(".page").count()
        for i in range(n):
            await pg.locator(".page").nth(i).screenshot(path=str(ZIEL / f"seite_{i + 1}.png"))
        ueber = await pg.evaluate("""[...document.querySelectorAll('.page')].map(p=>{
            const mm=96/25.4, r=p.getBoundingClientRect(), f=p.querySelector('.fuss').getBoundingClientRect();
            const kids=[...p.children].filter(c=>!c.classList.contains('fuss'));
            const last=Math.max(...kids.map(c=>c.getBoundingClientRect().bottom));
            const unten=r.bottom-parseFloat(getComputedStyle(p).paddingBottom);
            return {frei: Math.round((f.top-last)/mm*10)/10, zuviel: Math.round((f.bottom-unten)/mm*10)/10};})""")
        for i, u in enumerate(ueber, 1):
            print(f"Seite {i}: frei vor der Fusszeile {u['frei']} mm" + (f"  ZU LANG um {u['zuviel']} mm" if u["zuviel"] > 0.2 else ""))
        if pdf:
            await pg.emulate_media(media="print")
            await pg.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
        await b.close()


if __name__ == "__main__":
    ZIEL.mkdir(parents=True, exist_ok=True)
    nf = daten()
    pdf = OUT / DATEI if "--pdf" in sys.argv else None
    asyncio.run(rendern(nf, pdf))
    print("HTML:", (ZIEL / "uebersicht.html").relative_to(ROOT), "| Vorschau:", (ZIEL / "seite_1.png").relative_to(ROOT), "…")
    if pdf:
        print("PDF:", pdf.relative_to(ROOT))
