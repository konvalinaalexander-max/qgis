#!/bin/bash
# Karte der Region neu bauen: alle Betriebe mit Flächen im Gebiet (Schritte 11–16) und Online-Fassung (Schritt 6).
# Braucht ca. 3.5 GB Platz für die Downloads (data/kantone/, data/basis/) und rund 10 Minuten.
# AdR-Regionen (öffentlich): Excel-Dateien der Migros in data/adr/ (Schritt 15).
# Vertraulicher Teil (Namen): nur mit FELDKARTE_PASSWORT (mind. 16 Zeichen); ohne Passwort wird die Karte ohne Namen gebaut.
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3
run() { echo "== $*"; "$PY" "scripts/$@"; }
[ -f work/auswahl.gpkg ] || run 01_auswahl.py
run 11_kantone.py
run 12_region.py
run 13_betriebe.py
run 14_namen.py
if ls data/adr/*.xls* >/dev/null 2>&1 || ls data/intern/adr/*.xls* >/dev/null 2>&1; then run 15_adr.py
else echo "== 15_adr übersprungen (keine AdR-Listen in data/adr/)"; fi
run 16_karte.py
run 06_online.py
echo "Fertig. Ansehen: $PY scripts/server.py  →  http://localhost:8000"
echo "Online stellen: output/karte/ committen und auf main pushen."
