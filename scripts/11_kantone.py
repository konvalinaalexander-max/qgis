"""Schritt 11: Daten für die Region herunterladen (alles nicht im Git, ca. 3.5 GB).

Schreibt
  data/kantone/<KT>/   Nutzungsflächen + Bewirtschaftungseinheiten aller Kantone, die geodienste.ch frei abgibt
                       (ausser den Projektkantonen in config «kantone», die liegen in data/raw/)
  data/basis/          swisstopo: Gemeindegrenzen (swissBOUNDARIES3D), PLZ-Gebiete (Ortschaftenverzeichnis),
                       Gebäudeadressen (amtliches Gebäudeadressverzeichnis)

Warum alle Kantone: Ein Betrieb meldet alle Flächen seinem Sitzkanton. Felder im Gebiet, die ein Betrieb aus
dem Aargau oder aus Luzern bewirtschaftet, stehen deshalb nur im Datensatz AG bzw. LU.
Nicht frei erhältlich (Registrierung/Freigabe nötig) sind NE (Nutzungsflächen), TI, NW, OW, VD.

Aufruf: python3 scripts/11_kantone.py [--neu]   (--neu: vorhandene Downloads ersetzen)
"""
import argparse
import json
import shutil
import urllib.request
import zipfile

from common import BASIS, CFG, KANTONE_DIR, kanton_gpkg

ap = argparse.ArgumentParser()
ap.add_argument("--neu", action="store_true", help="vorhandene Downloads ersetzen")
args = ap.parse_args()

THEMEN = ("lwb_nutzungsflaechen", "lwb_bewirtschaftungseinheit")
DIENSTE = "https://www.geodienste.ch/info/services.json?base_topics=" + ",".join(THEMEN) + "&language=de"
BASIS_URLS = [
    "https://data.geo.admin.ch/ch.swisstopo.swissboundaries3d/swissboundaries3d_2026-01/"
    "swissboundaries3d_2026-01_2056_5728.gpkg.zip",
    "https://data.geo.admin.ch/ch.swisstopo-vd.ortschaftenverzeichnis_plz/ortschaftenverzeichnis_plz/"
    "ortschaftenverzeichnis_plz_2056.shp.zip",
    "https://data.geo.admin.ch/ch.swisstopo.amtliches-gebaeudeadressverzeichnis/amtliches-gebaeudeadressverzeichnis_ch/"
    "amtliches-gebaeudeadressverzeichnis_ch_2056.csv.zip",
]


def laden(url, ziel):
    if ziel.exists() and ziel.stat().st_size and not args.neu:
        return False
    ziel.parent.mkdir(parents=True, exist_ok=True)
    teil = ziel.with_suffix(ziel.suffix + ".part")
    with urllib.request.urlopen(url, timeout=600) as r, open(teil, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    teil.rename(ziel)
    return True


def entpacken(z, ordner):
    with zipfile.ZipFile(z) as zf:
        zf.extractall(ordner)


dienste = json.load(urllib.request.urlopen(DIENSTE, timeout=60))["services"]
gesperrt = sorted({f"{s['canton']} ({s['base_topic'].split('_')[1]}: {s['publication_data']})"
                   for s in dienste if s["publication_data"] != "Frei erhältlich"})
for s in sorted(dienste, key=lambda s: (s["canton"], s["base_topic"])):
    kt = s["canton"]
    if kt in CFG["kantone"] or s["publication_data"] != "Frei erhältlich":
        continue
    datei = f"{s['topic']}_{kt}_gpkg_lv95.zip"
    url = f"https://www.geodienste.ch/downloads/geopackage/{s['base_topic']}/{kt}/deu/{datei}"
    z = KANTONE_DIR / kt / datei
    neu = laden(url, z)
    if neu or not kanton_gpkg(s["base_topic"].replace("lwb_", ""), kt):
        entpacken(z, KANTONE_DIR / kt)
    print(f"{kt} {s['base_topic']:<28} {'geladen' if neu else 'vorhanden'} ({z.stat().st_size / 1e6:.0f} MB, Stand {s['updated_at'][:10]})")

for url in BASIS_URLS:
    z = BASIS / url.rsplit("/", 1)[1]
    neu = laden(url, z)
    ordner = BASIS / z.name[:-4]
    if neu or not ordner.exists():
        entpacken(z, ordner)
    print(f"Basis {z.name}: {'geladen' if neu else 'vorhanden'} ({z.stat().st_size / 1e6:.0f} MB)")

print("Nicht frei erhältlich (fehlen in der Region):", ", ".join(gesperrt) or "–")
