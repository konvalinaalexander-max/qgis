"""Schritt 12: Gebiet festlegen und alle Betriebe sammeln, die darin Flächen bewirtschaften (alle Kantone).

Gebiet = konvexe Hülle aller Flächen der Betriebe in config «betriebe» + region.puffer_km, nur Schweiz.
Bezugsjahr: region.bezugsjahr (2025); hat ein Kanton nur einen anderen Jahrgang (GL, GR: 2026), wird dieser
verwendet (Spalte bezugsjahr). Ein Betrieb gehört dazu, wenn mindestens eine seiner Nutzungsflächen das Gebiet berührt. Von diesen Betrieben
werden ALLE Flächen übernommen, auch die ausserhalb des Gebiets (Spalte in_gebiet).

Liest  work/auswahl.gpkg (Schritt 1), data/raw/ und data/kantone/ (Schritt 11), data/basis/ (Landesgrenze)
Schreibt work/region.gpkg mit den Layern
  gebiet               kern (Hülle) und gebiet (Hülle + Puffer, nur CH)
  flaechen             Nutzungsflächen ohne überlagernde Elemente: betriebsnummer, kanton (Datensatz), lnf_code,
                       nutzung, programm, flaeche_m2, gemeinde (BFS der Bewirtschaftungseinheit), ps_nr, in_gebiet
  betriebe             amtlicher Betriebspunkt: betriebsnummer, betriebsname, bur_nr, kanton
  produktionsstaetten  ps_nr, ps_name, betriebsnummer, kanton
"""
import geopandas as gpd
import pandas as pd
import pyogrio
import shapely

from common import AUSWAHL, BASIS, CFG, KANTONE_DIR, REGION, kanton_gpkg

if not AUSWAHL.exists():
    raise SystemExit("work/auswahl.gpkg fehlt – zuerst scripts/01_auswahl.py ausführen.")

# --- Gebiet
fav = gpd.read_file(AUSWAHL, layer="nutzungsflaechen")
fav = fav[fav.ist_ueberlagernd != True]
grenzen = next(BASIS.glob("swissboundaries3d_*_2056_5728.gpkg/*.gpkg"), None)
if grenzen is None:
    raise SystemExit("data/basis/ fehlt – zuerst scripts/11_kantone.py ausführen.")
land = gpd.read_file(grenzen, layer="tlm_landesgebiet")
ch = shapely.union_all(land[land.icc == "CH"].geometry.values)
kern = shapely.union_all(fav.geometry.values).convex_hull
gebiet = kern.buffer(CFG["region"]["puffer_km"] * 1000).intersection(ch)
shapely.prepare(gebiet)
print(f"Gebiet: Kern {kern.area / 1e6:.0f} km², mit {CFG['region']['puffer_km']} km Puffer (nur CH) {gebiet.area / 1e6:.0f} km²")

kantone = list(CFG["kantone"]) + sorted(p.name for p in KANTONE_DIR.iterdir() if p.is_dir() and p.name not in CFG["kantone"]) \
    if KANTONE_DIR.exists() else list(CFG["kantone"])

NF_SPALTEN = ["identifikator_be", "lnf_code", "nutzung", "programm", "ist_ueberlagernd", "flaeche_m2", "bezugsjahr"]
JAHR = CFG["region"]["bezugsjahr"]
fl_teile, bt_teile, ps_teile, ohne_nf = [], [], [], []
for kt in kantone:
    pn, pb = kanton_gpkg("nutzungsflaechen", kt), kanton_gpkg("bewirtschaftungseinheit", kt)
    if not pn or not pb or not pn.exists():
        if list((KANTONE_DIR / kt).glob("lwb_nutzungsflaechen_*.zip")):
            raise SystemExit(f"[{kt}] ZIP der Nutzungsflächen vorhanden, aber nicht entpackt – scripts/11_kantone.py erneut ausführen.")
        ohne_nf.append(kt)
        continue
    # Jahrgang: Bezugsjahr aus config, sonst der (einzige) vorhandene
    jahre = set(pyogrio.read_dataframe(pn, layer="nutzungsflaechen", columns=["bezugsjahr"], read_geometry=False).bezugsjahr)
    if not jahre:
        print(f"[{kt}] Datensatz leer")
        continue
    jahr = JAHR if JAHR in jahre else max(jahre)
    if jahr != JAHR:
        print(f"[{kt}] Bezugsjahr {JAHR} fehlt, verwende {jahr}")
    # 1. Flächen im Gebiet -> Betriebe
    nf = gpd.read_file(pn, layer="nutzungsflaechen", bbox=gebiet.bounds, where=f"bezugsjahr = {jahr}",
                       columns=["identifikator_be", "ist_ueberlagernd"])
    nf = nf[(nf.ist_ueberlagernd != True) & shapely.intersects(gebiet, nf.geometry.values)]
    if nf.empty:
        print(f"[{kt}] keine Flächen im Gebiet")
        continue
    be = gpd.read_file(pb, layer="bewirtschaftungseinheit", ignore_geometry=True, where=f"bezugsjahr = {jahr}",
                       columns=["identifikator_be", "betriebsnummer", "gemeinde", "ps_nr"])
    nrs = set(be[be.identifikator_be.isin(nf.identifikator_be)].betriebsnummer)
    # 2. alle Flächen dieser Betriebe (auch ausserhalb des Gebiets)
    be = be[be.betriebsnummer.isin(nrs)]
    ids = set(be.identifikator_be)
    if len(ids) < 3000:
        liste = ",".join("'" + i.replace("'", "''") + "'" for i in ids)
        alle = gpd.read_file(pn, layer="nutzungsflaechen", columns=NF_SPALTEN,
                             where=f"bezugsjahr = {jahr} AND identifikator_be IN ({liste})")
    else:
        alle = gpd.read_file(pn, layer="nutzungsflaechen", columns=NF_SPALTEN, where=f"bezugsjahr = {jahr}")
        alle = alle[alle.identifikator_be.isin(ids)]
    alle = alle[alle.ist_ueberlagernd != True].drop(columns="ist_ueberlagernd")
    # deckungsgleiche Flächen desselben Betriebs nur einmal (AG meldet Code 595 zusätzlich auf Hauptkulturen)
    alle["_geo"] = alle.geometry.normalize().to_wkb()
    alle["_595"] = alle.lnf_code == 595
    n0 = len(alle)
    alle = alle.sort_values("_595").drop_duplicates(subset=["identifikator_be", "_geo"]).sort_index().drop(columns=["_geo", "_595"])
    if len(alle) < n0:
        print(f"[{kt}] {n0 - len(alle)} deckungsgleiche Doppelflächen weggelassen")
    alle = alle.merge(be, on="identifikator_be", how="left").drop(columns="identifikator_be")
    alle["kanton"] = kt
    alle["in_gebiet"] = shapely.intersects(gebiet, alle.geometry.values)
    fl_teile.append(alle)
    bt = gpd.read_file(pb, layer="betrieb", columns=["betriebsnummer", "betriebsname", "bur_nr"], where=f"bezugsjahr = {jahr}")
    bt_teile.append(bt[bt.betriebsnummer.isin(nrs)].assign(kanton=kt, bezugsjahr=jahr))
    ps = gpd.read_file(pb, layer="produktionsstaette", columns=["ps_nr", "ps_name", "betriebsnummer"], where=f"bezugsjahr = {jahr}")
    ps_teile.append(ps[ps.betriebsnummer.isin(nrs)].assign(kanton=kt))
    print(f"[{kt}] {len(nrs):>5} Betriebe, {int(alle.in_gebiet.sum()):>7} Flächen im Gebiet, {len(alle):>7} Flächen insgesamt")

fl = pd.concat(fl_teile, ignore_index=True)
bt = pd.concat(bt_teile, ignore_index=True)
ps = pd.concat(ps_teile, ignore_index=True)
doppelt = bt.betriebsnummer[bt.betriebsnummer.duplicated()]
if len(doppelt):
    raise SystemExit(f"Betriebsnummer in mehreren Kantonen: {sorted(set(doppelt))[:10]}")
fehlt = set(fl.betriebsnummer) - set(bt.betriebsnummer)
if fehlt:
    print(f"WARNUNG – {len(fehlt)} Betriebsnummern ohne Betriebspunkt, z. B. {sorted(fehlt)[:5]}")

if REGION.exists():
    REGION.unlink()
gpd.GeoDataFrame({"name": ["kern", "gebiet"], "km2": [round(kern.area / 1e6), round(gebiet.area / 1e6)]},
                 geometry=[kern, gebiet], crs=2056).to_file(REGION, layer="gebiet", driver="GPKG")
gpd.GeoDataFrame(fl, geometry="geometry", crs=2056).to_file(REGION, layer="flaechen", driver="GPKG")
gpd.GeoDataFrame(bt, geometry="geometry", crs=2056).to_file(REGION, layer="betriebe", driver="GPKG")
gpd.GeoDataFrame(ps, geometry="geometry", crs=2056).to_file(REGION, layer="produktionsstaetten", driver="GPKG")
print(f"Total: {bt.betriebsnummer.nunique()} Betriebe aus {fl.kanton.nunique()} Kantonen, "
      f"{int(fl.in_gebiet.sum())} Flächen im Gebiet ({fl[fl.in_gebiet].flaeche_m2.sum() / 1e4:,.0f} ha), "
      f"{len(fl)} Flächen insgesamt -> {REGION}")
if ohne_nf:
    print("Ohne Nutzungsflächen (nicht frei erhältlich):", ", ".join(ohne_nf))
