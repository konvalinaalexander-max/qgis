"""Schritt 5: QGIS-Projekt erzeugen (PyQGIS).

Schreibt output/<dateinamen.qgis> mit
  - Gruppe «Auswahl Betriebe»: Flächen nach Betrieb / nach Kultur, Betriebsstandorte
  - Gruppe «Alle Betriebe …»: je Kanton ein Layer «Betrieb hervorheben XX (Variable @betrieb)»
    (regelbasiert: Flächen der Betriebsnummer in der Projektvariable @betrieb rot, Rest nur nah sichtbar)
    plus ausgeblendete Nutzungsflächen aller Betriebe je Kanton
  - Gruppe «Hintergrund swisstopo»: Luftbild (bis z20) und Landeskarte (bis z19) als XYZ-Kacheln

Ausführen – zwei Wege:
  A) In QGIS: Erweiterungen → Python-Konsole → Editor anzeigen → diese Datei öffnen → Ausführen.
     Das offene Projekt bleibt unverändert; die neue Datei danach über Projekt → Öffnen laden.
  B) Ohne QGIS-Oberfläche mit dem Python, das QGIS mitbringt (Pfad siehe CLAUDE.md).
Benötigt vorher: Schritt 1 und 3 (work/auswahl.gpkg ist nicht nötig, aber output/*.gpkg schon).
"""
import os
import re
import zipfile
from pathlib import Path

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:  # in der QGIS-Python-Konsole ist __file__ nicht immer gesetzt
    ROOT = Path(os.environ.get("FELDKARTE_DIR", Path.home() / "Downloads" / "Feldkarte-Projekt"))

import json

from qgis.core import (QgsApplication, QgsCategorizedSymbolRenderer, QgsCoordinateReferenceSystem,
                       QgsExpressionContextUtils, QgsFillSymbol, QgsMarkerSymbol, QgsPalLayerSettings, QgsProject,
                       QgsRasterLayer, QgsReferencedRectangle, QgsRendererCategory, QgsRuleBasedRenderer,
                       QgsSingleSymbolRenderer, QgsTextBufferSettings, QgsTextFormat, QgsVectorLayer,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtGui import QColor

standalone = QgsApplication.instance() is None
if standalone:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QgsApplication([], False)
    app.initQgis()

CFG = json.loads((ROOT / "config" / "projekt.json").read_text(encoding="utf-8"))
OUT = ROOT / "output"
RAW = ROOT / "data" / "raw"
FARMS = CFG["betriebe"]
FARM_COL = {f["name"]: f["color"] for f in FARMS}
GROUP_COL = CFG["kulturgruppen"]
NEU = ", ".join(CFG["kantone"])

proj = QgsProject()  # neues, leeres Projekt (berührt ein in QGIS offenes Projekt nicht)
proj.setCrs(QgsCoordinateReferenceSystem("EPSG:2056"))
proj.setTitle(f"{CFG['titel']} – lokal ({NEU})")
proj.writeEntryBool("Paths", "/Absolute", False)
QgsExpressionContextUtils.setProjectVariable(proj, "betrieb", CFG["qgis_startbetrieb"])


def darker(h, f=0.72):
    c = QColor(h)
    return QColor(int(c.red() * f), int(c.green() * f), int(c.blue() * f)).name()


def fill(color, alpha=115, outline=None, width="0.4"):
    c = QColor(color)
    return QgsFillSymbol.createSimple({"color": f"{c.red()},{c.green()},{c.blue()},{alpha}",
                                       "outline_color": outline or darker(color), "outline_width": width})


def vec(path, layer, name):
    lyr = QgsVectorLayer(f"{path}|layername={layer}", name, "ogr")
    assert lyr.isValid(), (str(path), layer)
    return lyr


def raw_gpkg(art, kt):
    v = CFG["kantone"][kt]
    name = f"lwb_{art}_{v}_{kt}"
    folder = f"{name}_gpkg_lv95"
    path = RAW / folder / "geopackage" / f"{name}_2056.gpkg"
    z = ROOT / "data" / "raw_zip" / f"{folder}.zip"
    if not path.exists() and z.exists():  # aus dem Git-Repository: gezippte Rohdaten zuerst entpacken
        RAW.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(RAW)
    return path


root = proj.layerTreeRoot()
g_sel = root.addGroup("Auswahl Betriebe")
g_all = root.addGroup(f"Alle Betriebe {' · '.join(CFG['kantone'])} (lokal, {CFG['stand'].split(' · ')[0]})")
g_bg = root.addGroup("Hintergrund swisstopo")
layers = []  # (layer, gruppe, sichtbar)

# --- Auswahl ---
sel_path = OUT / CFG["dateinamen"]["gpkg"]
l_farm = vec(sel_path, "flaechen", "Flächen nach Betrieb")
l_farm.setRenderer(QgsCategorizedSymbolRenderer("betrieb",
    [QgsRendererCategory(k, fill(v, 120, width="0.5"), k) for k, v in FARM_COL.items()]))
l_kult = vec(sel_path, "flaechen", "Flächen nach Kultur")
l_kult.setRenderer(QgsCategorizedSymbolRenderer("kulturgruppe",
    [QgsRendererCategory(k, fill(v, 160, outline="#333333", width="0.3"), k) for k, v in GROUP_COL]))
l_pt = vec(sel_path, "betriebsstandorte", "Betriebsstandorte")
l_pt.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple(
    {"name": "star", "color": "255,255,255", "outline_color": "30,30,30", "size": "4.5"})))
erste = ", ".join("'" + f["nrs"][0] + "'" for f in FARMS)   # Beschriftung nur am ersten Standort je Betrieb
lab = QgsPalLayerSettings()
lab.fieldName = f"CASE WHEN \"betriebsnummer\" IN ({erste}) THEN \"betrieb\" ELSE '' END"
lab.isExpression = True
lab.enabled = True
tf = QgsTextFormat()
tf.setSize(10)
buf = QgsTextBufferSettings()
buf.setEnabled(True)
buf.setSize(1)
tf.setBuffer(buf)
lab.setFormat(tf)
l_pt.setLabeling(QgsVectorLayerSimpleLabeling(lab))
l_pt.setLabelsEnabled(True)
layers += [(l_pt, g_sel, False), (l_farm, g_sel, True), (l_kult, g_sel, False)]

# --- Alle Betriebe je Kanton ---
be_layers, nf_layers = [], []
for kt in CFG["kantone"]:
    pb, pn = raw_gpkg("bewirtschaftungseinheit", kt), raw_gpkg("nutzungsflaechen", kt)
    if not pb.exists():
        print(f"[{kt}] Rohdaten fehlen – Kanton wird im QGIS-Projekt weggelassen")
        continue
    l_be = vec(pb, "bewirtschaftungseinheit", f"Betrieb hervorheben {kt} (Variable @betrieb)")
    rr = QgsRuleBasedRenderer.Rule(None)
    r_sel = QgsRuleBasedRenderer.Rule(fill("#FF2D2D", 150, outline="#FFFFFF", width="0.45"),
                                      filterExp="replace(\"betriebsnummer\", ' ', '') = replace(@betrieb, ' ', '')",
                                      label="Gewählter Betrieb")
    r_else = QgsRuleBasedRenderer.Rule(QgsFillSymbol.createSimple(
        {"style": "no", "outline_color": "255,255,255,170", "outline_width": "0.2"}), label="Übrige Betriebe (nur nah sichtbar)")
    r_else.setIsElse(True)
    r_else.setMaximumScale(1)
    r_else.setMinimumScale(30000)
    rr.appendChild(r_sel)
    rr.appendChild(r_else)
    l_be.setRenderer(QgsRuleBasedRenderer(rr))
    be_layers.append((l_be, g_all, True))
    l_nf = vec(pn, "nutzungsflaechen", f"Nutzungsflächen {kt} (alle Betriebe)")
    l_nf.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(
        {"color": "255,255,255,0", "outline_color": "255,230,120,200", "outline_width": "0.25"})))
    l_nf.setScaleBasedVisibility(True)
    l_nf.setMinimumScale(25000)
    l_nf.setMaximumScale(1)
    nf_layers.append((l_nf, g_all, False))
layers += be_layers + nf_layers


# --- Hintergrund ---
def xyz(layer, name, zmax):
    url = f"https://wmts.geo.admin.ch/1.0.0/{layer}/default/current/3857/{{z}}/{{x}}/{{y}}.jpeg"
    return QgsRasterLayer(f"type=xyz&url={url}&zmax={zmax}&zmin=0", name, "wms")


layers += [(xyz("ch.swisstopo.swissimage", "swisstopo Luftbild", 20), g_bg, True),
           (xyz("ch.swisstopo.pixelkarte-farbe", "swisstopo Landeskarte", 19), g_bg, False)]

for lyr, grp, vis in layers:
    proj.addMapLayer(lyr, False)
    grp.addLayer(lyr).setItemVisibilityChecked(vis)

ext = l_farm.extent()
ext.scale(1.05)
proj.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(ext, proj.crs()))
out = OUT / CFG["dateinamen"]["qgis"]
ok = proj.write(str(out))

# Pfade sicher relativ machen (falls Ordner über Symlinks eingebunden sind, schreibt QGIS absolute Pfade)
tmp = out.with_suffix(".tmp")
with zipfile.ZipFile(out) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename.endswith(".qgs"):
            s = data.decode("utf-8")
            s = re.sub(r'[^"<>|]*?/(lwb_[^/"<>|]+_gpkg_lv95/geopackage/)', r"../data/raw/\1", s)
            s = re.sub(r'[^"<>|]*?/(' + re.escape(CFG["dateinamen"]["gpkg"]) + ")", r"./\1", s)
            data = s.encode("utf-8")
        zout.writestr(item, data)
tmp.replace(out)
print("geschrieben:", ok, out)

if standalone:
    app.exitQgis()
