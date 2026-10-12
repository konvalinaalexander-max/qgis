"""Schritt 14: Namen zu den Betrieben der Region zuordnen (Ergebnis vertraulich, nicht im Git).

Nur Quellen, in denen sich Betriebe selbst oder von Gesetzes wegen öffentlich als Unternehmen zeigen:
  hr      Handelsregister (Zefix, offene Daten des Bundes über LINDAS): Firmen mit landwirtschaftlichem Zweck/Namen
  sbv     Hofsuche des Schweizer Bauernverbands (freiwilliger Eintrag der Höfe: Hofname, Betriebsleitung)
  osm     OpenStreetMap: Hofläden (shop=farm, Betreiber) und Hofnamen (place=farm)
  daten   Bezeichnung in den Kantonsdaten (betriebsname in TG/SH/AG …, Hof- oder Firmenname)
  config  die Favoriten aus config/projekt.json
  recherche  Web-Recherche (data/intern/namen_recherche.csv, je Zeile Quelle und Sicherheit)
Nicht verwendet: UID-Register als Massenabfrage (UIDG Art. 11: öffentliche Abfragen nur zu einzelnen Einheiten),
private Telefonbucheinträge, Angaben zu Familienmitgliedern.

Ohne --personen (Standard) nur Namen, die keine Personendaten sind: Firmen mit eigener Rechtspersönlichkeit (AG, GmbH,
Genossenschaft, Verein, Stiftung), Hofnamen und die Bezeichnung in den Kantonsdaten. Mit --personen zusätzlich
Einzelunternehmen und Kollektivgesellschaften aus dem Handelsregister, die Hofsuche SBV (Betriebsleitung) und die
Betreiber von Hofläden (OSM) – nur auf ausdrücklichen Wunsch (Personendaten).

Zuordnung über die Lage: Eintrag (Koordinate bzw. amtlich geocodierte Adresse) beim amtlichen Betriebspunkt
(Abstand in Metern). Mehrere Betriebe am selben Punkt -> alle bekommen den Eintrag, Sicherheit «unsicher».

Liest  work/betriebe.gpkg (Schritt 13), data/basis/ (Gebäudeadressen), data/intern/quellen/ (Abzüge, siehe --laden)
Schreibt data/intern/namen.csv: betriebsnummer, art, name, person, detail, quelle, url, abstand_m, sicherheit
Aufruf: python3 scripts/14_namen.py [--laden] [--personen]   (--laden: Quellen neu abfragen)
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from common import BASIS, BETRIEBE, CFG, FARMS, INTERN, REGION, adresse_key, strasse_key, teile

ap = argparse.ArgumentParser()
ap.add_argument("--laden", action="store_true", help="Quellen neu abfragen (sonst data/intern/quellen/ verwenden)")
ap.add_argument("--personen", action="store_true", help="auch Personennamen (Einzelunternehmen, Hofsuche SBV, Hofladen-Betreiber)")
args = ap.parse_args()
Q = INTERN / "quellen"
Q.mkdir(parents=True, exist_ok=True)

LANDW = ("landwirtschaft|gemüse|gemuese|bauernhof|agrar|ackerbau|pflanzenbau|tierhaltung|viehzucht|milchwirtschaft|"
         "milchproduktion|obstbau|obstanlage|beeren|hofladen|gärtnerei|gaertnerei|baumschule|jungpflanzen|setzlinge|"
         "gewächshaus|treibhaus|weinbau|rebbau|kräuter|bio-produkt|bioprodukt|biohof|hofgemeinschaft|"
         "betriebsgemeinschaft|generationengemeinschaft|bewirtschaftung")
KANTONE_HR = ("ZH", "TG", "SH", "SG", "AG", "SZ", "ZG", "AR", "AI", "GL", "LU")


def laden_hr():
    q = f"""PREFIX schema: <http://schema.org/>
PREFIX admin: <https://schema.ld.admin.ch/>
PREFIX locn: <http://www.w3.org/ns/locn#>
SELECT ?c ?name ?typ ?muni ?desc ?str ?nr ?plz ?ort ?kt WHERE {{
  ?c a admin:ZefixOrganisation ; schema:legalName ?name ; schema:additionalType ?typ ; admin:municipality ?muni ;
     schema:address ?adr .
  ?adr locn:adminUnitL2 ?kt .
  FILTER(?kt IN ({",".join(f'"{k}"' for k in KANTONE_HR)}))
  OPTIONAL {{ ?c schema:description ?desc }}
  OPTIONAL {{ ?adr locn:thoroughfare ?str }}
  OPTIONAL {{ ?adr locn:locatorDesignator ?nr }}
  OPTIONAL {{ ?adr locn:postCode ?plz }}
  OPTIONAL {{ ?adr locn:postName ?ort }}
  FILTER(REGEX(CONCAT(STR(?name), " ", COALESCE(STR(?desc), "")), "{LANDW}", "i"))
}}"""
    req = urllib.request.Request("https://ld.admin.ch/query", data=urllib.parse.urlencode({"query": q}).encode(),
                                 headers={"Accept": "text/csv"})
    (Q / "hr_lindas.csv").write_bytes(urllib.request.urlopen(req, timeout=900).read())


def laden_sbv(gebiet4326):
    """Raster über das Gebiet; gespeichert werden nur Hofname, Betriebsleitung, Adresse, Website, Lage, Produktion."""
    out, seen = [], set()
    minx, miny, maxx, maxy = gebiet4326.bounds
    for lat in np.arange(miny + 0.04, maxy, 0.09):
        for lon in np.arange(minx + 0.05, maxx, 0.13):
            if not gebiet4326.buffer(0.05).contains(shapely.Point(lon, lat)):
                continue
            url = f"https://www.schweizerbauern.ch/hofsuche.php?lat={lat:.5f}&lon={lon:.5f}&lang=de&size=200"
            for versuch in range(4):
                try:
                    d = json.load(urllib.request.urlopen(url, timeout=90))
                    break
                except OSError:
                    time.sleep(2 ** (versuch + 1))
            else:
                raise SystemExit(f"Hofsuche nicht erreichbar: {url}")
            for h in d["hits"]:
                s = h["_source"]
                if s["id"] in seen or not s.get("location"):
                    continue
                seen.add(s["id"])
                out.append({"id": s["id"], "hofname": s.get("farmname") or "", "vorname": s.get("first_name") or "",
                            "nachname": s.get("last_name") or "", "strasse": s.get("street") or "",
                            "plz": s.get("zip") or "", "ort": (s.get("city") or "").strip(), "website": s.get("website") or "",
                            "lat": float(s["location"]["lat"]), "lon": float(s["location"]["lon"]),
                            "produktion": (s.get("productiontype") or {}).get("name", ""),
                            "kulturen": ", ".join(c["name"] for c in s.get("cultures") or []),
                            "labels": ", ".join(c["name"] for c in s.get("productionlabels") or [])})
            time.sleep(1)
    (Q / "sbv_hofsuche.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")


def laden_osm(gebiet4326):
    s, w, n, e = gebiet4326.bounds[1], gebiet4326.bounds[0], gebiet4326.bounds[3], gebiet4326.bounds[2]
    bb = f"{s:.4f},{w:.4f},{n:.4f},{e:.4f}"
    ql = f"""[out:json][timeout:300];
(nwr["shop"="farm"]({bb}); nwr["place"="farm"]["name"]({bb}); nwr["landuse"="farmyard"]["name"]({bb});
 nwr["building"="farm"]["name"]({bb}); nwr["amenity"="vending_machine"]["vending"~"farm|milk|eggs|fruit|vegetables|potatoes"]({bb});
 nwr["craft"~"winery|beekeeper"]({bb}); nwr["landuse"="greenhouse_horticulture"]["name"]({bb}););
out center tags;"""
    for ep in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
        try:
            r = urllib.request.urlopen(ep, data=urllib.parse.urlencode({"data": ql}).encode(), timeout=400).read()
            json.loads(r)
            (Q / "osm.json").write_bytes(r)
            return
        except (OSError, ValueError):
            continue
    raise SystemExit("Overpass nicht erreichbar")


bt = gpd.read_file(BETRIEBE, layer="betriebe")
gebiet = gpd.read_file(REGION, layer="gebiet").set_index("name").geometry
g4326 = gpd.GeoSeries([gebiet["gebiet"]], crs=2056).to_crs(4326).iloc[0]
if args.laden or not (Q / "hr_lindas.csv").exists() or not (Q / "osm.json").exists():
    laden_hr()
    laden_osm(g4326)
if args.personen and (args.laden or not (Q / "sbv_hofsuche.json").exists()):
    laden_sbv(g4326)
JURISTISCH = ("0106", "0107", "0108", "0109", "0110")  # AG, GmbH, Genossenschaft, Verein, Stiftung
if not args.personen:
    # Datensparsam: ohne --personen keine Personendaten aufbewahren (Einzelunternehmen u. ä., Hofladen-Betreiber)
    _hr = pd.read_csv(Q / "hr_lindas.csv", dtype=str).fillna("")
    _hr[_hr.typ.str.rsplit("/", n=1).str[-1].isin(JURISTISCH)].to_csv(Q / "hr_lindas.csv", index=False)
    _osm = json.loads((Q / "osm.json").read_text(encoding="utf-8"))
    for _e in _osm["elements"]:
        _e.get("tags", {}).pop("operator", None)
    (Q / "osm.json").write_text(json.dumps(_osm, ensure_ascii=False), encoding="utf-8")
    (Q / "sbv_hofsuche.json").unlink(missing_ok=True)

# --- amtliche Gebäudeadressen (zum Geocodieren der Registeradressen)
adr = pd.read_csv(next(BASIS.glob("amtliches-gebaeudeadressverzeichnis_ch_2056.csv/*.csv")), sep=";", dtype=str,
                  encoding="utf-8-sig", usecols=["STN_LABEL", "ADR_NUMBER", "ZIP_LABEL", "ADR_STATUS", "ADR_EASTING", "ADR_NORTHING"])
adr = adr[adr.ADR_STATUS == "real"]


adr["key"] = [f"{strasse_key(s)}|{str(n).lower().replace(' ', '')}|{str(z)[:4]}"
              for s, n, z in zip(adr.STN_LABEL, adr.ADR_NUMBER, adr.ZIP_LABEL)]
GEO = dict(zip(adr.key, zip(adr.ADR_EASTING.astype(float), adr.ADR_NORTHING.astype(float))))

PUNKTE = shapely.STRtree(bt.geometry.values)
PERSON_WORT = re.compile(r"(?i:\bc/o\b|\bfam\.|\bfamilie\b|\bdr\.|\bherr\b|\bfrau\b)|(?:^|\s)[A-ZÄÖÜ]\.\s?[A-ZÄÖÜ][a-zäöüé]")


ADR_BETRIEB = {}
for i, a in enumerate(bt.adresse.fillna("")):
    k = adresse_key(a)
    if k:
        ADR_BETRIEB.setdefault(k, []).append(i)
        ADR_BETRIEB.setdefault(k.rsplit("|", 2)[0] + "|" + k.split("|")[1].split(".")[0] + "|" + k.rsplit("|", 1)[1], []).append(i)


def zuordnen(x, y, max_m):
    """Koordinate (LV95) -> Liste (Index Betrieb, Abstand m), alle Betriebspunkte innerhalb max_m."""
    p = shapely.Point(x, y)
    idx = PUNKTE.query(p, predicate="dwithin", distance=max_m)
    return sorted(((int(i), round(p.distance(bt.geometry.iloc[i]))) for i in idx), key=lambda t: t[1])


zeilen = []


def eintrag(i, art, name, person, detail, quelle, url, abstand, sicherheit):
    zeilen.append({"betriebsnummer": bt.betriebsnummer.iloc[i], "art": art, "name": name.strip(), "person": person.strip(),
                   "detail": detail.strip(), "quelle": quelle, "url": url, "abstand_m": abstand, "sicherheit": sicherheit})


def verteilen(treffer, sicher_m, adr_key="", **kw):
    """Treffer an die Betriebe verteilen. Gleiche Adresse wie genau ein Betrieb -> dieser («wahrscheinlich»).
    Sonst über die Lage; teilen sich mehrere Betriebe den Punkt (< 30 m), ist es «unsicher»."""
    gleich = sorted(set(ADR_BETRIEB.get(adr_key, []))) if adr_key else []
    if len(gleich) == 1:
        i = gleich[0]
        d = next((d for j, d in treffer if j == i), -1)
        eintrag(i, abstand=d, sicherheit="wahrscheinlich", **kw)
        return
    if not treffer:
        return
    nahe = [t for t in treffer if t[1] <= treffer[0][1] + 30]
    for i, d in nahe:
        s = "wahrscheinlich" if d <= sicher_m and len(nahe) == 1 else "unsicher"
        eintrag(i, abstand=d, sicherheit=s, **kw)


# 1. Handelsregister: Adresse amtlich geocodieren, Betriebspunkt innerhalb 150 m
LF = {"0101": "Einzelunternehmen", "0103": "Kollektivgesellschaft", "0104": "Kommanditgesellschaft", "0106": "AG",
      "0107": "GmbH", "0108": "Genossenschaft", "0109": "Verein", "0110": "Stiftung", "0111": "Zweigniederlassung"}
hr = pd.read_csv(Q / "hr_lindas.csv", dtype=str).fillna("")
AGRI_NAME = re.compile(r"gemüse|gemuese|landwirtschaft|bauernhof|\bhof\b|hof\s|höfe|agrar|\bbio|obst|beeren|gärtnerei|"
                       r"gaertnerei|baumschule|pflanzen|kräuter|weinbau|rebbau|weingut|milch|farm|gutsbetrieb|hofladen", re.I)
AGRI_ZWECK = re.compile(r"landwirtschaft|gemüse|gemuese|ackerbau|obstbau|tierhaltung|viehzucht|milchwirtschaft|milchproduktion|"
                        r"pflanzenbau|bauernhof|beeren|gärtnerei|gaertnerei|baumschule|jungpflanzen|setzlinge|weinbau|rebbau|"
                        r"kräuter|hofladen|gewächshaus|gemüsebau|gartenbauprodukt", re.I)
NICHT = re.compile(r"immobil|\bimmo\b|consult|trading|treuhand|praxis|liegenschaft|invest|holding|management|\bservices?\b|"
                   r"transport|garage|\bauto|elektro|informatik|software|beratung|versicherung|medizin|therapie|coiffeur|"
                   r"restaurant|gastro|hotel|bauunternehm|maler|sanitär|schreinerei|zimmerei|landmaschinen|landtechnik|"
                   r"liquidation|architekt|ingenieur|reinigung|catering|verwaltung", re.I)
hr = hr[(hr.name.str.contains(AGRI_NAME) | hr.desc.str.contains(AGRI_ZWECK)) & ~hr.name.str.contains(NICHT)]
if not args.personen:
    hr = hr[hr.typ.str.rsplit("/", n=1).str[-1].isin(JURISTISCH)]
n_hr = 0
for r in hr.itertuples():
    key = f"{strasse_key(r.str)}|{r.nr.lower().replace(' ', '')}|{r.plz[:4]}"
    if key not in GEO:
        continue
    treffer = zuordnen(*GEO[key], 60)
    if treffer or key in ADR_BETRIEB:
        n_hr += 1
        ehra = r.c.rsplit("/", 1)[1]
        verteilen(treffer, 40, adr_key=key, art="firma", name=r.name, person="",
                  detail=f"{LF.get(r.typ.rsplit('/', 1)[1], 'Firma')}, {r.str} {r.nr}, {r.plz} {r.ort}; Zweck: {r.desc[:220]}",
                  quelle="Handelsregister (Zefix, LINDAS)", url=f"https://www.zefix.ch/de/search/entity/list/firm/{ehra}")
print(f"Handelsregister: {len(hr)} Firmen mit landwirtschaftlichem Namen/Zweck, {n_hr} an einer Hofadresse")

# 2. Hofsuche SBV: Lage des Eintrags, Betriebspunkt innerhalb 200 m
sbv = json.loads((Q / "sbv_hofsuche.json").read_text(encoding="utf-8")) if args.personen else []
pts = gpd.GeoSeries(gpd.points_from_xy([s["lon"] for s in sbv], [s["lat"] for s in sbv]), crs=4326).to_crs(2056)
n_sbv = 0
for s, p in zip(sbv, pts):
    treffer = zuordnen(p.x, p.y, 150)
    m = re.match(r"^(.*?)\s+(\d+[a-zA-Z]?)\s*$", s["strasse"].strip())
    key = f"{strasse_key(m.group(1))}|{m.group(2).lower()}|{s['plz'][:4]}" if m else ""
    if not treffer and key not in ADR_BETRIEB:
        continue
    n_sbv += 1
    person = f"{s['vorname']} {s['nachname']}".strip()
    verteilen(treffer, 100, adr_key=key, art="hof", name=s["hofname"] or person, person=person,
              detail=f"{s['strasse']}, {s['plz']} {s['ort']}; {s['produktion']}; {s['kulturen']}"
                     + (f"; Labels: {s['labels']}" if s["labels"] else ""),
              quelle="Hofsuche Schweizer Bauernverband (Eintrag des Hofs)",
              url=s["website"] or f"https://www.schweizerbauern.ch/hofsuche/?id={s['id']}")
print(f"Hofsuche SBV: {len(sbv)} Höfe, {n_sbv} bei einem Betriebspunkt")

# 3. OpenStreetMap: Hofläden (Betreiber/Name) bis 120 m, Hofnamen bis 150 m
osm = json.loads((Q / "osm.json").read_text(encoding="utf-8"))["elements"]
n_osm = 0
for e in osm:
    t = e.get("tags", {})
    lat, lon = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
    p = gpd.GeoSeries([shapely.Point(lon, lat)], crs=4326).to_crs(2056).iloc[0]
    url = f"https://www.openstreetmap.org/{e['type']}/{e['id']}"
    if t.get("shop") == "farm" or t.get("amenity") == "vending_machine" or "craft" in t:
        if not args.personen:
            continue
        name = t.get("operator") or t.get("name") or ""
        if not name or name.lower() in ("hofladen", "hoflädeli", "verkaufsautomat", "milchautomat", "eierautomat"):
            continue
        treffer = zuordnen(p.x, p.y, 120)
        if treffer:
            n_osm += 1
            verteilen(treffer, 80, art="hofladen", name=name, person="",
                      detail=f"{t.get('name', '')} {('– ' + t['description']) if t.get('description') else ''}".strip()[:200],
                      quelle="OpenStreetMap (Hofladen/Betreiber)", url=url)
    elif t.get("name") and (args.personen or not PERSON_WORT.search(t["name"])):
        treffer = zuordnen(p.x, p.y, 150)
        if treffer:
            n_osm += 1
            verteilen(treffer, 100, art="hofname", name=t["name"], person="", detail="Hof- bzw. Ortsname",
                      quelle="OpenStreetMap (Hofname)", url=url)
print(f"OpenStreetMap: {len(osm)} Objekte, {n_osm} bei einem Betriebspunkt")

# 4. Bezeichnung in den Kantonsdaten (nicht ZH: dort ist es die Adresse)
for i, (b, kt) in enumerate(zip(bt.bezeichnung.fillna(""), bt.kanton_sitz)):
    if b and not re.search(r"\b\d{4}\b", b) and (args.personen or not PERSON_WORT.search(b)):
        eintrag(i, "bezeichnung", b, "", "Bezeichnung des Betriebs in den Kantonsdaten", f"Kantonsdaten {kt} (betriebsname)",
                "", 0, "amtlich")

# 5. Favoriten (config) und 6. Recherche
NR = {nr: i for i, nr in enumerate(bt.betriebsnummer)}
for f in FARMS:
    ts = teile(f)
    for nr in f["nrs"]:
        if nr not in NR:
            continue
        eigene = [t for t in ts if nr in t.get("nrs", [])]
        if eigene:
            name, detail = eigene[0]["name"], eigene[0].get("sub", "")
        elif len(ts) > 1:
            name, detail = f["name"], "Firmen: " + ", ".join(t["name"] for t in ts if not t.get("nrs"))
        else:
            name, detail = f["name"], f.get("sub", "")
        eintrag(NR[nr], "firma", name, "", detail, "config/projekt.json (geprüft, docs/betriebe.md)", "", 0, "geprüft")
rech = INTERN / "namen_recherche.csv"
if rech.exists() and args.personen:
    r = pd.read_csv(rech, dtype=str).fillna("")
    for z in r.itertuples():
        if z.betriebsnummer in NR:
            eintrag(NR[z.betriebsnummer], z.art or "recherche", z.name, z.person, z.detail, z.quelle, z.url, 0, z.sicherheit)
    print(f"Recherche: {len(r)} Einträge")

out = pd.DataFrame(zeilen).drop_duplicates(subset=["betriebsnummer", "art", "name", "quelle"])
out.to_csv(INTERN / "namen.csv", index=False)
mit = out.betriebsnummer.nunique()
mit_name = out[out.art.isin(["firma", "hof", "hofladen", "recherche"])].betriebsnummer.nunique()
print(f"{len(out)} Einträge für {mit} von {len(bt)} Betrieben; mit Firmen-/Hof-/Betreibernamen: {mit_name} -> {INTERN / 'namen.csv'}")
print(out.groupby(["art", "sicherheit"]).size().to_string())
