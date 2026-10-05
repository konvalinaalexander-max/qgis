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
