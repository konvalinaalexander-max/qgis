"""Schritt 16: Website «Feldkarte» bauen – alle Flächen im Gebiet, ein Klick zeigt den ganzen Betrieb.

Liest  work/betriebe.gpkg (Schritt 13), web/karte/ (Vorlage), web/vendor/ (MapLibre, PMTiles, Schriften)
       vertraulich, nur mit Passwort: data/intern/namen.csv (Schritt 14), work/adr.gpkg + work/adr_anteile.csv (Schritt 15)
Schreibt output/karte/
  index.html, app.js, app.css, vendor/   die Website (statisch, braucht einen Webserver mit Range-Anfragen:
                                         GitHub Pages oder lokal scripts/server.py)
  flaechen-<Kennung>.pmtiles   Vektorkacheln aller Flächen der Betriebe, Zoom 12–14 (Layer «f»: p Fläche, i Betrieb,
                     g Kulturgruppe, k LNF-Code, m m², b Bio, gm Gemeinde)
  grob-<Kennung>.pmtiles       Übersicht für Zoom 10–11: Flächen ab 0.3 ha, vereinfacht (p, i, g)
                     Kennung = Fingerabdruck des Inhalts (auch in index.html und betriebe.json): Kacheln und
                     betriebe.json passen so immer zusammen, ältere Kacheldateien werden gelöscht.
  betriebe.json      ein Eintrag je Betrieb: Betriebsnummer, Adresse (ohne Personenangaben), Gemeinde, Kennzahlen,
                     Favoriten aus der Konfiguration – keine Namen (auch nicht die Bezeichnung der Kantonsdaten)
  intern.bin         verschlüsselt (scripts/intern.py): Namen mit Quellen (inkl. Bezeichnung der Kantonsdaten) und die
                     internen Regionen samt Anteilen je Betrieb. Nur wenn FELDKARTE_PASSWORT gesetzt ist (≥ 16 Zeichen).
"""
import gzip
import hashlib
import json
import os
import shutil

import geopandas as gpd
import pandas as pd
import pyogrio
import shapely

from common import BETRIEBE, CFG, FARMS, GROUP_COLORS, GROUPS, INTERN, OUT, WEB, WORK, teile
from intern import verschluesseln

import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--schnell", action="store_true", help="Vektorkacheln nicht neu schreiben, wenn sie zum Inhalt passen")
args = ap.parse_args()
ZIEL = OUT / "karte"
(ZIEL / "vendor").mkdir(parents=True, exist_ok=True)

bt = gpd.read_file(BETRIEBE, layer="betriebe").sort_values(["kanton_sitz", "betriebsnummer"]).reset_index(drop=True)
fl = gpd.read_file(BETRIEBE, layer="flaechen")
IDX = {nr: i for i, nr in enumerate(bt.betriebsnummer)}

# --- Nachschlagetabellen
gemeinden = sorted(set(fl.gemeinde_name.dropna()) | set(bt.gemeinde.dropna()))
GEM = {g: i for i, g in enumerate(gemeinden)}
lnf = fl.groupby("lnf_code").nutzung.first().to_dict()
favoriten = []
for f in FARMS:
    nrs = [IDX[n] for n in f["nrs"] if n in IDX]
    favoriten.append({"key": f["key"], "name": f["name"], "sub": f.get("sub", ""), "color": f["color"], "i": nrs,
                      "note": f.get("note", ""),
                      "teile": [{"name": t["name"], "kurz": t["kurz"], "color": t["color"], "bio": t.get("bio_text", "")}
                                for t in teile(f)]})
fav_von = {i: f["key"] for f in favoriten for i in f["i"]}


def r2(x):
    return round(float(x), 2)


AQ = {"Kantonsdaten (betriebsname)": 0, "nächste Gebäudeadresse (amtl. Verzeichnis)": 1}
SQ = {"amtlich": 0, "Produktionsstätte": 1, "Adresse (amtlich verortet)": 2, "grösste eigene Fläche (Standort fehlt)": 3}
eintraege = []
for r in bt.itertuples():
    bbox = [round(float(v), 5) for v in r.bbox.split(",")]
    eintraege.append([
        r.betriebsnummer, r.kanton_sitz, SQ.get(r.standort_quelle, 0), r.adresse or "", AQ.get(r.adresse_quelle, -1),
        int(r.adresse_dist_m), r.gemeinde or "",
        round(r.lon, 5), round(r.lat, 5), int(r.n_flaechen), r2(r.ha), r2(r.ha_gebiet), r2(r.ha_bio),
        [r2(getattr(r, f"ha_g{g}")) for g in range(len(GROUPS))], bbox, fav_von.get(IDX[r.betriebsnummer], ""),
        r.gemeinden or "", int(r.dist_flaeche_m) if pd.notna(r.dist_flaeche_m) else -1,
        r.produktionsstaetten or "", int(r.bezugsjahr),
    ])
gebiet = gpd.read_file(WORK / "region.gpkg", layer="gebiet").set_index("name").to_crs(4326).geometry["gebiet"]
meta = {
    "titel": CFG["titel"], "stand": CFG["stand"], "jahr": CFG["region"]["bezugsjahr"],
    "gruppen": [[g, GROUP_COLORS[g]] for g in GROUPS], "lnf": {int(k): v for k, v in lnf.items()},
    "gemeinden": gemeinden, "favoriten": favoriten,
    "gebiet": [round(v, 4) for v in gebiet.bounds], "puffer_km": CFG["region"]["puffer_km"],
    "kantone": sorted(set(bt.kanton_sitz)),
    "felder": ["nr", "kt", "sq", "adresse", "aq", "ad", "gemeinde", "lon", "lat", "n", "ha", "ha_gebiet", "ha_bio",
               "gruppen_ha", "bbox", "favorit", "gemeinden", "dist_flaeche_m", "produktionsstaetten", "jahr"],
}

# --- Vektorkacheln
GRUPPE = {g: i for i, g in enumerate(GROUPS)}
kacheln = gpd.GeoDataFrame({
    "p": pd.RangeIndex(len(fl)).astype("int32"),
    "i": fl.betriebsnummer.map(IDX).astype("int32"),
    "g": fl.gruppe.map(GRUPPE).astype("int16"),
    "k": fl.lnf_code.astype("int32"),
    "m": fl.flaeche_m2.round().astype("int32"),
    "b": fl.bio.astype("int16"),
    "gm": fl.gemeinde_name.map(GEM).fillna(-1).astype("int32"),
}, geometry=fl.geometry.values, crs=2056).to_crs(3857)
def kacheln_schreiben(df, pfad, layer, zmin, zmax, simpl):
    tmp = pfad.with_name(pfad.stem + ".tmp.pmtiles")  # erst nach Erfolg umbenennen (--schnell prüft nur den Namen)
    tmp.unlink(missing_ok=True)
    pyogrio.write_dataframe(df, tmp, layer=layer, driver="PMTiles",
                            dataset_options={"MINZOOM": str(zmin), "MAXZOOM": str(zmax), "NAME": "Feldkarte Flächen",
                                             "DESCRIPTION": f"Landwirtschaftliche Kulturflächen {CFG['region']['bezugsjahr']}, geodienste.ch",
                                             "MAX_SIZE": "2000000", "MAX_FEATURES": "400000", "SIMPLIFICATION": str(simpl),
                                             "SIMPLIFICATION_MAX_ZOOM": "0.5"})
    mb = tmp.stat().st_size / 1e6
    print(f"Vektorkacheln {pfad.name}: {len(df)} Flächen, Zoom {zmin}–{zmax} ({mb:.1f} MB)")
    if mb > 95:
        raise SystemExit(f"{pfad.name} ist grösser als 95 MB – GitHub nimmt höchstens 100 MB je Datei an (Gebiet verkleinern).")
    if mb > 50:
        print(f"WARNUNG: {pfad.name} > 50 MB (GitHub warnt ab 50 MB, Grenze 100 MB)")
    tmp.replace(pfad)


# Kennung der Kacheln: Fingerabdruck von allem, was in ihnen steht (Attribute, Geometrien), und von dem, worauf ihre
# Zahlen zeigen (i = Reihenfolge der Betriebe, gm = Gemeinden, g = Kulturgruppen). Sie steht im Dateinamen: Eine noch
# offene Seite mit älterer betriebe.json findet nach einem Update ihre Kacheln nicht mehr und meldet «Neu laden»,
# statt still fremde Betriebe zu zeigen. KACHELN_V erhöhen, wenn sich die Kachel-Parameter unten ändern.
KACHELN_V = "3|f 12-14 s1|g 10-11 s2 >=3000 m2 v8"
h = hashlib.sha256(KACHELN_V.encode())
h.update(json.dumps([list(bt.betriebsnummer), gemeinden, GROUPS], ensure_ascii=False).encode())
h.update(pd.util.hash_pandas_object(pd.DataFrame(kacheln.drop(columns="geometry")), index=False).values.tobytes())
h.update(hashlib.sha256(b"".join(shapely.to_wkb(fl.geometry.values))).digest())
KENNUNG = h.hexdigest()[:12]
pm, grob = ZIEL / f"flaechen-{KENNUNG}.pmtiles", ZIEL / f"grob-{KENNUNG}.pmtiles"
if args.schnell and pm.exists() and grob.exists():
    print(f"Vektorkacheln passen zum Inhalt, behalten ({(pm.stat().st_size + grob.stat().st_size) / 1e6:.1f} MB)")
else:
    # ab Zoom 12: alle Flächen mit Angaben; Zoom 10–11: Übersicht (Flächen ab 0.3 ha, vereinfacht, nur Betrieb + Kultur)
    kacheln_schreiben(kacheln, pm, "f", 12, 14, 1)
    gr = fl.flaeche_m2 >= 3000
    kacheln_schreiben(gpd.GeoDataFrame(kacheln.loc[gr.values, ["p", "i", "g"]], geometry=fl.geometry[gr].simplify(8).values, crs=2056)
                      .to_crs(3857), grob, "f", 10, 11, 2)
meta["kacheln"] = KENNUNG
(ZIEL / "betriebe.json").write_text(json.dumps({"meta": meta, "b": eintraege}, ensure_ascii=False, separators=(",", ":")),
                                    encoding="utf-8")
for alt in [*ZIEL.glob("*.pmtiles"), ZIEL / "kacheln.txt"]:
    if alt not in (pm, grob) and alt.exists():
        alt.unlink()
        print(f"alte Datei gelöscht: {alt.name}")

# --- Vertraulicher Teil (Namen, interne Regionen)
pw = os.environ.get("FELDKARTE_PASSWORT", "")
if pw:
    intern = {"namen": {}, "adr": None}
    nf = INTERN / "namen.csv"
    if nf.exists():
        n = pd.read_csv(nf, dtype=str).fillna("")
        for z in n.itertuples():
            if z.betriebsnummer in IDX:
                intern["namen"].setdefault(IDX[z.betriebsnummer], []).append(
                    [z.art, z.name, z.person, z.detail, z.quelle, z.url, z.sicherheit, int(float(z.abstand_m or 0))])
    if (WORK / "adr.gpkg").exists():
        reg = gpd.read_file(WORK / "adr.gpkg", layer="regionen").to_crs(4326)
        reg["geometry"] = reg.geometry.simplify(0.0004)
        namen_reg = list(reg.region)
        geo = json.loads(reg[["region", "stand", "geometry"]].to_json(drop_id=True))
        for i, ft in enumerate(geo["features"]):
            ft["properties"]["r"] = i
        anteile = {}
        a = pd.read_csv(WORK / "adr_anteile.csv")
        for z in a.itertuples():
            if z.betriebsnummer in IDX:
                r = -1 if z.region == "(keine)" else namen_reg.index(z.region)
                anteile.setdefault(IDX[z.betriebsnummer], []).append([r, z.ha, z.anteil])
        intern["adr"] = {"regionen": namen_reg, "geojson": geo, "anteile": anteile}
    roh = gzip.compress(json.dumps(intern, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9)
    (ZIEL / "intern.bin").write_bytes(verschluesseln(roh, pw))
    print(f"intern.bin: Namen für {len(intern['namen'])} Betriebe, Regionen {'ja' if intern['adr'] else 'nein'} "
          f"({(ZIEL / 'intern.bin').stat().st_size / 1e6:.1f} MB, verschlüsselt)")
else:
    (ZIEL / "intern.bin").unlink(missing_ok=True)
    print("FELDKARTE_PASSWORT nicht gesetzt: Website ohne Namen und ohne interne Regionen.")

# --- Website-Dateien
robots = "" if CFG["online"].get("suchmaschinen") else '<meta name="robots" content="noindex, nofollow">'
html = (WEB / "karte" / "index.html").read_text(encoding="utf-8")
version = KENNUNG + hashlib.sha256((WEB / "karte" / "app.js").read_bytes() + (WEB / "karte" / "app.css").read_bytes()).hexdigest()[:6]
html = html.replace("__TITEL__", CFG["titel"]).replace("__STAND__", CFG["stand"]).replace("<!--__ROBOTS__-->", robots) \
    .replace("__VERSION__", version).replace("__KACHELN__", KENNUNG)
(ZIEL / "index.html").write_text(html, encoding="utf-8")
for name in ("app.js", "app.css"):
    shutil.copy2(WEB / "karte" / name, ZIEL / name)
for quelle, ziel in [("maplibre/maplibre-gl.js", "maplibre-gl.js"), ("maplibre/maplibre-gl.css", "maplibre-gl.css"),
                     ("maplibre/LICENSE.txt", "LICENSE-maplibre.txt"), ("pmtiles/pmtiles.js", "pmtiles.js"),
                     ("pmtiles/LICENSE", "LICENSE-pmtiles.txt"), ("fonts/ibm-plex-sans-latin-var.woff2", "plex-sans.woff2"),
                     ("fonts/ibm-plex-mono-latin-400.woff2", "plex-mono.woff2"), ("fonts/OFL.txt", "LICENSE-plex.txt")]:
    shutil.copy2(WEB / "vendor" / quelle, ZIEL / "vendor" / ziel)
groesse = sum(p.stat().st_size for p in ZIEL.rglob("*") if p.is_file())
print(f"Website -> {ZIEL} ({groesse / 1e6:.1f} MB)")
