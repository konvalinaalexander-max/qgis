"""Schritt 1: Aus den kantonalen Rohdaten die Flächen der konfigurierten Betriebe herausziehen.

Liest  data/raw/lwb_*  (Bewirtschaftungseinheiten + Nutzungsflächen je Kanton)
Schreibt work/auswahl.gpkg mit den Layern
  - nutzungsflaechen          (alle Attribute + betriebsnummer, gemeinde, ps_nr (Produktionsstätte), kanton)
  - bewirtschaftungseinheiten
  - betriebe                  (Betriebsstandorte, Punkte)
  - produktionsstaetten       (Produktionsstätten der Betriebe, Punkte mit Adresse)

Prinzip: Ein Betrieb meldet ALLE seine Flächen dem Kanton seines Sitzes, auch Flächen in
Nachbarkantonen. Darum wird jede Betriebsnummer im Datensatz ihres Sitzkantons gesucht.
"""
import geopandas as gpd
import pandas as pd

from common import AUSWAHL, CFG, FARMS, raw_gpkg, teil_of

nrs = [n for f in FARMS for n in f["nrs"]]
be_parts, nf_parts, bt_parts, ps_parts = [], [], [], []

for kt in CFG["kantone"]:
    pb, pn = raw_gpkg("bewirtschaftungseinheit", kt), raw_gpkg("nutzungsflaechen", kt)
    if not pb.exists() or not pn.exists():
        print(f"[{kt}] Rohdaten fehlen, übersprungen: {pb.parent.parent.name} / {pn.parent.parent.name}")
        continue
    be = gpd.read_file(pb, layer="bewirtschaftungseinheit")
    be = be[be.betriebsnummer.isin(nrs)].copy()
    if be.empty:
        print(f"[{kt}] keine der Betriebsnummern enthalten")
        continue
    be["kanton"] = kt
    bt = gpd.read_file(pb, layer="betrieb")
    bt = bt[bt.betriebsnummer.isin(nrs)].copy()
    bt["kanton"] = kt
    ps = gpd.read_file(pb, layer="produktionsstaette")
    ps = ps[ps.betriebsnummer.isin(nrs)].copy()
    ps["kanton"] = kt

    ids = ",".join(f"'{i}'" for i in be.identifikator_be.unique())
    nf = gpd.read_file(pn, layer="nutzungsflaechen", where=f"identifikator_be IN ({ids})")
    nf["kanton"] = kt
    nf = nf.merge(be[["identifikator_be", "betriebsnummer", "gemeinde", "ps_nr"]], on="identifikator_be", how="left")  # ps_nr: Produktionsstätte -> Teilbetrieb
    print(f"[{kt}] {be.betriebsnummer.nunique()} Betriebsnummern, {len(be)} Bewirtschaftungseinheiten, {len(nf)} Nutzungsflächen")
    be_parts.append(be); nf_parts.append(nf); bt_parts.append(bt); ps_parts.append(ps)

if not be_parts:
    raise SystemExit("Keine Daten gefunden – stimmen Betriebsnummern in config/projekt.json und Ordner in data/raw?")

be = pd.concat(be_parts, ignore_index=True)
nf = pd.concat(nf_parts, ignore_index=True)
bt = pd.concat(bt_parts, ignore_index=True)
ps = pd.concat(ps_parts, ignore_index=True)

fehlend = [n for n in nrs if n not in set(be.betriebsnummer)]
if fehlend:
    print("WARNUNG – nicht gefunden:", fehlend)

if AUSWAHL.exists():
    AUSWAHL.unlink()
nf.to_file(AUSWAHL, layer="nutzungsflaechen", driver="GPKG")
be.to_file(AUSWAHL, layer="bewirtschaftungseinheiten", driver="GPKG")
bt.to_file(AUSWAHL, layer="betriebe", driver="GPKG")
ps.to_file(AUSWAHL, layer="produktionsstaetten", driver="GPKG")

haupt = nf[nf.ist_ueberlagernd != True]
s = haupt.groupby("betriebsnummer").agg(flaechen=("t_id", "count"), ha=("flaeche_m2", lambda v: round(v.sum() / 1e4, 2)))
print(s.to_string())
haupt = haupt.assign(teil=[teil_of(n, ps)["id"] for n, ps in zip(haupt.betriebsnummer, haupt.ps_nr)])  # Fehler, wenn ein Teil fehlt
print(haupt.groupby("teil").agg(flaechen=("t_id", "count"), ha=("flaeche_m2", lambda v: round(v.sum() / 1e4, 2))).to_string())
print(f"geschrieben: {AUSWAHL.relative_to(AUSWAHL.parents[1])}  ({len(nf)} Nutzungsflächen inkl. überlagernde, {len(be)} BE, {len(bt)} Betriebe)")
