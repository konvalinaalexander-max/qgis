"""Gemeinsame Pfade, Konfiguration und Hilfsfunktionen für alle Skripte.

Alle Pfade sind relativ zum Projektordner, damit der Ordner verschoben werden kann.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "projekt.json").read_text(encoding="utf-8"))
GEM = json.loads((ROOT / "config" / "gemeinden.json").read_text(encoding="utf-8"))

RAW = ROOT / "data" / "raw"      # entpackte Downloads von geodienste.ch (unverändert)
WORK = ROOT / "work"             # Zwischenstände, jederzeit neu erzeugbar
OUT = ROOT / "output"            # Ergebnisse für den Gebrauch
WEB = ROOT / "web"
for d in (WORK, OUT):
    d.mkdir(exist_ok=True)

AUSWAHL = WORK / "auswahl.gpkg"
FARMS = CFG["betriebe"]
GROUPS = [g for g, _ in CFG["kulturgruppen"]]
GROUP_COLORS = dict(map(tuple, CFG["kulturgruppen"]))
NR2FARM = {n: f for f in FARMS for n in f["nrs"]}

# Bio-Status je Teilbetrieb (config: "bio" am Betrieb oder am Teilbetrieb)
#   deklariert = Betrieb meldet seine Flächen als «Bioproduktion» (Direktzahlungsprogramm)
#   firma      = Bio laut Firmenangaben (z. B. Knospe), in den Kantonsdaten aber nicht als Bio gemeldet
#   nein       = kein Bio
#   offen      = Bio-Status nicht belegt (z. B. Gewächshaus mit eigener Betriebsnummer, Betreiber unklar)
BIO_CODES = ("deklariert", "firma", "nein", "offen")


def teile(farm):
    """Teilbetriebe eines Betriebs. Ohne Eintrag «teile» ist der Betrieb selbst der einzige Teil."""
    if farm.get("teile"):
        return [dict(t, id=f"{farm['key']}-{t['key']}") for t in farm["teile"]]
    return [{"key": farm["key"], "id": farm["key"], "name": farm["name"], "kurz": farm["name"], "sub": farm.get("sub", ""),
             "bio": farm.get("bio", "nein"), "bio_text": farm.get("bio_text", ""), "color": farm["color"]}]


def teil_of(nr, ps_nr=None):
    """Betriebsnummer (+ Produktionsstätte der Bewirtschaftungseinheit) -> Teilbetrieb (dict mit «id»).

    Ein Teil passt, wenn die Betriebsnummer in «nrs» oder die Produktionsstätte in «ps» steht; sonst greift
    der Teil mit «rest»: true. Passt nichts, ist die Konfiguration unvollständig (Fehler)."""
    farm = NR2FARM[nr]
    ts = teile(farm)
    if len(ts) == 1 and not farm.get("teile"):
        return ts[0]
    for t in ts:
        if nr in t.get("nrs", []) or (ps_nr and ps_nr in t.get("ps", [])):
            return t
    for t in ts:
        if t.get("rest"):
            return t
    raise ValueError(f"Keine Zuordnung zu einem Teilbetrieb: {farm['name']} {nr!r} Produktionsstätte {ps_nr!r} – config/projekt.json ergänzen")


def bio_status(programm, teil):
    """Bio-Status einer Fläche: «bio» (als Bioproduktion gemeldet), «bio_betrieb» (Bio-Betrieb bzw. Bio laut
    Firma, Fläche aber nicht als Bio gemeldet – z. B. Wald, Gewächshäuser mit festem Fundament), «offen»
    (Bio-Status des Teilbetriebs nicht belegt) oder «nein»."""
    if isinstance(programm, str) and "Bioproduktion" in programm:
        return "bio"
    if teil.get("bio") == "offen":
        return "offen"
    return "bio_betrieb" if teil.get("bio") in ("deklariert", "firma") else "nein"


BIO_LABELS = {"bio": "Bio (gemeldet)", "bio_betrieb": "Bio-Betrieb, Fläche nicht als Bio gemeldet", "nein": "nicht Bio",
              "offen": "Bio-Status unklar"}
for _f in FARMS:
    for _t in teile(_f):
        if _t["bio"] not in BIO_CODES:
            raise ValueError(f"config/projekt.json: «bio» von {_t['name']} muss eines von {BIO_CODES} sein, nicht {_t['bio']!r}")


def out_path(kind):
    """kind: website | excel | gpkg | qgis"""
    return OUT / CFG["dateinamen"][kind]


RAW_ZIP = ROOT / "data" / "raw_zip"  # dieselben Downloads gezippt (so im Git-Repository abgelegt)


def raw_gpkg(art, kt):
    """art: 'bewirtschaftungseinheit' oder 'nutzungsflaechen'; kt: 'ZH', 'TG', ...

    Fehlt der entpackte Ordner in data/raw/, wird er aus data/raw_zip/<ordner>.zip entpackt.
    """
    v = CFG["kantone"][kt]
    name = f"lwb_{art}_{v}_{kt}"
    folder = f"{name}_gpkg_lv95"
    path = RAW / folder / "geopackage" / f"{name}_2056.gpkg"
    z = RAW_ZIP / f"{folder}.zip"
    if not path.exists() and z.exists():
        import zipfile
        RAW.mkdir(parents=True, exist_ok=True)
        print(f"entpacke {z.name} -> data/raw/")
        with zipfile.ZipFile(z) as zf:
            zf.extractall(RAW)
    return path


def gemeinde(bfs):
    """BFS-Nummer -> (Gemeindename, Kanton). Unbekannte Nummern: ('BFS 1234', '')."""
    try:
        key = str(int(bfs))
    except (TypeError, ValueError):
        return ("?", "")
    name, kt = GEM.get(key, (f"BFS {key}", ""))
    return name, kt


def kantone_text(kts):
    """['ZH','TG'] -> 'Kantone Zürich und Thurgau'"""
    names = [CFG["kantonsnamen"].get(k, k) for k in kts]
    if len(names) == 1:
        return f"Kanton {names[0]}"
    return "Kantone " + ", ".join(names[:-1]) + " und " + names[-1]


def kulturgruppe(code, name):
    """LNF-Code + Nutzungsbezeichnung -> eine der 9 Kulturgruppen (Reihenfolge der Regeln ist wichtig)."""
    code = int(code)
    n = str(name).lower()
    if "unproduktiv" in n:
        return "Wald & übrige Flächen"
    if "gewürz" in n:
        return "Beeren & Spezialkulturen"
    if code in (545, 546, 547):
        return "Freilandgemüse"
    if 800 <= code <= 849:
        return "Gewächshaus / geschützt"
    if code in (524, 525):
        return "Kartoffeln"
    if any(k in n for k in ["extensiv", "wenig intensiv", "hecken", "buntbrache", "rotationsbrache", "saum",
                            "nützlingsstreifen", "streuefl", "ruderal", "wassergräben", "uferwiese", "hochstamm"]):
        return "Biodiversitätsfläche"
    if "beeren" in n or "rhabarber" in n or 700 <= code <= 799:
        return "Beeren & Spezialkulturen"
    if code in (601, 602):
        return "Kunstwiese"
    if 600 <= code <= 699:
        return "Dauerwiese / Weide"
    if 500 <= code <= 599:
        return "Ackerkulturen"
    return "Wald & übrige Flächen"


def programme(s):
    """'Bio;Kein Programm;…' -> Liste ohne 'Kein Programm'."""
    if not isinstance(s, str) or not s.strip():
        return []
    return [p.strip() for p in s.split(";") if p.strip() and p.strip() != "Kein Programm"]
