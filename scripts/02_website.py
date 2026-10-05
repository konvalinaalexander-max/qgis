"""Schritt 2: Website bauen (eine einzige HTML-Datei, funktioniert ohne Server).

Liest  work/auswahl.gpkg, web/template.html, web/vendor/leaflet/*
Schreibt output/<dateinamen.website>

Die Flächen werden vereinfacht (0.3 m), nach WGS84 umprojiziert und als JS-Daten eingebettet.
Leaflet wird inline eingebettet (kein CDN nötig). Nur die Hintergrundkarten (swisstopo) und der
Parzellen-Layer (Kanton Zürich) kommen beim Öffnen aus dem Internet.
"""
import json

import geopandas as gpd
import pandas as pd

from common import AUSWAHL, CFG, FARMS, NR2FARM, WEB, gemeinde, kantone_text, kulturgruppe, out_path, programme

nf = gpd.read_file(AUSWAHL, layer="nutzungsflaechen")
nf = nf[nf.ist_ueberlagernd != True].copy()          # überlagernde Elemente (z. B. Hochstammbäume) weglassen
nf["farm"] = nf.betriebsnummer.map(lambda n: NR2FARM[n]["key"])
nf["gruppe"] = [kulturgruppe(c, n) for c, n in zip(nf.lnf_code, nf.nutzung)]
nf["geometry"] = nf.geometry.simplify(0.3, preserve_topology=True)
pts = nf.representative_point()
nf["x"] = pts.x.round(0).astype(int)
nf["y"] = pts.y.round(0).astype(int)
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
                                 "j": int(r.bezugsjahr), "x": int(r.x), "y": int(r.y)}})

kts = [k for k in CFG["kantone"] if k in kts]
meta = {"farms": FARMS, "stand": CFG["stand"], "groups": CFG["kulturgruppen"], "kantone": kantone_text(kts),
        "quelle": kantone_text(kts) + ", Nutzungsflächen und Bewirtschaftungseinheiten (geodienste.ch)"}
data_js = ("window.FELDDATEN=" + json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":"))
           + ";\nwindow.META=" + json.dumps(meta, ensure_ascii=False) + ";")

t = (WEB / "template.html").read_text(encoding="utf-8")
css = (WEB / "vendor/leaflet/leaflet.css").read_text(encoding="utf-8")
js = (WEB / "vendor/leaflet/leaflet.js").read_text(encoding="utf-8")
for old, new in [
    ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">',
     "<style>/* Leaflet 1.9.4 */\n" + css + "</style>"),
    ('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>',
     "<script>/* Leaflet 1.9.4, BSD-2-Clause */\n" + js + "</script>"),
    ("/*__DATA__*/", data_js),
    ("__TITEL__", CFG["titel"]),
]:
    assert old in t, f"Platzhalter fehlt in template.html: {old[:60]}"
    t = t.replace(old, new)

p = out_path("website")
p.write_text(t, encoding="utf-8")
s = nf.groupby("farm").agg(flaechen=("t_id", "count"), ha=("flaeche_m2", lambda v: round(v.sum() / 1e4, 2)))
print(s.to_string())
unbekannt = sorted({f["properties"]["gm"] for f in feats if f["properties"]["gm"].startswith("BFS")})
if unbekannt:
    print("WARNUNG – Gemeindenamen fehlen in config/gemeinden.json:", unbekannt)
print(f"{len(feats)} Flächen, {round(len(t.encode()) / 1e6, 2)} MB -> output/{p.name}")
