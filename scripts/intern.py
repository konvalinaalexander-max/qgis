"""Vertrauliche Daten verschlüsseln (Repo und Website sind öffentlich).

Vertraulich sind die internen Regionsdefinitionen (data/intern/adr/) und die zugeordneten Namen (data/intern/namen.csv,
data/intern/quellen/). Sie liegen unverschlüsselt nur in data/intern/ (nicht im Git). Auf die Website kommt nur die
verschlüsselte Datei intern.bin (Schritt 16). Eine Sicherung von data/intern/ (data/intern.enc) bleibt ebenfalls
ausserhalb des Git – sie gehört auf einen privaten Speicher, nicht in das öffentliche Repo.

Verfahren (wie im Browser mit WebCrypto): PBKDF2-HMAC-SHA256 (600'000 Runden, 16 Byte Salz) -> AES-256-GCM
(12 Byte IV). Datei = «FKv2» + Runden (4 Byte) + Salz + IV + Chiffretext mit Prüfsumme; Kennung und Runden sind
als Zusatzdaten mitgeschützt. Passwort aus der Umgebungsvariable FELDKARTE_PASSWORT (oder Eingabe), mindestens
16 Zeichen.

Aufruf: python3 scripts/intern.py sichern     data/intern/ -> data/intern.enc
        python3 scripts/intern.py entpacken   data/intern.enc -> data/intern/
"""
import getpass
import hashlib
import io
import os
import struct
import sys
import tarfile

from common import INTERN, ROOT

KENNUNG = b"FKv2"
RUNDEN = 600_000
MIN_LAENGE = 16
SICHERUNG = ROOT / "data" / "intern.enc"


def passwort():
    p = os.environ.get("FELDKARTE_PASSWORT") or ""
    if not p and sys.stdin.isatty():
        p = getpass.getpass("Passwort für die vertraulichen Daten: ")
    return p


def pruefen(pw):
    if len(pw) < MIN_LAENGE:
        raise SystemExit(f"Passwort zu kurz: mindestens {MIN_LAENGE} Zeichen (z. B. vier zufällige Wörter).")


def _schluessel(pw, salz, runden):
    return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salz, runden, 32)


def verschluesseln(daten, pw):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    pruefen(pw)
    kopf = KENNUNG + struct.pack(">I", RUNDEN)
    salz, iv = os.urandom(16), os.urandom(12)
    return kopf + salz + iv + AESGCM(_schluessel(pw, salz, RUNDEN)).encrypt(iv, daten, kopf)


def entschluesseln(blob, pw):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if blob[:4] != KENNUNG:
        raise ValueError("keine verschlüsselte Feldkarte-Datei (Kennung FKv2)")
    kopf, runden = blob[:8], struct.unpack(">I", blob[4:8])[0]
    salz, iv = blob[8:24], blob[24:36]
    return AESGCM(_schluessel(pw, salz, runden)).decrypt(iv, blob[36:], kopf)


if __name__ == "__main__":
    befehl = sys.argv[1] if len(sys.argv) > 1 else ""
    if befehl not in ("sichern", "entpacken"):
        raise SystemExit(__doc__)
    pw = passwort()
    if befehl == "sichern":
        puffer = io.BytesIO()
        with tarfile.open(fileobj=puffer, mode="w:gz") as tar:
            tar.add(INTERN, arcname="intern")
        SICHERUNG.write_bytes(verschluesseln(puffer.getvalue(), pw))
        print(f"{SICHERUNG} ({SICHERUNG.stat().st_size / 1e6:.1f} MB) – nicht ins Git, privat aufbewahren")
    else:
        daten = entschluesseln(SICHERUNG.read_bytes(), pw)
        with tarfile.open(fileobj=io.BytesIO(daten), mode="r:gz") as tar:
            tar.extractall(INTERN.parent, filter="data")
        print(f"entpackt nach {INTERN}")
