#!/bin/bash
# Baut Website, GeoPackage und Excel neu (Schritte 1–4).
# Das QGIS-Projekt (Schritt 5) braucht PyQGIS und läuft separat, siehe CLAUDE.md.
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3
for s in 01_auswahl 02_website 03_gpkg 04_excel; do
  echo "== $s"
  "$PY" "scripts/$s.py"
done
echo "Fertig. Ergebnisse in output/. QGIS-Projekt separat: scripts/05_qgis_projekt.py"
