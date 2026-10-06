"""Übersicht der Betriebe als PDF auf einer A4-Seite: welche Firmen gehören dazu, Fläche, Bio oder nicht, Hauptkulturen.

Aufruf:  python scripts/uebersicht_pdf.py          -> work/uebersicht/uebersicht.html + Vorschaubild (PNG)
         python scripts/uebersicht_pdf.py --pdf    -> zusätzlich output/<dateinamen.uebersicht>
Die Zahlen kommen aus work/auswahl.gpkg (Schritt 1, gleich gerechnet wie die Website). Die Angaben zu Firmen und
Bio stehen unten in BETRIEBE (Belege: docs/betriebe.md). Vor dem PDF alles fact-checken (CLAUDE.md, Arbeitsweise).
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
            ((611,), "extensive Wiesen"), ((612, 613), "Dauerwiesen"), ((516,), "Dinkel"),
            ((512, 513, 514, 515), "Weizen"), ((508, 521), "Mais"), ((551,), "Beeren"),
            ((801, 802, 803, 804, 807, 808, 811, 812, 813, 814, 847, 848, 849), "Gewächshaus")]

# Bio-Kennzeichen: Text und CSS-Klasse
BIO = {"ja": "Bio", "nein": "nicht Bio", "firma": "Bio laut Firma¹", "offen": "unklar"}

# Je Betrieb: Status gesamt, Kurzbeschrieb, Betriebsnummern mit den Firmen darin, Firmen ohne eigene Betriebsnummer.
# Firma: (Name, was sie macht, Teil-ID für die Fläche, Bio)
BETRIEBE = [
    {"key": "imhof", "ort": "Schwerzenbach ZH", "status": "ja", "was": "Bio-Gemüse (Demeter), Topfkräuter, Zierpflanzen",
     "nummern": [("ZH0197/ 1/  1", [("Hansjürg Imhof Bio-Produkte", "Bio-Gemüse", "imhof-haupt", "ja")]),
                 ("ZH0197/ 1/702", [("Imhof Flora AG", "Beet- und Balkonpflanzen, Gewächshaus", "imhof-gewaechshaus", "nein")])],
     "weitere": [("Imhofbio AG", "Topfkräuter, Handel", "ja")]},
    {"key": "beerstecher", "ort": "Dübendorf ZH", "status": "nein", "was": "Gemüse, Salate und Beeren, konventionell",
     "nummern": [("ZH0191/ 1/ 55", [("Beerstecher AG", "Gemüse, Salate, Beeren", "beerstecher", "nein")])]},
    {"key": "gerber", "ort": "Fehraltorf ZH · Felben-Wellhausen TG", "status": "firma", "was": "Bio-Gemüse und konventionelles Gemüse",
     "nummern": [("ZH0172/ 1/700", [("Gerber Bio Greens AG", "Bio-Gemüse, Fehraltorf", "gerber-biogreens", "firma"),
                                    ("Gerber Gemüsebau AG", "Gemüse, Thurtal", "gerber-gemuesebau", "nein")])]},
    {"key": "rathgeb", "ort": "Unterstammheim ZH", "status": "ja", "was": "Marke «Rathgeb Bio»",
     "nummern": [("ZH0042/ 1/850", [("Rathgeb BioProdukte AG", "Anbau, Unterstammheim", "rathgeb-unterstammheim", "ja"),
                                    ("Thurtaler Gemüse AG", "Anbau, Ellikon an der Thur", "rathgeb-ellikon", "ja")]),
                 ("TG39621", [("BioFresh AG", "Gewächshäuser, Tägerwilen", "rathgeb-biofresh", "ja")])],
     "weitere": [("ThurBio AG", "neues Gewächshaus Ellikon²", "ja")]},
]
STATUS = {"ja": "Bio", "nein": "nicht Bio", "firma": "teils Bio"}


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


def kulturen(d, n=3):
    werte = sorted(((d[d.lnf_code.isin(c)].ha.sum(), name) for c, name in KULTUREN), reverse=True)[:n]
    return "".join(f"<li>{name} <b>{zahl(v, 0)} ha</b></li>" for v, name in werte)


def firma(name, was, bio, ha=None):
    fl = f'<span class="fha">{ha}</span>' if ha else ""
    return (f'<div class="firma b-{bio}"><div class="fz"><b>{escape(name)}</b>{fl}</div>'
            f'<div class="fw">{escape(was)} · <span class="fb">{escape(BIO[bio])}</span></div></div>')


def block(b, nf):
    farm = next(f for f in FARMS if f["key"] == b["key"])
    d = nf[nf.farm == b["key"]]
    nummern = []
    for nr, firmen in b["nummern"]:
        fs = "".join(firma(n, w, bio, f"{zahl(nf[nf.teil == t].ha.sum())} ha") for n, w, t, bio in firmen)
        nummern.append(f'<div class="nummer"><div class="nk">Betriebsnummer <span>{escape(nr)}</span></div><div class="fs">{fs}</div></div>')
    weitere = ""
    if b.get("weitere"):
        weitere = ('<div class="weitere"><div class="nk">weitere Firmen, ohne zugeordnete Betriebsnummer</div><div class="fs">' +
                   "".join(firma(n, w, bio) for n, w, bio in b["weitere"]) + "</div></div>")
    return f"""
<section>
  <div class="links">
    <h2>{escape(farm['name'])}</h2>
    <div class="ort">{escape(b['ort'])}</div>
    <div class="tot">{zahl(d.ha.sum())} ha <span class="st s-{b['status']}">{STATUS[b['status']]}</span></div>
    <div class="was">{escape(b['was'])}</div>
    <ul class="ku">{kulturen(d)}</ul>
  </div>
  <div class="rechts">{''.join(nummern)}{weitere}</div>
</section>"""


def schrift(name):
    return base64.b64encode((WEB / "vendor" / "fonts" / name).read_bytes()).decode()


CSS = """
@font-face{font-family:"Plex";src:url(data:font/woff2;base64,__SANS__) format("woff2");font-weight:100 700}
@font-face{font-family:"PlexMono";src:url(data:font/woff2;base64,__MONO__) format("woff2");font-weight:400}
@page{size:A4;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
body{font-family:"Plex",sans-serif;font-size:9.1pt;line-height:1.32;color:#1d1d1d;font-variant-numeric:tabular-nums;
  -webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{width:210mm;height:297mm;padding:12mm 15mm 9mm;display:flex;flex-direction:column}
h1{font-size:17pt;font-weight:600;margin:0}
.sub{margin:1mm 0 3.5mm;color:#666}
.leg{display:flex;gap:5mm;font-size:8.4pt;color:#555;margin-bottom:3.5mm;align-items:center}
.leg span{display:inline-flex;align-items:center;gap:1.6mm}
.leg i{width:4mm;height:3mm;border-radius:.6mm;display:inline-block}
.leg .box{width:6mm;height:3.4mm;border:.8pt solid #999;border-radius:.8mm;background:#fff}
section{display:grid;grid-template-columns:46mm 1fr;gap:5mm;border-top:1pt solid #1d1d1d;padding:2.6mm 0 3.2mm}
h2{font-size:14pt;font-weight:600;margin:0;line-height:1.1}
.ort{color:#666;margin-top:.6mm}
.tot{font-size:12.5pt;font-weight:600;margin-top:1.6mm}
.st{display:inline-block;margin-left:1.5mm;padding:.2mm 2mm;border-radius:1mm;font-weight:600;font-size:8.8pt;vertical-align:2pt}
.st.s-ja{background:#dcf2e3;color:#14632f}
.st.s-nein{background:#fbe6d2;color:#8a3d0a}
.st.s-firma{background:#eef3d9;color:#4a5a12}
.was{color:#555;margin-top:1.4mm;font-size:8.6pt}
.ku{list-style:none;margin:1.4mm 0 0;padding:0;font-size:8.6pt;color:#555}
.ku b{color:#1d1d1d;font-weight:500}
.rechts{display:flex;flex-direction:column;gap:1.6mm}
.nummer{border:.8pt solid #9a9a9a;border-radius:1.4mm;padding:1.3mm 1.8mm 1.8mm}
.weitere{border:.8pt dashed #b5b5b5;border-radius:1.4mm;padding:1.3mm 1.8mm 1.8mm}
.nk{font-size:8.2pt;color:#666;margin-bottom:1.1mm}
.nk span{font-family:"PlexMono",monospace;white-space:pre;color:#1d1d1d;font-size:9pt}
.fs{display:flex;gap:2mm}
.firma{flex:1;border-radius:1mm;padding:1mm 2.2mm 1.1mm;border-left:2.2mm solid}
.firma.b-ja{background:#eaf7ee;border-color:#2e9e57}
.firma.b-firma{background:#eef6e4;border-color:#8cc06a}
.firma.b-nein{background:#fdf1e6;border-color:#e08a3c}
.firma.b-offen{background:#f1f1f1;border-color:#a8a8a8}
.fz{display:flex;justify-content:space-between;gap:2mm;align-items:baseline}
.fz b{font-weight:600}
.fha{font-weight:600;white-space:nowrap}
.fw{color:#555;font-size:8.4pt;margin-top:.3mm}
.fb{font-weight:600}
.b-ja .fb,.b-firma .fb{color:#14632f}
.b-nein .fb{color:#8a3d0a}
.b-offen .fb{color:#555}
footer{margin-top:auto;border-top:.5pt solid #bbb;padding-top:1.8mm;font-size:7.6pt;color:#666;line-height:1.5}
footer p{margin:0 0 .8mm}
"""


def html(nf):
    css = CSS.replace("__SANS__", schrift("ibm-plex-sans-latin-var.woff2")).replace("__MONO__", schrift("ibm-plex-mono-latin-400.woff2"))
    bl = "".join(block(b, nf) for b in BETRIEBE)
    return f"""<!doctype html>
<html lang="de-CH"><head><meta charset="utf-8"><title>Gemüsebetriebe – Firmen, Flächen, Bio</title><style>{css}</style></head>
<body><div class="page">
<h1>Vier Gemüsebetriebe: Firmen, Flächen, Bio</h1>
<p class="sub">Welche Firma gehört zu welcher Betriebsnummer · Flächen 2025 · Stand {STAND}</p>
<div class="leg"><span><i class="box"></i>amtliche Betriebsnummer</span><span><i style="background:#2e9e57"></i>Bio</span>
<span><i style="background:#e08a3c"></i>nicht Bio</span></div>
{bl}
<footer>
  <p>¹ Laut Firma Bio Suisse zertifiziert; in den Kantonsdaten ist keine Fläche als Bio gemeldet.
  ² In den Flächendaten 2025 nicht enthalten.</p>
  <p>Flächen: Kantonsdaten 2025 (geodienste.ch). Bio: Zertifikate (Knospe, Demeter) und Firmenangaben. Die Daten enthalten keine
  Firmennamen; welche Firma zu welcher Betriebsnummer gehört, ist aus Adressen, Handelsregister und Firmenangaben abgeleitet.</p>
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
