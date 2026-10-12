"""Website lokal ansehen: kleiner Webserver mit Range-Anfragen (nötig für die Vektorkacheln *.pmtiles).

Aufruf: python3 scripts/server.py [Ordner] [--port 8000] [--netz]
Standard-Ordner: work/online (Schritt 6), sonst output/karte. Dann im Browser http://localhost:8000 öffnen.
Braucht nur Python ohne Zusatzpakete.
"""
import argparse
import http.server
import os
import re
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        bereich = self.headers.get("Range")
        pfad = self.translate_path(self.path)
        if not bereich or not os.path.isfile(pfad):
            return super().send_head()
        groesse = os.path.getsize(pfad)
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", bereich.strip())
        if not m or m.groups() == ("", ""):
            if "," in bereich:                       # mehrere Bereiche: ganze Datei senden
                return super().send_head()
            self.send_error(416)
            return None
        a, b = m.groups()
        if a:
            start, ende = int(a), min(int(b), groesse - 1) if b else groesse - 1
        else:                                        # «bytes=-500»: die letzten 500 Bytes
            start, ende = max(0, groesse - int(b)), groesse - 1
        if start >= groesse or start > ende:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{groesse}")
            self.end_headers()
            return None
        f = open(pfad, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(pfad))
        self.send_header("Content-Range", f"bytes {start}-{ende}/{groesse}")
        self.send_header("Content-Length", str(ende - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._rest = ende - start + 1
        return f

    def copyfile(self, source, outputfile):
        rest = getattr(self, "_rest", None)
        if rest is None:
            return super().copyfile(source, outputfile)
        while rest > 0:
            stueck = source.read(min(1 << 16, rest))
            if not stueck:
                break
            outputfile.write(stueck)
            rest -= len(stueck)
        self._rest = None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ordner", nargs="?", default="")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--netz", action="store_true", help="auch von anderen Geräten im Netz erreichbar (Standard: nur dieser Computer)")
    args = ap.parse_args()
    ordner = Path(args.ordner) if args.ordner else (ROOT / "work" / "online" if (ROOT / "work" / "online" / "index.html").exists()
                                                    else ROOT / "output" / "karte")
    print(f"http://localhost:{args.port}  ({ordner})  – beenden mit Ctrl+C")
    http.server.ThreadingHTTPServer(("" if args.netz else "127.0.0.1", args.port), partial(RangeHandler, directory=str(ordner))).serve_forever()
