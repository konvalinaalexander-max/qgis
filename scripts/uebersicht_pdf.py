"""Übersicht der Betriebe als PDF auf einer A4-Seite: Firmen, Betriebsnummern, Flächen, Bio, Kulturen.

Aufruf:  python scripts/uebersicht_pdf.py          -> work/uebersicht/uebersicht.html + Vorschaubild (PNG)
         python scripts/uebersicht_pdf.py --pdf    -> zusätzlich output/<dateinamen.uebersicht>
Die Zahlen kommen aus work/auswahl.gpkg (Schritt 1, gleich gerechnet wie die Website). Die Angaben zu Firmen und
Labels stehen unten in BETRIEBE (Belege: docs/betriebe.md). Vor dem PDF alles fact-checken (CLAUDE.md, Arbeitsweise).
Benötigt Playwright mit Chromium (wie scripts/screenshots.py).
"""
import asyncio
import base64
import sys
from html import escape

import geopandas as gpd

from common import AUSWAHL, CFG, FARMS, OUT, ROOT, WEB, WORK, programme, teil_of

STAND = "6. Oktober 2026"
DATEI = CFG["dateinamen"].get("uebersicht", "Betriebe_Firmen_Flaechen.pdf")
ZIEL = WORK / "uebersicht"

# Kulturen: Code(s) des Bundeskatalogs -> Kurzname; mehrere Codes werden zusammengezählt
KULTUREN = [((545, 546, 547), "Freilandgemüse"), ((601, 602), "Kunstwiese"), ((524, 525), "Kartoffeln"),
            ((611,), "extensive Wiesen"), ((612, 613), "übrige Dauerwiesen"), ((516,), "Dinkel"),
            ((512, 513, 514, 515), "Weizen"), ((508, 521), "Mais"), ((551,), "einjährige Beeren"), ((709,), "Rhabarber"),
            ((801, 802, 803, 804, 807, 808, 811, 812, 813, 814, 847, 848, 849), "Gewächshaus und geschützter Anbau")]

# Firmen je Betrieb: (Name, Angaben, Tätigkeit, Teil-ID für die Fläche oder None, Bezug der Fläche)
BETRIEBE = [
    {"key": "imhof", "ort": "Eichhof, Schwerzenbach ZH",
     "bio": "ja – 84.7 ha als Bio gemeldet; Bio Suisse (Knospe), Gemüse nach Demeter",
     "firmen": [
         ("Hansjürg Imhof Bio-Produkte", "Einzelunternehmen, nicht im Handelsregister",
          "Bio-Gemüse und Bio-Topfkräuter; Demeter, Knospe", "imhof-haupt", '<span class="nr">ZH0197/ 1/  1</span>, Betreiber vermutet'),
         ("Imhofbio AG", "seit 2010", "Bio-Topfkräuter und Bio-Weihnachtssterne, Aufbereitung und Handel; Demeter, Knospe", None, None),
         ("Imhof Flora AG", "seit 2014", "Beet- und Balkonpflanzen; nicht Bio", None, None),
     ],
     "zusatz": '<span class="nr">ZH0197/ 1/702</span>' + ": ein Gewächshaus auf dem Eichhof (1.0 ha); Betreiber (Imhof Flora AG oder Imhofbio AG) und "
               "Bio-Status nicht belegt."},
    {"key": "beerstecher", "ort": "Dübendorf ZH",
     "bio": "nein – keine Fläche als Bio gemeldet; ÖLN, SwissGAP, Suisse Garantie, Migros «Aus der Region»",
     "firmen": [
         ("Beerstecher AG", "seit 2003, Hochbordstrasse 15, Dübendorf",
          "Gemüse, Salate und Beeren; Gewächshaus in Hinwil mit Abwärme der KEZO", "beerstecher", '<span class="nr">ZH0191/ 1/ 55</span>'),
     ]},
    {"key": "gerber", "ort": "Fehraltorf ZH · Felben-Wellhausen TG",
     "bio": "teilweise laut Firma – Bio Greens AG nach Bio-Suisse-Richtlinien; in den Daten keine Fläche als Bio gemeldet",
     "firmen": [
         ("Gerber Bio Greens AG", "seit 2001, Fehraltorf", "Bio-Gemüse in Fehraltorf und Flaach; Knospe laut Firma",
          "gerber-biogreens", "Produktionsstätte Fehraltorf"),
         ("Gerber Gemüsebau AG", "seit 2000, bis 2021 Gerber Logistik AG; Felben-Wellhausen",
          "Frisch- und Lagergemüse im Thurtal, konventionell (Suisse Garantie)", "gerber-gemuesebau",
          "Produktionsstätte Felben-Wellhausen"),
         ("gerber.ch", "Einzelunternehmen, seit Dezember 2025, Fehraltorf", "Rolle für die Flächen 2025 offen", None, None),
     ],
     "zusatz": "Eine Betriebsnummer (" + '<span class="nr">ZH0172/ 1/700</span>' + ") mit zwei Produktionsstätten; die Zuordnung zu den Firmen ist aus den "
               "Adressen abgeleitet."},
    {"key": "rathgeb", "ort": "Unterstammheim ZH · Marke «Rathgeb Bio»",
     "bio": "ja – 547.4 ha als Bio gemeldet; alle vier Anbaufirmen Bio Suisse (Knospe)",
     "firmen": [
         ("Rathgeb BioProdukte AG", "seit 2016, Unterstammheim", "Anbau", "rathgeb-unterstammheim",
          '<span class="nr">ZH0042/ 1/850</span>, Standort Unterstammheim'),
         ("Thurtaler Gemüse AG", "Ellikon an der Thur; früher Kellermann-Gruppe, seit 2023 Rathgeb-Gruppe", "Anbau",
          "rathgeb-ellikon", '<span class="nr">ZH0042/ 1/850</span>, Standort Ellikon'),
         ("ThurBio AG", "Ellikon an der Thur; bis 2025 Berryfresh AG",
          "neues Gewächshaus in Ellikon, in den Daten 2025 nicht enthalten", None, None),
         ("BioFresh AG", "seit 2005, Tägerwilen TG", "Gewächshäuser", "rathgeb-biofresh", '<span class="nr">TG39621</span>'),
     ],
     "zusatz": "Weitere Firmen der Gruppe ohne zugeordnete Flächen: Rathgeb Holding AG, Rathgeb BioLog AG (Handel), "
               "Rathgeb Natura AG, kellermann.ch ag (Verarbeitung), Purnatur AG (Tomaten, 2024 nicht bio-zertifiziert)."},
]


def daten():
    nf = gpd.read_file(AUSWAHL, layer="nutzungsflaechen")
    nf = nf[nf.ist_ueberlagernd != True].copy()
    nf["teil"] = [teil_of(n, ps)["id"] for n, ps in zip(nf.betriebsnummer, nf.ps_nr)]
    nf["farm"] = [t.split("-")[0] for t in nf.teil]
    nf["bio"] = ["Bioproduktion" in programme(p) for p in nf.programm]
    nf["ha"] = nf.flaeche_m2 / 1e4
    return nf


def zahl(x, d=1):
    return f"{x:,.{d}f}".replace(",", "’")


def kulturen(d, n=6):
    werte = [(d[d.lnf_code.isin(codes)].ha.sum(), name) for codes, name in KULTUREN]
    werte = sorted([w for w in werte if w[0] >= 0.5], reverse=True)[:n]
    return " · ".join(f"{name} {zahl(v)}" for v, name in werte)


def block(b, nf):
    farm = next(f for f in FARMS if f["key"] == b["key"])
    d = nf[nf.farm == b["key"]]
    firmen = []
    for name, meta, taet, teil, wo in b["firmen"]:
        fl = f' <span class="fl">Fläche {zahl(nf[nf.teil == teil].ha.sum())} ha ({wo})</span>' if teil else ""
        firmen.append(f'<li><b>{escape(name)}</b> <span class="m">({escape(meta)})</span> – {escape(taet)}.{fl}</li>')
    zusatz = f'<p class="z">{b["zusatz"]}</p>' if b.get("zusatz") else ""
    return f"""
<section>
  <h2>{escape(farm['name'])} <span class="ort">{escape(b['ort'])}</span><span class="tot">{zahl(d.ha.sum())} ha · {len(d)} Flächen</span></h2>
  <dl>
    <dt>Bio</dt><dd>{escape(b['bio'])}</dd>
    <dt>Firmen</dt><dd><ul>{''.join(firmen)}</ul>{zusatz}</dd>
    <dt>Kulturen (ha)</dt><dd>{kulturen(d)}</dd>
  </dl>
</section>"""


def schrift(name):
    return base64.b64encode((WEB / "vendor" / "fonts" / name).read_bytes()).decode()


CSS = """
@font-face{font-family:"Plex";src:url(data:font/woff2;base64,__SANS__) format("woff2");font-weight:100 700}
@font-face{font-family:"PlexMono";src:url(data:font/woff2;base64,__MONO__) format("woff2");font-weight:400}
@page{size:A4;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
body{font-family:"Plex",sans-serif;font-size:8.7pt;line-height:1.38;color:#1a1a1a;font-variant-numeric:tabular-nums}
.page{width:210mm;height:297mm;padding:13mm 15mm 10mm;display:flex;flex-direction:column}
h1{font-size:15pt;font-weight:600;margin:0 0 1.2mm}
.sub{margin:0 0 4mm;color:#555;font-size:8.4pt}
section{border-top:.8pt solid #1a1a1a;padding:2.6mm 0 3.4mm}
h2{font-size:11pt;font-weight:600;margin:0 0 1.8mm;display:flex;align-items:baseline;gap:3mm}
h2 .ort{font-weight:400;color:#555;font-size:9pt}
h2 .tot{margin-left:auto;font-weight:600;font-size:9.5pt}
dl{display:grid;grid-template-columns:22mm 1fr;gap:.8mm 3mm;margin:0}
dt{color:#555}
dd{margin:0}
ul{margin:0;padding:0;list-style:none}
li{margin-bottom:.4mm}
.m{color:#555}
.fl{color:#555;white-space:nowrap}
.nr{font-family:"PlexMono",monospace;white-space:pre;font-size:8.4pt}
.z{margin:.8mm 0 0;color:#555}
footer{margin-top:auto;border-top:.5pt solid #999;padding-top:2mm;font-size:7.2pt;color:#555;line-height:1.45}
footer p{margin:0 0 .8mm}
"""


def html(nf):
    css = CSS.replace("__SANS__", schrift("ibm-plex-sans-latin-var.woff2")).replace("__MONO__", schrift("ibm-plex-mono-latin-400.woff2"))
    bl = "".join(block(b, nf) for b in BETRIEBE)
    return f"""<!doctype html>
<html lang="de-CH"><head><meta charset="utf-8"><title>Gemüsebetriebe – Firmen, Flächen, Bio</title><style>{css}</style></head>
<body><div class="page">
<h1>Gemüsebetriebe – Firmen, Flächen, Bio</h1>
<p class="sub">Imhof, Beerstecher, Gerber und Rathgeb · Flächen 2025 · Stand {STAND}</p>
{bl}
<footer>
  <p>Flächen: Kantone ZH, TG und SH, Landwirtschaftliche Kulturflächen, Bezugsjahr 2025 (geodienste.ch); deklarierte Nutzungsflächen
  ohne überlagernde Elemente. «Als Bio gemeldet»: Fläche mit dem Direktzahlungsprogramm Bioproduktion. Labels wie Knospe oder
  Demeter stehen nicht in den Daten; sie stammen aus Zertifikaten und Firmenangaben.</p>
  <p>Firmen: Handelsregister (Zefix, SHAB), Zertifikate, Firmenwebsites, Presse; abgerufen am {STAND}. Die Daten enthalten keine
  Firmennamen; die Zuordnung der Firmen zu Betriebsnummern und Standorten ist aus Adressen abgeleitet und nicht amtlich.</p>
</footer>
</div></body></html>"""


async def rendern(src, pdf):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 794, "height": 1123}, device_scale_factor=2)
        pg = await ctx.new_page()
        await pg.goto(src.as_uri())
        await pg.evaluate("document.fonts.ready")
        await pg.locator(".page").screenshot(path=str(ZIEL / "seite.png"))
        frei = await pg.evaluate("""(()=>{const p=document.querySelector('.page'), f=p.querySelector('footer');
            const s=[...p.querySelectorAll('section')].pop();
            return Math.round((f.getBoundingClientRect().top-s.getBoundingClientRect().bottom)/(96/25.4)*10)/10;})()""")
        print(f"frei vor der Fusszeile: {frei} mm" + ("  ZU LANG!" if frei < 0 else ""))
        if pdf:
            await pg.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
        await b.close()


if __name__ == "__main__":
    ZIEL.mkdir(parents=True, exist_ok=True)
    src = ZIEL / "uebersicht.html"
    src.write_text(html(daten()), encoding="utf-8")
    pdf = OUT / DATEI if "--pdf" in sys.argv else None
    asyncio.run(rendern(src, pdf))
    print("HTML:", src.relative_to(ROOT), "| Vorschau:", (ZIEL / "seite.png").relative_to(ROOT))
    if pdf:
        print("PDF:", pdf.relative_to(ROOT))
