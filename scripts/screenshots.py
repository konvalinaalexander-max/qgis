"""Optional: Website im Headless-Browser öffnen, Screenshots machen und JS-Fehler melden.

Benötigt: pip install playwright && python -m playwright install chromium
Schreibt work/screenshots/*.png. Hintergrundkacheln erscheinen nur mit Internetzugang.
"""
import asyncio

from playwright.async_api import async_playwright

from common import WORK, out_path

SHOTS = WORK / "screenshots"
SHOTS.mkdir(exist_ok=True)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w, h, name in [(1440, 900, "desktop"), (400, 860, "handy")]:
            pg = await b.new_page(viewport={"width": w, "height": h})
            msgs = []
            pg.on("console", lambda m: msgs.append(m.type + ": " + m.text))
            pg.on("pageerror", lambda e: msgs.append("PAGEERROR: " + str(e)))
            await pg.goto(out_path("website").as_uri())
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path=str(SHOTS / f"{name}.png"))
            if name == "desktop":
                await pg.click("#m-kultur")
                await pg.wait_for_timeout(300)
                await pg.click(".row")
                await pg.wait_for_timeout(800)
                await pg.screenshot(path=str(SHOTS / "desktop_popup.png"))
                print("Liste:", await pg.inner_text("#count"))
            fehler = [m for m in msgs if "PAGEERROR" in m or (m.startswith("error") and "net::" not in m and "ERR_" not in m)]
            print(name, "JS-Fehler:", fehler or "keine")
        await b.close()
    print("Screenshots in", SHOTS)


asyncio.run(main())
