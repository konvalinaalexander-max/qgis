"""Schritt 6: Online-Fassung der Website zusammenstellen (für GitHub Pages oder einen anderen Webspace).

Liest  output/<dateinamen.website> (Schritt 2), web/online/*
Schreibt work/online/ (Standard) bzw. den Ordner aus --out:
  index.html             die Website aus output/, ergänzt um Angaben für Handy-Startbildschirm und Link-Vorschau
  manifest.webmanifest   App-Name und Icons («Zum Home-Bildschirm»)
  icon-*.png, apple-touch-icon.png, vorschau.jpg (falls vorhanden)

Aufruf: python3 scripts/06_online.py [--url https://…/] [--out Ordner]
Braucht nur Python ohne Zusatzpakete. Auf GitHub erledigt das der Workflow .github/workflows/website.yml
bei jedem Push auf main. --url (öffentliche Adresse mit / am Ende) braucht es nur für die Link-Vorschau,
weil das Vorschaubild mit vollständiger Adresse angegeben werden muss.
Lokal ansehen: python3 -m http.server -d work/online 8000  →  http://localhost:8000
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

groesse = sum(p.stat().st_size for p in ziel.iterdir())
print(f"Online-Fassung: {len(list(ziel.iterdir()))} Dateien, {round(groesse / 1e6, 2)} MB -> {ziel}"
      + (f"  (Adresse {url})" if url else "  (ohne --url: keine Link-Vorschau)"))
