"""Schritt 2: Website bauen (eine einzige HTML-Datei, funktioniert ohne Server).

Liest  work/auswahl.gpkg, web/template.html, web/vendor/leaflet/*, web/vendor/fonts/*, web/online/icon.svg
Schreibt output/<dateinamen.website>

Die Flächen werden vereinfacht (0.3 m), nach WGS84 umprojiziert und als JS-Daten eingebettet.
Leaflet und die Schriften (IBM Plex) werden inline eingebettet (kein CDN, keine Google-Server nötig).
Nur die Hintergrundkarten (swisstopo) und der Parzellen-Layer (Kanton Zürich) kommen beim Öffnen
aus dem Internet. Die Online-Fassung (GitHub Pages) baut scripts/06_online.py aus dieser Datei.
"""
import base64
import json
from urllib.parse import quote

import geopandas as gpd
import pandas as pd

from common import AUSWAHL, CFG, FARMS, NR2FARM, WEB, gemeinde, kantone_text, kulturgruppe, out_path, programme

nf = gpd.read_file(AUSWAHL, layer="nutzungsflaechen")
nf = nf[nf.ist_ueberlagernd != True].copy()          # überlagernde Elemente (z. B. Hochstammbäume) weglassen
nf["farm"] = nf.betriebsnummer.map(lambda n: NR2FARM[n]["key"])
nf["gruppe"] = [kulturgruppe(c, n) for c, n in zip(nf.lnf_code, nf.nutzung)]
nf["geometry"] = nf.geometry.simplify(0.3, preserve_topology=True)
pts = nf.representative_point()                       # liegt sicher in der Fläche
nf["x"] = pts.x.round(0).astype(int)
nf["y"] = pts.y.round(0).astype(int)
ll = pts.to_crs(4326)                                 # derselbe Punkt in WGS84: Route, Link zur Fläche
nf["la"] = ll.y.round(6)
nf["lo"] = ll.x.round(6)
w = nf.to_crs(4326)


def rnd(c):
    if isinstance(c[0], (float, int)):
        return [round(c[0], 6), round(c[1], 6)]
    return [rnd(x) for x in c]


feats, kts = [], set()
for i, r in enumerate(w.itertuples()):
    g = r.geometry.__geo_interface__
    gname, gkt = gemeinde(r.gemeinde)
    kts.add(r.kanton)
    feats.append({"type": "Feature",
                  "geometry": {"type": g["type"], "coordinates": rnd(g["coordinates"])},
                  "properties": {"id": i, "f": r.farm, "nr": r.betriebsnummer, "k": r.nutzung, "c": int(r.lnf_code),
                                 "g": r.gruppe, "m2": int(r.flaeche_m2), "gm": gname, "kt": gkt, "p": programme(r.programm),
                                 "bb": bool(r.beitragsberechtigt),
                                 "bg": int(r.bewirtschaftungsgrad) if pd.notna(r.bewirtschaftungsgrad) else None,
                                 "j": int(r.bezugsjahr), "x": int(r.x), "y": int(r.y), "la": r.la, "lo": r.lo}})

kts = [k for k in CFG["kantone"] if k in kts]
meta = {"farms": FARMS, "stand": CFG["stand"], "groups": CFG["kulturgruppen"], "kantone": kantone_text(kts),
        "quelle": kantone_text(kts) + ", Nutzungsflächen und Bewirtschaftungseinheiten (geodienste.ch)"}
data_js = ("window.FELDDATEN=" + json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":"))
           + ";\nwindow.META=" + json.dumps(meta, ensure_ascii=False) + ";")


def font_face(family, datei, weight, stretch=None):
    b64 = base64.b64encode((WEB / "vendor" / "fonts" / datei).read_bytes()).decode("ascii")
    return ("@font-face{font-family:\"%s\";font-style:normal;font-weight:%s;%sfont-display:swap;"
            "src:url(data:font/woff2;base64,%s) format(\"woff2\")}" % (family, weight, f"font-stretch:{stretch};" if stretch else "", b64))


fonts_css = ("/* IBM Plex Sans (variabel) und IBM Plex Mono, latin. © IBM Corp., SIL Open Font License 1.1 "
             "(web/vendor/fonts/OFL.txt) */\n"
             + font_face("IBM Plex Sans", "ibm-plex-sans-latin-var.woff2", "400 600", "85% 100%") + "\n"
             + font_face("IBM Plex Mono", "ibm-plex-mono-latin-400.woff2", "400"))

namen = [f["name"] for f in FARMS]
namen_text = namen[0] if len(namen) == 1 else ", ".join(namen[:-1]) + " und " + namen[-1]
online = CFG.get("online", {})
beschreibung = online.get("beschreibung") or (
    f"Karte der landwirtschaftlichen Flächen der Betriebe {namen_text}, {CFG['stand'].split(' · ')[0]}. "
    f"Daten: {kantone_text(kts)} (geodienste.ch).")
robots = "" if online.get("suchmaschinen") else '<meta name="robots" content="noindex, nofollow">'


def attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


t = (WEB / "template.html").read_text(encoding="utf-8")
css = (WEB / "vendor/leaflet/leaflet.css").read_text(encoding="utf-8")
js = (WEB / "vendor/leaflet/leaflet.js").read_text(encoding="utf-8")
for old, new in [
    ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">',
     "<style>/* Leaflet 1.9.4 */\n" + css + "</style>"),
    ('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>',
     "<script>/* Leaflet 1.9.4, BSD-2-Clause */\n" + js + "</script>"),
    ("/*__FONTS__*/", fonts_css),
    ("/*__DATA__*/", data_js),
    ("<!--__ROBOTS__-->", robots),
    ("__ICON__", "data:image/svg+xml," + quote((WEB / "online" / "icon.svg").read_text(encoding="utf-8").strip(), safe="/:=")),
    ("__BESCHREIBUNG__", attr(beschreibung)),
    ("__TITEL__", attr(CFG["titel"])),
]:
    assert old in t, f"Platzhalter fehlt in template.html: {old[:60]}"
    t = t.replace(old, new)
assert "<!--__ONLINE__-->" in t, "Platzhalter <!--__ONLINE__--> fehlt in template.html (braucht 06_online.py)"

p = out_path("website")
p.write_text(t, encoding="utf-8")
s = nf.groupby("farm").agg(flaechen=("t_id", "count"), ha=("flaeche_m2", lambda v: round(v.sum() / 1e4, 2)))
print(s.to_string())
unbekannt = sorted({f["properties"]["gm"] for f in feats if f["properties"]["gm"].startswith("BFS")})
if unbekannt:
    print("WARNUNG – Gemeindenamen fehlen in config/gemeinden.json:", unbekannt)
print(f"{len(feats)} Flächen, {round(len(t.encode()) / 1e6, 2)} MB -> output/{p.name}")
