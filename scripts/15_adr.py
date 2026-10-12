"""Schritt 15: AdR-Regionen («Aus der Region», Migros) als Flächen und Anteile je Betrieb.

Die Regionsdefinitionen (öffentlich, von der Migros) liegen als Excel-Dateien in data/adr/ (früher data/intern/adr/;
eine Datei je Region, je Zeile PLZ und Ort; nicht im Git). Der Regionsname ist der Dateiname ohne den Teil, den alle
Dateinamen gemeinsam haben. Jede Zeile wird auf die amtlichen PLZ-Gebiete (Ortschaftenverzeichnis swisstopo) abgebildet:
- Ortsname genau gleich wie eine Ortschaft der PLZ (verglichen werden ganzer Name, Name ohne Klammerteil, Teile bei «/»,
  jeweils mit und ohne Kantonskürzel) -> diese Ortschaft(en);
- sonst die Ortschaft gleichen Namens unter einer anderen PLZ mit denselben ersten zwei Ziffern bzw. < 10 km entfernt
  (alte PLZ in den Listen: «8370 Busswil TG» -> 8371, «8842 Egg» -> Egg SZ 8847);
- sonst Ortschaften, deren Name mit dem Listennamen beginnt (oder umgekehrt), sonst alle Gebiete der PLZ;
- «NNxx» -> alle PLZ NN00–NN99; PLZ ohne Gebiet (Postfach u. ä.) -> Gemeinde gleichen Namens, sonst Gemeinde, deren
  Name das Ende eines alten Ortsnamens ist («Oberehrendingen» -> Ehrendingen);
- Gemeindelisten (Genève, Valais: «Comm. / lieu»): zusätzlich die ganze Gemeinde («1934 Val de Bagnes» mit Verbier).
Ortschaften einer gelisteten PLZ, die in keiner Liste mit eigenem Namen vorkommen, gehören zur Region, die die PLZ führt.
Regionen können sich überschneiden – die Anteile eines Betriebs ergeben dann zusammen mehr als 100 %. In keiner Region
liegen Flächen in PLZ, die keine Liste führt (Tessin: keine Liste der Migros Ticino; Kloster Fahr).

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
orte = gpd.read_file(ovz / "AMTOVZ_LOCALITY.shp", ignore_geometry=True)[["LOCALITYID", "NAME", "SHORTNAME", "INDEXNAME"]]
plz = plz.merge(orte, left_on="FK_LOCALIT", right_on="LOCALITYID", how="left")
plz["ZIP4"] = plz.ZIP4.astype(int)
KT = r"\b(zh|tg|sh|sg|ag|lu|be|so|bl|bs|fr|vd|ne|ge|vs|ju|zg|sz|gl|ur|ow|nw|ai|ar|gr|ti)\b"


def varianten(t):
    """Vergleichbare Formen eines Ortsnamens: ganz, ohne Klammerteil, je Teil bei «/», jeweils auch ohne Kantonskürzel.
    «Waldhäusern (Bünzen)» -> {waldhausern bunzen, waldhausern}; «Busswil TG» -> {busswil tg, busswil}."""
    t = str(t or "")
    roh = {t, re.sub(r"\(.*?\)", " ", t)} | set(t.split("/"))
    v = set()
    for x in roh:
        n = norm(x)
        if n:
            v |= {n, re.sub(r"\s+", " ", re.sub(KT, " ", n)).strip()}
            v.add(re.sub(r"^(ville de|commune de|gemeinde) ", "", n))
    return {x for x in v if x}


plz["namen"] = [varianten(a) | varianten(b) | varianten(c) for a, b, c in zip(plz.NAME, plz.SHORTNAME, plz.INDEXNAME)]
plz["mitte"] = plz.geometry.representative_point()
# Gemeinden (swissBOUNDARIES3D): Ersatz für Zeilen ohne PLZ-Gebiet und für Gemeindelisten (Genève, Valais)
grenzen = next(BASIS.glob("swissboundaries3d_*_2056_5728.gpkg/*.gpkg"))
gem = gpd.read_file(grenzen, layer="tlm_hoheitsgebiet", columns=["bfs_nummer", "name"])
gem["geometry"] = shapely.force_2d(gem.geometry.values)  # swissBOUNDARIES3D hat Höhen (3D)
gem = gem.dissolve(by="name").reset_index()
gem["ZIP_ID"] = "G" + gem.bfs_nummer.astype(str)
gem["ZIP4"], gem["NAME"] = 0, gem.name
gem["namen"] = gem.name.map(varianten)
gem["mitte"] = gem.geometry.representative_point()
# PLZ-Vorwahlen (erste zwei Ziffern), mit denen sich eine Gemeinde überschneidet: Plausibilität für Ersatz-Treffer
_j = gpd.sjoin(gem[["ZIP_ID", "geometry"]], plz[["ZIP4", "geometry"]], predicate="intersects")
gem["vorwahl"] = gem.ZIP_ID.map(_j.groupby("ZIP_ID").ZIP4.agg(lambda s: set(s // 100))).apply(lambda x: x if isinstance(x, set) else set())
plz = pd.concat([plz, gem[["ZIP_ID", "ZIP4", "NAME", "namen", "mitte", "geometry"]]], ignore_index=True)
ist_gem = plz.ZIP4 == 0
nach_plz = plz[~ist_gem].groupby("ZIP4").groups
NAMEN_INDEX = {}   # Namensvariante -> Gebiete (nur PLZ-Gebiete)
for i, ns in plz.loc[~ist_gem, "namen"].items():
    for n in ns:
        NAMEN_INDEX.setdefault(n, []).append(i)
GEM_INDEX = {}
for i, ns in plz.loc[ist_gem, "namen"].items():
    for n in ns:
        GEM_INDEX.setdefault(n, []).append(i)
VORWAHL = dict(zip(gem.ZIP_ID, gem.vorwahl))


def stand_aus(kopfzeilen):
    """Neuestes Datum in den Kopfzeilen einer Liste -> «Stand TT.MM.JJJJ» (Texte der Listen sind uneinheitlich)."""
    import datetime as dt
    daten = []
    for t in kopfzeilen:
        for d, m, y in re.findall(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b", str(t)):
            y = int(y) + (2000 if len(y) == 2 else 0)
            try:
                daten.append(dt.date(y, int(m), int(d)))
            except ValueError:
                pass
    return f"Stand {max(daten):%d.%m.%Y}" if daten else ""


zuordnung, stand, offen, hinweise = [], {}, {}, []
mit_name, gelistet = set(), []  # Gebiete, die irgendwo mit eigenem Ortsnamen stehen; (Region, PLZ)
for p in dateien:
    reg = region_name(p)
    roh = pd.read_excel(p, header=None, dtype=str).fillna("")
    kopf = next(i for i, r in roh.iterrows() if re.match(r"^(PLZ|CP|NPA)$", r.iloc[0].strip(), re.I))
    stand[reg] = stand_aus(" ".join(r) for _, r in roh.iloc[:kopf].iterrows())
    # Genève und Valais listen Gemeinden («Comm. / lieu»): ganze Gemeinde dazu (z. B. «1934 Val de Bagnes» mit Verbier).
    # Die übrigen Listen («Gemeinden / Orte») sind PLZ-genau: «8404 Winterthur» heisst nur dieses PLZ-Gebiet.
    gemeindeliste = bool(re.search(r"\bcomm", str(roh.iloc[kopf, 1]), re.I))
    n_ok, fehlt = 0, []
    for _, r in roh.iloc[kopf + 1:].iterrows():
        code, ort = r.iloc[0].strip(), r.iloc[1].strip()
        if not code:
            continue
        v = varianten(ort)
        if re.fullmatch(r"\d{2}xx", code, re.I):
            treffer = list(plz[~ist_gem & ((plz.ZIP4 // 100) == int(code[:2]))].index)
        elif re.fullmatch(r"\d{4}(\.0)?", code):
            nr = int(code[:4])
            kand = list(nach_plz.get(nr, []))
            exakt = [i for i in kand if plz.namen[i] & v]
            if exakt:
                treffer = exakt
            else:
                # Ort steht mit genau diesem Namen unter einer anderen, nahen PLZ (z. B. «8370 Busswil TG» -> 8371)
                bezug = shapely.union_all(plz.geometry[kand].values).centroid if kand else None
                anders = sorted({i for n in v for i in NAMEN_INDEX.get(n, [])
                                 if (plz.ZIP4[i] // 100 == nr // 100) or (bezug is not None and plz.mitte[i].distance(bezug) < 10000)})
                if anders:
                    treffer = anders
                    hinweise.append(f"{reg}: «{code} {ort}» -> PLZ {', '.join(str(plz.ZIP4[i]) for i in anders)} (Ort dort)")
                    gelistet += [(reg, int(plz.ZIP4[i])) for i in anders]
                else:
                    # Ortsname beginnt mit dem Namen einer Ortschaft der PLZ («Zürich Kreis 1») oder umgekehrt
                    teil = [i for i in kand if any(a.startswith(b + " ") or b.startswith(a + " ") for a in v for b in plz.namen[i])]
                    treffer = teil or kand
            mit_name.update(plz.ZIP_ID[i] for i in treffer if plz.ZIP4[i] > 0 and plz.namen[i] & v)
            gelistet.append((reg, nr))
            if gemeindeliste or not treffer:
                # Gemeinde gleichen Namens: bei Gemeindelisten immer dazu, sonst Ersatz für PLZ ohne Gebiet (Postfach u. ä.)
                g = sorted({i for n in v for i in GEM_INDEX.get(n, [])} | {i for i in GEM_INDEX.get(norm(ort) + " am hochrhein", [])})
                if not g and not treffer:   # alter Ortsname einer fusionierten Gemeinde («Oberehrendingen» -> Ehrendingen)
                    kandidaten = [(len(gn), i) for n in v for gn, idx in GEM_INDEX.items() if len(gn) >= 5 and n.endswith(gn) and n != gn
                                  for i in idx if nr // 100 in VORWAHL.get(plz.ZIP_ID[i], set())]
                    laengster = max((l for l, _ in kandidaten), default=0)   # der spezifischste Name (Ehrendingen, nicht Endingen)
                    g = sorted({i for l, i in kandidaten if l == laengster})
                    if g:
                        hinweise.append(f"{reg}: «{code} {ort}» -> Gemeinde {', '.join(plz.NAME[i] for i in g)}")
                treffer = list(treffer) + g
        else:
            treffer = []
        if len(treffer) == 0:
            fehlt.append(f"{code} {ort}")
            continue
        n_ok += 1
        zuordnung += [(reg, plz.ZIP_ID[i]) for i in treffer]
    offen[reg] = fehlt
    print(f"{reg:<32} {n_ok:>4} Zeilen zugeordnet, {len(fehlt):>3} ohne Gebiet (Postfach-PLZ, Ausland u. ä.)  [{stand[reg]}]")
for h in hinweise:
    print("  Zuordnung über den Ortsnamen:", h)

# Ortschaften ohne eigenen Listeneintrag zur Region ihrer PLZ
for reg, nr in set(gelistet):
    zuordnung += [(reg, plz.ZIP_ID[i]) for i in nach_plz.get(nr, []) if plz.ZIP_ID[i] not in mit_name]
z = pd.DataFrame(zuordnung, columns=["region", "ZIP_ID"]).drop_duplicates()
plz_reg = plz.drop(columns=["namen", "mitte"]).merge(z, on="ZIP_ID")
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
