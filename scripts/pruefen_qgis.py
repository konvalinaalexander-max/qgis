"""Prüft das erzeugte QGIS-Projekt: alle Layer gültig, Pfade relativ, @betrieb-Hervorhebung trifft.

Ausführen wie 05_qgis_projekt.py (QGIS-Python-Konsole oder QGIS-Python).
"""
import json
import os
import zipfile
from pathlib import Path

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:
    ROOT = Path(os.environ.get("FELDKARTE_DIR", Path.home() / "Downloads" / "Feldkarte-Projekt"))

from qgis.core import (QgsApplication, QgsExpression, QgsExpressionContext, QgsExpressionContextScope,
                       QgsExpressionContextUtils, QgsFeatureRequest, QgsProject)

standalone = QgsApplication.instance() is None
if standalone:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QgsApplication([], False)
    app.initQgis()

CFG = json.loads((ROOT / "config" / "projekt.json").read_text(encoding="utf-8"))
path = ROOT / "output" / CFG["dateinamen"]["qgis"]

with zipfile.ZipFile(path) as z:
    qgs = z.read([n for n in z.namelist() if n.endswith(".qgs")][0]).decode("utf-8")
absolut = [l for l in qgs.splitlines() if "datasource>/" in l or 'source="/' in l]
print("absolute Pfade:", len(absolut))

p = QgsProject()
print("gelesen:", p.read(str(path)))
fehler = 0
for l in p.mapLayers().values():
    n = l.featureCount() if hasattr(l, "featureCount") else "-"
    fehler += 0 if l.isValid() else 1
    print(f"  {l.name():48s} gültig={l.isValid()}  Objekte={n}")

for f in CFG["betriebe"]:
    for nr in f["nrs"]:
        res = []
        for be in [l for l in p.mapLayers().values() if l.name().startswith("Betrieb hervorheben")]:
            sc = QgsExpressionContextScope()
            sc.setVariable("betrieb", nr)
            ctx = QgsExpressionContext()
            ctx.appendScopes([QgsExpressionContextUtils.globalScope(), QgsExpressionContextUtils.projectScope(p),
                              QgsExpressionContextUtils.layerScope(be), sc])
            req = QgsFeatureRequest(QgsExpression("replace(\"betriebsnummer\", ' ', '') = replace(@betrieb, ' ', '')"))
            req.setExpressionContext(ctx)
            fs = list(be.getFeatures(req))
            if fs:
                res.append(f"{be.name()[20:22]}: {len(fs)} BE / {round(sum(x['flaeche_m2'] for x in fs) / 1e4, 2)} ha")
        print(f"  @betrieb = {nr!r:18s} ({f['name']}): {', '.join(res) or 'KEIN TREFFER'}")

print("OK" if fehler == 0 and not absolut else "PROBLEME GEFUNDEN")
if standalone:
    app.exitQgis()
