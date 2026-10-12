#!/bin/bash
# Karte der Region neu bauen: alle Betriebe mit Flächen im Gebiet (Schritte 11–16) und Online-Fassung (Schritt 6).
# Braucht ca. 3.5 GB Platz für die Downloads (data/kantone/, data/basis/) und rund 10 Minuten.
# Vertraulicher Teil (Namen, interne Regionen): nur mit FELDKARTE_PASSWORT (mind. 16 Zeichen) und den Dateien in
# data/intern/ (Regionsdefinitionen in data/intern/adr/). Ohne Passwort wird die Karte ohne diesen Teil gebaut.
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
if ls data/intern/adr/*.xls* >/dev/null 2>&1; then run 15_adr.py; else echo "== 15_adr übersprungen (keine Regionsdefinitionen in data/intern/adr/)"; fi
run 16_karte.py
run 06_online.py
echo "Fertig. Ansehen: $PY scripts/server.py  →  http://localhost:8000"
echo "Online stellen: output/karte/ committen und auf main pushen."
