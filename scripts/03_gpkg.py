"""Schritt 3: Lesbares GeoPackage für QGIS (und als Datengrundlage für Excel).

Liest  work/auswahl.gpkg
Schreibt output/<dateinamen.gpkg> mit den Layern
  - flaechen           (eine Zeile pro Hauptkultur-Fläche, deutsche Spaltennamen, mit Teilbetrieb und Bio-Status)
  - betriebsstandorte  (Punkte)
"""
import geopandas as gpd

from common import AUSWAHL, BIO_LABELS, NR2FARM, bio_status, gemeinde, kulturgruppe, out_path, teil_of

nf = gpd.read_file(AUSWAHL, layer="nutzungsflaechen")
nf = nf[nf.ist_ueberlagernd != True].copy()
gem = [gemeinde(g) for g in nf.gemeinde]
tl = [teil_of(n, ps) for n, ps in zip(nf.betriebsnummer, nf.ps_nr)]

out = gpd.GeoDataFrame({
    "betrieb": nf.betriebsnummer.map(lambda n: NR2FARM[n]["name"]),
    "betriebsnummer": nf.betriebsnummer,
    "teilbetrieb": [t["name"] for t in tl],
    "produktionsstaette": nf.ps_nr,
    "kultur": nf.nutzung,
    "lnf_code": nf.lnf_code,
    "kulturgruppe": [kulturgruppe(c, n) for c, n in zip(nf.lnf_code, nf.nutzung)],
    "flaeche_a": (nf.flaeche_m2 / 100).round(1),
    "flaeche_ha": (nf.flaeche_m2 / 1e4).round(3),
    "gemeinde": [g[0] for g in gem],
    "kanton": [g[1] for g in gem],
    "programme": nf.programm,
    "bio_status": [BIO_LABELS[bio_status(pr, t)] for pr, t in zip(nf.programm, tl)],
    "beitragsberechtigt": nf.beitragsberechtigt,
    "bezugsjahr": nf.bezugsjahr,
    "identifikator_be": nf.identifikator_be,
}, geometry=nf.geometry, crs=nf.crs)

p = out_path("gpkg")
if p.exists():
    p.unlink()
out.to_file(p, layer="flaechen", driver="GPKG")
bt = gpd.read_file(AUSWAHL, layer="betriebe")
bt["betrieb"] = bt.betriebsnummer.map(lambda n: NR2FARM[n]["name"])
bt[["betrieb", "betriebsnummer", "geometry"]].to_file(p, layer="betriebsstandorte", driver="GPKG")

print(out.groupby("betrieb").flaeche_ha.agg(["count", "sum"]).round(2).to_string())
print(f"{len(out)} Flächen, {len(bt)} Standorte -> output/{p.name}")
