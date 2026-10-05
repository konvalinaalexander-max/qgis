"""Optional: App-Icons für die Online-Fassung aus web/online/icon.svg erzeugen (braucht Playwright).

Schreibt web/online/icon-192.png, icon-512.png (abgerundet), icon-maskable-512.png und
apple-touch-icon.png (randlos; Android bzw. iOS runden selbst ab, Inhalt in der sicheren Mitte).
Nur nötig, wenn icon.svg geändert wurde. Das Favicon der Website liest 02_website.py direkt aus icon.svg.
"""
import asyncio

from playwright.async_api import async_playwright

from common import WEB

ONLINE = WEB / "online"
SVG = (ONLINE / "icon.svg").read_text(encoding="utf-8").strip()
RANDLOS = SVG.replace('rx="14"', 'rx="0"').replace("<g ", '<g transform="translate(32 32) scale(.8) translate(-32 -32)" ', 1)
JOBS = [("icon-192.png", 192, SVG), ("icon-512.png", 512, SVG),
        ("icon-maskable-512.png", 512, RANDLOS), ("apple-touch-icon.png", 180, RANDLOS)]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, size, svg in JOBS:
            pg = await b.new_page(viewport={"width": size, "height": size})
            gross = svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{gross}</body></html>')
            await pg.screenshot(path=str(ONLINE / name), omit_background=True)
            await pg.close()
            print("geschrieben:", ONLINE.relative_to(WEB.parent) / name)
        await b.close()


asyncio.run(main())
