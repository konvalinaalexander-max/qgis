"""Rendert die QGIS-Anleitungen (HTML -> PDF) mit Chromium/Playwright.

Aufruf:  python anleitungen/render.py            (beide)
         python anleitungen/render.py mac        (nur Mac)
Benötigt: playwright (+ chromium), pypdf. Schriften liegen in anleitungen/fonts/.
Die erste Seite (Titelblatt) wird ohne Fusszeile gerendert, alle weiteren mit Fusszeile.
Vor dem Rendern: Inhalte fact-checken (siehe CLAUDE.md, Arbeitsweise) und «Stand»-Datum anpassen.
"""
import asyncio
import sys
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter

HERE = Path(__file__).resolve().parent
STAND = "28.09.2026"
JOBS = {
    "windows": ("anleitung_windows.html", "QGIS_Anleitung_Geodaten_Landwirtschaft_ZH.pdf",
                "QGIS-Anleitung · Landwirtschaftliche Geodaten Kanton Zürich",
                "Schritt-für-Schritt-Anleitung QGIS 3.44 LTR"),
    "mac": ("anleitung_mac.html", "QGIS_Anleitung_Mac_Geodaten_Landwirtschaft_ZH.pdf",
            "QGIS-Anleitung · Landwirtschaftliche Geodaten Kanton Zürich · Ausgabe macOS",
            "Schritt-für-Schritt-Anleitung QGIS 3.44 LTR für macOS"),
}


async def render(src, out, footer_text, subject):
    footer = f"""
<div style="font-family:Helvetica,Arial,sans-serif;font-size:7.5pt;color:#56615b;width:100%;padding:0 17mm;display:flex;justify-content:space-between;">
  <span>{footer_text} · Stand {STAND}</span>
  <span>Seite <span class="pageNumber"></span> / <span class="totalPages"></span></span>
</div>"""
    with tempfile.TemporaryDirectory() as tmp:
        full, cover = Path(tmp) / "full.pdf", Path(tmp) / "cover.pdf"
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page()
            await pg.goto((HERE / src).as_uri(), wait_until="networkidle")
            await pg.evaluate("document.fonts.ready")
            await pg.pdf(path=str(full), format="A4", print_background=True, prefer_css_page_size=True,
                         display_header_footer=True, header_template="<div></div>", footer_template=footer)
            await pg.pdf(path=str(cover), format="A4", print_background=True, prefer_css_page_size=True, page_ranges="1")
            await b.close()
        w = PdfWriter()
        w.add_page(PdfReader(cover).pages[0])
        for page in PdfReader(full).pages[1:]:
            w.add_page(page)
        w.add_metadata({"/Title": "QGIS für den Betrieb – Landwirtschaftliche Geodaten Kanton Zürich",
                        "/Subject": subject, "/Author": "Alex"})
        with open(HERE / out, "wb") as f:
            w.write(f)
        print(HERE / out, len(w.pages), "Seiten")


wahl = sys.argv[1:] or list(JOBS)
for k in wahl:
    asyncio.run(render(*JOBS[k]))
