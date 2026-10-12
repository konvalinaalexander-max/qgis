"""Schritt 6: Online-Fassung der Website zusammenstellen (für GitHub Pages oder einen anderen Webspace).

Liest  output/karte/ (Schritt 16, falls vorhanden), output/<dateinamen.website> (Schritt 2), web/online/*
Schreibt work/online/ (Standard) bzw. den Ordner aus --out:
  index.html             die Karte aller Betriebe der Region (output/karte/, Schritt 16) – fehlt sie, die Website
                         der Favoriten; ergänzt um Angaben für Handy-Startbildschirm und Link-Vorschau
  betriebe.html          die Detailansicht der Favoriten (Schritt 2), wenn die Karte der Region die Startseite ist
  flaechen-<Kennung>.pmtiles, grob-<Kennung>.pmtiles, betriebe.json, regionen.json, app.js, app.css, vendor/,
                         intern.bin (verschlüsselt, falls gebaut)
  manifest.webmanifest   App-Name und Icons («Zum Home-Bildschirm»)
  icon-*.png, apple-touch-icon.png, vorschau.jpg (falls vorhanden)

Aufruf: python3 scripts/06_online.py [--url https://…/] [--out Ordner]
Braucht nur Python ohne Zusatzpakete. Auf GitHub erledigt das der Workflow .github/workflows/website.yml
bei jedem Push auf main. --url (öffentliche Adresse mit / am Ende) braucht es nur für die Link-Vorschau,
weil das Vorschaubild mit vollständiger Adresse angegeben werden muss.
Lokal ansehen: python3 scripts/server.py  →  http://localhost:8000 (die Vektorkacheln der Karte brauchen
Range-Anfragen; python3 -m http.server kann das nicht)
"""
import argparse
import json
import shutil
from pathlib import Path

from common import CFG, WEB, WORK, out_path

ap = argparse.ArgumentParser(description="Online-Fassung der Website zusammenstellen")
ap.add_argument("--url", default="", help="öffentliche Adresse der Website, z. B. https://name.github.io/repo/")
ap.add_argument("--out", default=str(WORK / "online"), help="Zielordner (Standard: work/online)")
args = ap.parse_args()

quelle = out_path("website")
if not quelle.exists():
    raise SystemExit(f"{quelle} fehlt – zuerst scripts/02_website.py ausführen (oder ./run_all.sh).")
html = quelle.read_text(encoding="utf-8")
assert "<!--__ONLINE__-->" in html, "Platzhalter <!--__ONLINE__--> fehlt – Website mit aktueller Vorlage neu bauen (02_website.py)."
karte = out_path("website").parent / "karte"
mit_karte = (karte / "index.html").exists()

ziel = Path(args.out).resolve()
if ziel.exists():
    shutil.rmtree(ziel)
ziel.mkdir(parents=True)

statisch = sorted(p for p in (WEB / "online").iterdir() if p.suffix in (".png", ".jpg", ".svg"))
for p in statisch:
    shutil.copy2(p, ziel / p.name)
namen = {p.name for p in statisch}

url = args.url.strip()
if url and not url.endswith("/"):
    url += "/"


def attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


kopf = ['<link rel="manifest" href="manifest.webmanifest">',
        '<link rel="apple-touch-icon" href="apple-touch-icon.png">']
if url:
    kopf.append(f'<meta property="og:url" content="{attr(url)}">')
    if "vorschau.jpg" in namen:
        kopf += [f'<meta property="og:image" content="{attr(url)}vorschau.jpg">',
                 '<meta property="og:image:width" content="1200">',
                 '<meta property="og:image:height" content="630">',
                 '<meta name="twitter:card" content="summary_large_image">']
html = html.replace("<!--__ONLINE__-->", "\n".join(kopf))
if mit_karte:
    # nur diese Dateien veröffentlichen (keine Zwischendateien abgebrochener Läufe)
    erlaubt = [karte / n for n in ("app.js", "app.css", "betriebe.json", "regionen.json", "intern.bin")]
    erlaubt += sorted(p for p in karte.glob("*.pmtiles") if p.name.startswith(("flaechen-", "grob-")) and ".tmp" not in p.name)
    erlaubt += sorted((karte / "vendor").glob("*"))
    for p in erlaubt:
        if p.is_file():
            (ziel / p.relative_to(karte)).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, ziel / p.relative_to(karte))
    start = (karte / "index.html").read_text(encoding="utf-8")
    assert "<!--__ONLINE__-->" in start, "Platzhalter <!--__ONLINE__--> fehlt in output/karte/index.html (16_karte.py)."
    (ziel / "index.html").write_text(start.replace("<!--__ONLINE__-->", "\n".join(kopf)), encoding="utf-8")
    # Detailansicht der Favoriten: Link zurück zur Karte der Region (Platzhalter in web/template.html)
    link = '<p><a href="./">← Karte der Region: alle Betriebe im Gebiet</a></p>'
    if url:   # eigene Adresse für Link-Vorschauen (sonst zeigen Dienste beim Teilen die Startseite)
        html = html.replace(f'<meta property="og:url" content="{attr(url)}">', f'<meta property="og:url" content="{attr(url)}betriebe.html">')
    (ziel / "betriebe.html").write_text(html.replace("<!--__KARTE__-->", link), encoding="utf-8")
else:
    (ziel / "index.html").write_text(html, encoding="utf-8")

manifest = {
    "name": CFG["titel"],
    "short_name": "Feldkarte",
    "description": CFG["titel"] + " · " + CFG["stand"],
    "lang": "de-CH",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "background_color": "#F5F6F2",
    "theme_color": "#2C5B45",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}
fehlend = [i["src"] for i in manifest["icons"] if i["src"] not in namen] + \
          [n for n in ["apple-touch-icon.png"] if n not in namen]
if fehlend:
    print("WARNUNG – Icons fehlen in web/online/ (scripts/icons.py):", fehlend)
(ziel / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

dateien = [p for p in ziel.rglob("*") if p.is_file()]
groesse = sum(p.stat().st_size for p in dateien)
print(f"Online-Fassung{' mit Karte der Region' if mit_karte else ''}: {len(dateien)} Dateien, {round(groesse / 1e6, 2)} MB -> {ziel}"
      + (f"  (Adresse {url})" if url else "  (ohne --url: keine Link-Vorschau)"))
