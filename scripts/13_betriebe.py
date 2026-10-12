"""Schritt 13: Betriebsverzeichnis für die Region – ein Eintrag je Betriebsnummer.

Liest  work/region.gpkg (Schritt 12), data/basis/ (Gemeindegrenzen, Gebäudeadressen)
Schreibt work/betriebe.gpkg mit den Layern
  betriebe  Punkt = amtlicher Betriebsstandort (Favoriten mit «standort_ps»: die Produktionsstätte); Adresse: der
            «betriebsname» der Kantonsdaten, wenn er eine Adresse ohne Personenangaben ist (ZH, AG, SG, AR …), sonst
            die nächste amtliche Gebäudeadresse am Punkt; Hofbezeichnung aus den Daten (TG/SH u. a.), Gemeinde, Flächen und ha
            (gesamt und im Gebiet), ha je Kulturgruppe, Bio-ha, Gemeinden der Flächen, Schwerpunkt der Flächen,
            Abstand Standort–Flächen, Ausdehnung (bbox, WGS84), Produktionsstätten, Favorit (config «betriebe»)
  flaechen  alle Flächen mit Kulturgruppe, Gemeinde (räumlich, Gemeindestand swissBOUNDARIES3D) und Bio-Kennzeichen
und work/betriebe.csv (dasselbe ohne Geometrie, für die Recherche).
"""
import re

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from common import (BASIS, BETRIEBE, CFG, FARMS, GROUPS, NR2FARM, REGION, WORK, adresse_key, hat_person, kulturgruppe,
                    strasse_key)

KT_NR = {1: "ZH", 2: "BE", 3: "LU", 4: "UR", 5: "SZ", 6: "OW", 7: "NW", 8: "GL", 9: "ZG", 10: "FR", 11: "SO", 12: "BS",
         13: "BL", 14: "SH", 15: "AR", 16: "AI", 17: "SG", 18: "GR", 19: "AG", 20: "TG", 21: "TI", 22: "VD", 23: "VS",
         24: "NE", 25: "GE", 26: "JU"}
ADRESSE_MAX_M = 60   # so weit darf die nächste Gebäudeadresse vom Betriebspunkt entfernt sein (sonst keine Adresse)
STRASSE_NR = r"^[^,]*\d+[a-zA-Z]?(?:\.\d+)?\s*,\s*\d{4}\s+\S"      # «Strasse 12, 8000 Ort»
# Personenangaben (c/o, z. Hd., Familie, Herr/Frau, Initiale + Name, Vorname): common.hat_person(), geprüft wird der
# ganze Text vor der letzten PLZ

fl = gpd.read_file(REGION, layer="flaechen")
bt = gpd.read_file(REGION, layer="betriebe")
ps = gpd.read_file(REGION, layer="produktionsstaetten")
print(f"{len(bt)} Betriebe, {len(fl)} Flächen")
bt["standort_quelle"] = "amtlich"
# Favoriten: Standort an einer Produktionsstätte statt an der Wohnadresse (config «standort_ps»)
for f in FARMS:
    p = ps[ps.ps_nr == f.get("standort_ps")]
    if len(p):
        k = bt.betriebsnummer == p.betriebsnummer.iloc[0]
        bt.loc[k, "geometry"] = p.geometry.iloc[0]
        bt.loc[k, "betriebsname"] = p.ps_name.iloc[0]
        bt.loc[k, "standort_quelle"] = "Produktionsstätte"

# --- amtliche Gebäudeadressen (Geocodierung, nächste Adresse)
adr_csv = next(BASIS.glob("amtliches-gebaeudeadressverzeichnis_ch_2056.csv/*.csv"))
adr = pd.read_csv(adr_csv, sep=";", dtype=str, encoding="utf-8-sig",
                  usecols=["STN_LABEL", "ADR_NUMBER", "ZIP_LABEL", "COM_NAME", "ADR_STATUS", "ADR_EASTING", "ADR_NORTHING"])
adr = adr[adr.ADR_STATUS == "real"]
ax, ay = adr.ADR_EASTING.astype(float).values, adr.ADR_NORTHING.astype(float).values
GEO = {f"{strasse_key(s_)}|{str(n).lower().replace(' ', '')}|{str(z)[:4]}": (x_, y_)
       for s_, n, z, x_, y_ in zip(adr.STN_LABEL, adr.ADR_NUMBER, adr.ZIP_LABEL, ax, ay)}

# Ungültige Standorte: einige Kantone liefern einen Platzhalterpunkt ausserhalb der Schweiz (z. B. 25 Betriebe auf
# demselben Punkt in Frankreich). Ersatz: die Adresse aus betriebsname amtlich verorten, sonst die grösste eigene Fläche.
pkt_fl = bt.set_index("betriebsnummer").geometry.reindex(fl.betriebsnummer).values
d_eigen = pd.Series(shapely.distance(pkt_fl, fl.geometry.values), index=fl.betriebsnummer.values).groupby(level=0).min()
x, y = bt.geometry.x, bt.geometry.y
ungueltig = ~x.between(2480000, 2840000) | ~y.between(1070000, 1300000) | (bt.betriebsnummer.map(d_eigen) > 50000)
groesste = fl.loc[fl.groupby("betriebsnummer").flaeche_m2.idxmax()].set_index("betriebsnummer").geometry
for i in bt.index[ungueltig]:
    k = adresse_key(bt.at[i, "betriebsname"])
    if k in GEO:
        bt.at[i, "geometry"] = shapely.Point(GEO[k])
        bt.at[i, "standort_quelle"] = "Adresse (amtlich verortet)"
    else:
        bt.at[i, "geometry"] = groesste[bt.at[i, "betriebsnummer"]].representative_point()
        bt.at[i, "standort_quelle"] = "grösste eigene Fläche (Standort fehlt)"
if ungueltig.any():
    print(f"Ungültige Standorte ersetzt: {int(ungueltig.sum())} ({bt[ungueltig].standort_quelle.value_counts().to_dict()})")

# --- Flächen: Kulturgruppe, Bio, Gemeinde (Lage des Flächenpunkts)
fl["gruppe"] = [kulturgruppe(c, n) for c, n in zip(fl.lnf_code, fl.nutzung)]
fl["bio"] = fl.programm.fillna("").str.contains("Bioproduktion")
grenzen = next(BASIS.glob("swissboundaries3d_*_2056_5728.gpkg/*.gpkg"))
gem = gpd.read_file(grenzen, layer="tlm_hoheitsgebiet", columns=["bfs_nummer", "name", "kantonsnummer", "objektart"])
gem = gem[gem.objektart == "Gemeindegebiet"]
gem["kt"] = gem.kantonsnummer.map(KT_NR)
punkte = gpd.GeoDataFrame(geometry=fl.geometry.representative_point(), crs=2056)
j = gpd.sjoin(punkte, gem[["name", "kt", "geometry"]], how="left", predicate="within")
j = j[~j.index.duplicated()]
fl["gemeinde_name"] = j["name"].fillna("Ausland").values
fl["gemeinde_kt"] = j["kt"].fillna("").values
fl["ha"] = fl.flaeche_m2 / 1e4

# --- Betriebe: Kennzahlen aus den Flächen
g = fl.groupby("betriebsnummer")
k = pd.DataFrame({
    "n_flaechen": g.size(),
    "ha": g.ha.sum(),
    "n_gebiet": g.in_gebiet.sum(),
    "ha_gebiet": fl[fl.in_gebiet].groupby("betriebsnummer").ha.sum(),
    "ha_bio": fl[fl.bio].groupby("betriebsnummer").ha.sum(),
})
gruppen = fl.pivot_table(index="betriebsnummer", columns="gruppe", values="ha", aggfunc="sum").reindex(columns=GROUPS)
gruppen.columns = [f"ha_g{i}" for i in range(len(GROUPS))]
k = k.join(gruppen).fillna(0)
for c in k.columns:
    if c.startswith("ha"):
        k[c] = k[c].round(2)


def top_gemeinden(d):
    s = d.groupby(["gemeinde_name", "gemeinde_kt"]).ha.sum().sort_values(ascending=False)
    # Kantonszusatz nur, wenn der amtliche Name ihn nicht schon trägt («Berg (TG)»)
    return "; ".join(f"{n}{f' ({kt})' if kt and not n.endswith(')') else ''} {v:.1f} ha" for (n, kt), v in s.head(4).items())


k["gemeinden"] = g.apply(top_gemeinden, include_groups=False)
k["kantone_flaechen"] = g.gemeinde_kt.apply(lambda s: ",".join(sorted(set(x for x in s if x))))
# Schwerpunkt (flächengewichtet), Ausdehnung
c = fl.geometry.centroid
fl["_wx"], fl["_wy"] = c.x * fl.flaeche_m2, c.y * fl.flaeche_m2
s = fl.groupby("betriebsnummer")[["_wx", "_wy", "flaeche_m2"]].sum()
k["sx"], k["sy"] = (s._wx / s.flaeche_m2).round(), (s._wy / s.flaeche_m2).round()
b4326 = fl.to_crs(4326).bounds.groupby(fl.betriebsnummer).agg({"minx": "min", "miny": "min", "maxx": "max", "maxy": "max"})
k["bbox"] = [f"{a:.5f},{b:.5f},{c_:.5f},{d:.5f}" for a, b, c_, d in b4326.loc[k.index].values]

bt = bt.set_index("betriebsnummer").join(k, how="left")
bt["kanton_sitz"] = bt.kanton
# --- Standort: Gemeinde, Abstand zu den Flächen
j = gpd.sjoin(bt[["geometry"]], gem[["name", "kt", "geometry"]], how="left", predicate="within")
j = j[~j.index.duplicated()]
bt["gemeinde"] = j["name"].fillna("").values
bt["dist_schwerpunkt_m"] = np.hypot(bt.geometry.x - bt.sx, bt.geometry.y - bt.sy).round()
pkt = bt.geometry.reindex(fl.betriebsnummer).values  # Betriebspunkt je Fläche
bt["dist_flaeche_m"] = pd.Series(shapely.distance(pkt, fl.geometry.values), index=fl.betriebsnummer.values) \
    .groupby(level=0).min().reindex(bt.index).round()
nah = shapely.distance(pkt, fl.geometry.centroid.values) <= 2000
bt["ha_2km"] = pd.Series(np.where(nah, fl.ha.values, 0), index=fl.betriebsnummer.values) \
    .groupby(level=0).sum().reindex(bt.index).round(2)

# --- Adresse: ZH aus betriebsname, sonst nächste amtliche Gebäudeadresse
baum = shapely.STRtree(shapely.points(ax, ay))
idx, dist = baum.query_nearest(bt.geometry.values, max_distance=ADRESSE_MAX_M, return_distance=True, all_matches=False)
gwr = pd.DataFrame({"i": idx[1], "d": dist}, index=bt.index[idx[0]])
gwr = gwr[~gwr.index.duplicated()]
a = adr.iloc[gwr.i.values]
gwr["adresse"] = (a.STN_LABEL.fillna("") + " " + a.ADR_NUMBER.fillna("")).str.strip().values + ", " + a.ZIP_LABEL.fillna("").values
# betriebsname: in ZH immer eine Adresse, in AG/SG/AR u. a. meist; in TG/SH ein Hof- oder Flurname. Einträge mit
# Personenangaben (c/o, z. Hd., Familie, Initialen, Vornamen …) werden nicht übernommen – dann die amtliche
# Gebäudeadresse am Punkt.
name = bt.betriebsname.fillna("").str.strip()
person = name.map(hat_person)
mit_plz = name.str.contains(r"\b\d{4}\b")
aus_daten = ~person & (name.str.match(STRASSE_NR) | ((bt.kanton == "ZH") & mit_plz))
gwr_adr = gwr.adresse.reindex(bt.index).fillna("")
bt["adresse"] = np.where(aus_daten, name, gwr_adr)
bt["adresse_quelle"] = np.where(aus_daten, "Kantonsdaten (betriebsname)",
                                np.where(gwr_adr != "", "nächste Gebäudeadresse (amtl. Verzeichnis)", ""))
bt["adresse_dist_m"] = np.where(aus_daten, 0, gwr.d.reindex(bt.index).round().fillna(-1)).astype(int)
bt["bezeichnung"] = np.where(~person & ~mit_plz, name, "")
print(f"Adresse aus den Kantonsdaten: {int(aus_daten.sum())}, nächste Gebäudeadresse: {int((~aus_daten & (gwr_adr != '')).sum())}, "
      f"betriebsname mit Personenangaben nicht übernommen: {int(person.sum())}")

# --- Produktionsstätten, Favoriten
# Öffentlich nur Nummer und Adresse (ps_name mit PLZ, ohne Personenangaben). Bezeichnungen ohne PLZ (in TG, ZG, SZ u. a.
# z. B. «Pouletstall <Name>») kommen nur in den verschlüsselten Teil (14_namen.py).


def ps_text(nr, name):
    name = str(name or "").strip().lstrip(",").strip()
    return f"{nr} {name}" if re.search(r"\b\d{4}\b", name) and not hat_person(name) else nr


ps_txt = ps.groupby("betriebsnummer").apply(lambda d: "; ".join(ps_text(a, b) for a, b in zip(d.ps_nr, d.ps_name)),
                                            include_groups=False)
bt["produktionsstaetten"] = ps_txt.reindex(bt.index).fillna("")
bt["favorit"] = [NR2FARM[nr]["key"] if nr in NR2FARM else "" for nr in bt.index]
w = bt.to_crs(4326).geometry
bt["lon"], bt["lat"] = w.x.round(6), w.y.round(6)

bt = bt.drop(columns=["kanton"]).reset_index()
spalten = ["betriebsnummer", "kanton_sitz", "bezugsjahr", "favorit", "standort_quelle", "adresse", "adresse_quelle", "adresse_dist_m", "bezeichnung",
           "gemeinde", "lon", "lat", "n_flaechen", "ha", "n_gebiet", "ha_gebiet", "ha_bio", "ha_2km", "dist_flaeche_m",
           "dist_schwerpunkt_m", "gemeinden", "kantone_flaechen", "produktionsstaetten", "bbox", "bur_nr"] + \
         [f"ha_g{i}" for i in range(len(GROUPS))]
bt = gpd.GeoDataFrame(bt[spalten + ["geometry"]], geometry="geometry", crs=2056)
if BETRIEBE.exists():
    BETRIEBE.unlink()
bt.to_file(BETRIEBE, layer="betriebe", driver="GPKG")
fl.drop(columns=["_wx", "_wy"]).to_file(BETRIEBE, layer="flaechen", driver="GPKG")
bt.drop(columns="geometry").to_csv(WORK / "betriebe.csv", index=False)
print(f"{len(bt)} Betriebe -> {BETRIEBE}")
print("Adresse:", (bt.adresse != "").sum(), "| ohne:", (bt.adresse == "").sum(),
      "| Standort > 3 km von eigenen Flächen:", int((bt.dist_flaeche_m > 3000).sum()))
print("Kulturgruppen (ha im Gebiet):", fl[fl.in_gebiet].groupby("gruppe").ha.sum().round().to_dict())
