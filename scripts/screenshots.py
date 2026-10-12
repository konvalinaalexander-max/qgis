"""Optional: Website im Headless-Browser prüfen – Screenshots Desktop/Handy, Bedienung, JS-Fehler.

Benötigt: pip install playwright && python -m playwright install chromium
Schreibt work/screenshots/*.png. Hintergrundkacheln erscheinen nur mit Internetzugang.

  python scripts/screenshots.py              Screenshots + Prüfung der Bedienung
  python scripts/screenshots.py --vorschau   zusätzlich web/online/vorschau.jpg neu erzeugen
                                             (Bild für die Link-Vorschau in WhatsApp, Mail usw.): die Karte der
                                             Region (output/karte, über scripts/server.py), Favoriten farbig
"""
import asyncio
import socket
import subprocess
import sys
import time

from playwright.async_api import async_playwright

from common import OUT, ROOT, WEB, WORK, out_path

SHOTS = WORK / "screenshots"
SHOTS.mkdir(exist_ok=True)
URL = out_path("website").as_uri()


def fehlerliste(msgs):
    return [m for m in msgs if "PAGEERROR" in m or (m.startswith("error") and "net::" not in m and "ERR_" not in m)]


async def seite(b, **ctx):
    c = await b.new_context(**ctx)
    pg = await c.new_page()
    msgs = []
    pg.on("console", lambda m: msgs.append(m.type + ": " + m.text))
    pg.on("pageerror", lambda e: msgs.append("PAGEERROR: " + str(e)))
    await pg.goto(URL)
    await pg.wait_for_timeout(2000)
    return c, pg, msgs


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()

        c, pg, msgs = await seite(b, viewport={"width": 1440, "height": 900})
        await pg.screenshot(path=str(SHOTS / "desktop.png"))
        await pg.click("#m-kultur")
        await pg.click("#t-flaechen")
        await pg.click("#list .row")
        await pg.wait_for_timeout(1200)
        await pg.screenshot(path=str(SHOTS / "desktop_popup.png"))
        print("Desktop – Liste:", await pg.inner_text("#count"), "| Popup offen:", await pg.locator(".leaflet-popup").count() == 1)
        print("Desktop – JS-Fehler:", fehlerliste(msgs) or "keine")
        await c.close()

        c, pg, msgs = await seite(b, viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        await pg.screenshot(path=str(SHOTS / "handy.png"))
        await pg.tap("#t-flaechen")
        await pg.wait_for_timeout(500)
        await pg.tap("#list .row")
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(SHOTS / "handy_details.png"))
        offen = not await pg.locator("#p-detail").is_hidden()
        await pg.go_back()
        await pg.wait_for_timeout(600)
        zu = await pg.locator("#p-detail").is_hidden()
        print("Handy – Details offen:", offen, "| nach Zurück geschlossen:", zu)
        print("Handy – JS-Fehler:", fehlerliste(msgs) or "keine")
        await c.close()

        if "--vorschau" in sys.argv:
            # Startseite online ist die Karte der Region: sie braucht einen Webserver mit Range-Anfragen
            with socket.socket() as so:
                so.bind(("127.0.0.1", 0))
                port = so.getsockname()[1]
            server = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "server.py"), str(OUT / "karte"), "--port", str(port)],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(50):
                    try:
                        socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                        break
                    except OSError:
                        time.sleep(0.2)
                c = await b.new_context(viewport={"width": 1200, "height": 630})
                pg = await c.new_page()
                await pg.goto(f"http://127.0.0.1:{port}/")
                await pg.wait_for_function("!!window.feldkarte", timeout=60000)
                await pg.evaluate("document.querySelector('#favon').click()")                  # Favoriten farbig
                await pg.evaluate("window.feldkarte.map.jumpTo({center: [8.735, 47.43], zoom: 10.6})")  # Zürich–Winterthur
                await pg.wait_for_function("window.feldkarte.map.loaded()", timeout=60000)
                await pg.wait_for_timeout(2500)
                await pg.mouse.move(1190, 620)
                ziel = WEB / "online" / "vorschau.jpg"
                await pg.screenshot(path=str(ziel), type="jpeg", quality=82)
                print("Vorschaubild:", ziel.relative_to(WEB.parent))
                await c.close()
            finally:
                server.terminate()

        await b.close()
    print("Screenshots in", SHOTS)


asyncio.run(main())
