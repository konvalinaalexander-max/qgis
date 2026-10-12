"""Schritt 15: AdR-Regionen («Aus der Region», Migros) als Flächen und Anteile je Betrieb.

Die Regionsdefinitionen (öffentlich, von der Migros) liegen als Excel-Dateien in data/adr/ (früher data/intern/adr/;
eine Datei je Region, je Zeile PLZ und Ort; nicht im Git). Der Regionsname ist der Dateiname ohne den Teil, den alle Dateinamen gemeinsam haben. Jede Zeile
wird auf die amtlichen PLZ-Gebiete (Ortschaftenverzeichnis swisstopo) abgebildet: eine PLZ mit einem Gebiet ->
dieses; mehrere Gebiete -> die mit passendem Ortsnamen, sonst alle; «NNxx» -> NN00–NN99; PLZ ohne Gebiet
(Postfach u. ä.) -> Gemeinde gleichen Namens. Ortschaften einer gelisteten PLZ, die in keiner Liste mit eigenem
Namen vorkommen, gehören zur Region, die die PLZ führt. Regionen können sich überschneiden – die Anteile eines
Betriebs ergeben dann zusammen mehr als 100 %. Flächen im Ausland liegen in keiner Region.

Liest  data/adr/*.xls(x), data/basis/ (PLZ-Gebiete, Gemeindegrenzen), work/betriebe.gpkg (Schritt 13)
Schreibt work/adr.gpkg: regionen, plz;  work/adr_anteile.csv: betriebsnummer, region, ha, anteil (je Region; eine
         Fläche in mehreren Regionen zählt für jede);  work/adr_kombi.csv: betriebsnummer, regionen (Kombination, mit
         « + » verbunden, «(keine)» ausserhalb), ha, anteil – zusammen 100 %
"""
import os
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

from common import BASIS, BETRIEBE, INTERN, ROOT, WORK

QUELLE = next((d for d in (ROOT / "data" / "adr", INTERN / "adr") if list(d.glob("*.xls*"))), ROOT / "data" / "adr")
dateien = sorted(QUELLE.glob("*.xls*"))
if not dateien:
    raise SystemExit(f"Keine Regionsdefinitionen in {QUELLE} – Excel-Dateien der Migros dorthin legen (nicht ins Git).")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


_STAEMME = [Path(p).stem for p in dateien]
_GEMEINSAM = os.path.commonprefix(_STAEMME) if len(_STAEMME) > 1 else ""
_GEMEINSAM = _GEMEINSAM[:len(_GEMEINSAM) - len(_GEMEINSAM.split(" ")[-1])] if " " in _GEMEINSAM else ""


def region_name(p):
    n = Path(p).stem[len(_GEMEINSAM):]
    n = re.sub(r"_(de|fr|it)$", "", n).replace("_", " ").strip()
    return re.sub(r"\s+", " ", n)


ovz = BASIS / "ortschaftenverzeichnis_plz_2056.shp" / "AMTOVZ_SHP_LV95"
plz = gpd.read_file(ovz / "AMTOVZ_ZIP.shp")[["ZIP_ID", "ZIP4", "ADDITIONAL", "FK_LOCALIT", "geometry"]]
plz = plz.set_crs(2056, allow_override=True)  # LV95 (Shapefile-Definition leicht anders benannt)
orte = gpd.read_file(ovz / "AMTOVZ_LOCALITY.shp", ignore_geometry=True)[["LOCALITYID", "NAME"]]
plz = plz.merge(orte, left_on="FK_LOCALIT", right_on="LOCALITYID", how="left")
plz["ZIP4"] = plz.ZIP4.astype(int)
plz["ort_norm"] = plz.NAME.map(norm)
# Ersatz für Zeilen ohne PLZ-Gebiet (Postfach-PLZ, Büsingen): Gemeinde gleichen Namens (swissBOUNDARIES3D)
grenzen = next(BASIS.glob("swissboundaries3d_*_2056_5728.gpkg/*.gpkg"))
gem = gpd.read_file(grenzen, layer="tlm_hoheitsgebiet", columns=["bfs_nummer", "name"])
gem["geometry"] = shapely.force_2d(gem.geometry.values)  # swissBOUNDARIES3D hat Höhen (3D)
gem = gem.dissolve(by="name").reset_index()
gem["ort_norm"] = gem.name.map(norm)
gem["ZIP_ID"] = "G" + gem.bfs_nummer.astype(str)
gem["ZIP4"], gem["NAME"] = 0, gem.name
plz = pd.concat([plz, gem[["ZIP_ID", "ZIP4", "NAME", "ort_norm", "geometry"]]], ignore_index=True)
nach_plz = plz[plz.ZIP4 > 0].groupby("ZIP4").groups
gemeinde_nach_name = {}
for i, o in plz[plz.ZIP4 == 0].ort_norm.items():
    gemeinde_nach_name.setdefault(o, []).append(i)

zuordnung, stand, offen = [], {}, {}
mit_name, gelistet = set(), []  # Gebiete, die irgendwo mit eigenem Ortsnamen stehen; (Region, PLZ)
for p in dateien:
    reg = region_name(p)
    roh = pd.read_excel(p, header=None, dtype=str).fillna("")
    kopf = next(i for i, r in roh.iterrows() if re.match(r"^(PLZ|CP|NPA)$", r.iloc[0].strip(), re.I))
    stand[reg] = next((c for c in roh.iloc[:kopf, 0] if "gültig" in c.lower() or "stand" in c.lower()), "")
    n_ok, fehlt = 0, []
    for _, r in roh.iloc[kopf + 1:].iterrows():
        code, ort = r.iloc[0].strip(), r.iloc[1].strip()
        if not code:
            continue
        if re.fullmatch(r"\d{2}xx", code, re.I):
            treffer = plz[(plz.ZIP4 // 100) == int(code[:2])].index
        elif re.fullmatch(r"\d{4}(\.0)?", code):
            kand = nach_plz.get(int(code[:4]), [])
            o = norm(ort)
            passend = [i for i in kand if plz.ort_norm[i] and (plz.ort_norm[i] in o or o.startswith(plz.ort_norm[i]) or o in plz.ort_norm[i])]
            treffer = passend or list(kand)
            mit_name.update(plz.ZIP_ID[i] for i in passend)
            gelistet.append((reg, int(code[:4])))
            if not treffer:  # PLZ ohne Gebiet: Gemeinde gleichen Namens (z. B. «Büsingen», «Winterthur»)
                o2 = re.sub(r"\b(zh|tg|sh|sg|ag|lu|be|so|bl|bs|fr|vd|ne|ge|vs|ju|zg|sz|gl|ur|ow|nw|ai|ar|gr|ti)\b", "", o).strip()
                treffer = gemeinde_nach_name.get(o2, []) or gemeinde_nach_name.get(o2 + " am hochrhein", [])
        else:
            treffer = []
        if len(treffer) == 0:
            fehlt.append(f"{code} {ort}")
            continue
        n_ok += 1
        zuordnung += [(reg, plz.ZIP_ID[i]) for i in treffer]
    offen[reg] = fehlt
    print(f"{reg:<32} {n_ok:>4} Zeilen zugeordnet, {len(fehlt):>3} ohne PLZ-Gebiet (z. B. Postfach-PLZ)  [{stand[reg]}]")

# Ortschaften ohne eigenen Listeneintrag zur Region ihrer PLZ
for reg, nr in set(gelistet):
    zuordnung += [(reg, plz.ZIP_ID[i]) for i in nach_plz.get(nr, []) if plz.ZIP_ID[i] not in mit_name]
z = pd.DataFrame(zuordnung, columns=["region", "ZIP_ID"]).drop_duplicates()
plz_reg = plz.merge(z, on="ZIP_ID")
regionen = plz_reg.dissolve(by="region").reset_index()[["region", "geometry"]]
regionen["geometry"] = regionen.geometry.buffer(0).simplify(40)
regionen["stand"] = regionen.region.map(stand)
regionen["km2"] = (regionen.area / 1e6).round()
ziel = WORK / "adr.gpkg"
if ziel.exists():
    ziel.unlink()
regionen.to_file(ziel, layer="regionen", driver="GPKG")
plz_reg.groupby("ZIP_ID").agg(ZIP4=("ZIP4", "first"), NAME=("NAME", "first"), regionen=("region", lambda s: "; ".join(sorted(set(s)))),
                               geometry=("geometry", "first")).pipe(gpd.GeoDataFrame, crs=2056).to_file(ziel, layer="plz", driver="GPKG")

# --- Anteile je Betrieb (Lage des Flächenpunkts im PLZ-Gebiet)
fl = gpd.read_file(BETRIEBE, layer="flaechen", columns=["betriebsnummer", "flaeche_m2"])
punkte = gpd.GeoDataFrame(fl[["betriebsnummer", "flaeche_m2"]], geometry=fl.geometry.representative_point(), crs=2056)
j = gpd.sjoin(punkte, plz_reg[["ZIP_ID", "region", "geometry"]], how="inner", predicate="within")
# eine Fläche zählt je Region nur einmal (Ersatz-Gemeindeflächen überdecken PLZ-Gebiete derselben Region)
j = j[~pd.Index(list(zip(j.index, j.region))).duplicated()]
ha_reg = j.groupby(["betriebsnummer", "region"]).flaeche_m2.sum().div(1e4).rename("ha").reset_index()
total = fl.groupby("betriebsnummer").flaeche_m2.sum().div(1e4)
# Fläche in keiner Region (Region «(keine)»)
in_einer = fl.index.isin(j.index)
keine = fl[~in_einer].groupby("betriebsnummer").flaeche_m2.sum().div(1e4).rename("ha").reset_index().assign(region="(keine)")
ha_reg = pd.concat([ha_reg, keine[keine.ha > 0]], ignore_index=True)
ha_reg["anteil"] = (ha_reg.ha / ha_reg.betriebsnummer.map(total)).round(4)
ha_reg["ha"] = ha_reg.ha.round(2)
ha_reg.to_csv(WORK / "adr_anteile.csv", index=False)
# Aufteilung ohne Doppelzählung: je Fläche die Kombination ihrer Regionen (zusammen 100 %)
kombi_fl = j.groupby(level=0).region.agg(lambda s: " + ".join(sorted(set(s)))).reindex(fl.index).fillna("(keine)")
kombi = fl.assign(regionen=kombi_fl).groupby(["betriebsnummer", "regionen"]).flaeche_m2.sum().div(1e4).rename("ha").reset_index()
kombi["anteil"] = (kombi.ha / kombi.betriebsnummer.map(total)).round(4)
kombi["ha"] = kombi.ha.round(2)
kombi.to_csv(WORK / "adr_kombi.csv", index=False)
assert (kombi.groupby("betriebsnummer").anteil.sum() - 1).abs().max() < 0.01, "Aufteilung ergibt nicht 100 %"
for reg, f in offen.items():
    if f:
        print(f"  {reg} ohne PLZ-Gebiet: {', '.join(f[:12])}")
print(f"{len(regionen)} Regionen -> {ziel}; Anteile für {ha_reg.betriebsnummer.nunique()} Betriebe -> {WORK / 'adr_anteile.csv'}")
