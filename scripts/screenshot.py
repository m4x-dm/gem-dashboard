"""Zrzut ekranu strony Streamlit przez Chrome DevTools Protocol (czeka na render).

Uzycie: python shot.py URL OUT.png [szerokosc] [wysokosc] [sekundy_czekania]
"""
import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request

from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
url, out = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
h = int(sys.argv[4]) if len(sys.argv) > 4 else 1600
wait = float(sys.argv[5]) if len(sys.argv) > 5 else 25
port = 9333

prof = tempfile.mkdtemp()
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", f"--remote-debugging-port={port}",
                         f"--user-data-dir={prof}", f"--window-size={w},{h}", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try:
            targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
            page = next(t for t in targets if t["type"] == "page")
            break
        except Exception:
            time.sleep(0.2)

    async def run():
        ws = await websocket_connect(page["webSocketDebuggerUrl"], max_message_size=200 * 1024 * 1024)
        mid = 0

        async def call(method, params=None):
            nonlocal mid
            mid += 1
            ws.write_message(json.dumps({"id": mid, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await ws.read_message())
                if msg.get("id") == mid:
                    return msg.get("result", {})

        await call("Emulation.setDeviceMetricsOverride",
                   {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": w < 600})
        await call("Page.navigate", {"url": url})
        deadline = time.time() + wait
        # Gotowe = brak widgetu statusu i spinnerow, a tekst strony stoi >= 8 s.
        # (Sam brak stStatusWidget nie wystarcza — w ukladzie z gornym menu bywa
        # nieobecny w trakcie dzialania skryptu i zrzut lapal niedokonczona strone.)
        last_len, stable = -1, 0
        while time.time() < deadline:
            r = await call("Runtime.evaluate", {"expression":
                "(document.querySelector('[data-testid=\"stStatusWidget\"]') === null && "
                "document.querySelector('[data-testid=\"stSpinner\"]') === null && "
                "document.querySelectorAll('[data-testid=\"stMarkdownContainer\"]').length > 2)"
                " ? document.body.innerText.length : -1",
                "returnByValue": True})
            cur = r.get("result", {}).get("value", -1)
            stable = stable + 1 if cur >= 0 and cur == last_len else 0
            last_len = cur
            if stable >= 8:
                break
            await __import__("asyncio").sleep(1)
        await __import__("asyncio").sleep(2)
        shot = await call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        open(out, "wb").write(base64.b64decode(shot["data"]))
        print("saved", out)

    IOLoop.current().run_sync(run, timeout=wait + 60)
finally:
    proc.kill()
