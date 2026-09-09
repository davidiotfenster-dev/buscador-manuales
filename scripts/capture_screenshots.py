import asyncio
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = r"c:\Users\david.paredes\Documents\buscador-manuales\docs\screenshots"

os.makedirs(OUTPUT_DIR, exist_ok=True)
msg_id = 0

def log(msg):
    print(msg, flush=True)

async def send_cmd(ws, method, params=None):
    global msg_id
    msg_id += 1
    req_id = msg_id
    payload = {"id": req_id, "method": method}
    if params:
        payload["params"] = params
    await ws.send(json.dumps(payload))
    while True:
        try:
            resp_raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
            resp = json.loads(resp_raw)
            if resp.get("id") == req_id:
                if "error" in resp:
                    log(f"Error in {method}: {resp['error']}")
                return resp.get("result", {})
        except asyncio.TimeoutError:
            log(f"Timeout waiting for response to {method} (id={req_id})")
            return {}

async def eval_js(ws, expr):
    return await send_cmd(ws, "Runtime.evaluate", {
        "expression": expr,
        "awaitPromise": True,
        "returnByValue": True
    })

async def capture_screenshot(ws, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    result = await send_cmd(ws, "Page.captureScreenshot", {
        "format": "png",
        "captureBeyondViewport": False
    })
    data = result.get("data")
    if data:
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(data))
        log(f"[OK] Captured: {filename} ({os.path.getsize(filepath)} bytes)")
    else:
        log(f"[FAIL] Failed to capture: {filename}")

async def run():
    temp_dir = tempfile.mkdtemp()
    cmd = [
        CHROME_PATH,
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--disable-extensions",
        "--headless=new",
        "--window-size=1440,900",
        "--hide-scrollbars",
        f"--user-data-dir={temp_dir}",
        "about:blank"
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(2)

    try:
        tabs_raw = urllib.request.urlopen("http://127.0.0.1:9222/json").read()
        tabs = json.loads(tabs_raw)
        pages = [t for t in tabs if t.get("type") == "page"]
        if not pages:
            log("No page tab found!")
            return
        ws_url = pages[0]["webSocketDebuggerUrl"]
        log(f"Connecting to CDP Page: {ws_url}")

        async with websockets.connect(ws_url, max_size=50*1024*1024) as ws:
            await send_cmd(ws, "Page.enable")
            await send_cmd(ws, "Runtime.enable")

            # 1. Login Page
            log("\n1. Navigating to http://localhost:8000...")
            await send_cmd(ws, "Page.navigate", {"url": "http://localhost:8000"})
            await asyncio.sleep(2.5)
            await capture_screenshot(ws, "01_login.png")

            # 2. Perform Login
            log("\n2. Logging in as admin@empresa.com...")
            await eval_js(ws, """
                document.getElementById('login-email').value = 'admin@empresa.com';
                document.getElementById('login-password').value = 'admin123';
                document.getElementById('login-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
            """)
            await asyncio.sleep(3)

            # Skip first-login password modal if open
            await eval_js(ws, """
                const btnSkip = document.getElementById('btn-skip-password');
                if (btnSkip) btnSkip.click();
            """)
            await asyncio.sleep(1)

            # 3. Main Dashboard (Buscador)
            log("\n3. Capturing 02_buscador_principal.png...")
            await capture_screenshot(ws, "02_buscador_principal.png")

            # 4. Search Results
            log("\n4. Searching for 'wifi'...")
            await eval_js(ws, """
                const input = document.getElementById('input-busqueda');
                input.value = 'wifi';
                document.getElementById('btn-buscar').click();
            """)
            await asyncio.sleep(3)
            log("Capturing 03_busqueda_resultados.png...")
            await capture_screenshot(ws, "03_busqueda_resultados.png")

            # 5. Biblioteca Manuales
            log("\n5. Navigating to Biblioteca (Manuales)...")
            await eval_js(ws, """
                document.querySelector('[data-vista="biblioteca"]').click();
            """)
            await asyncio.sleep(2.5)
            log("Capturing 04_biblioteca_manuales.png...")
            await capture_screenshot(ws, "04_biblioteca_manuales.png")

            # 6. Biblioteca Videos
            log("\n6. Switching to Biblioteca (Videos YouTube)...")
            await eval_js(ws, """
                document.getElementById('btn-subtab-videos').click();
            """)
            await asyncio.sleep(2.5)
            log("Capturing 05_biblioteca_videos.png...")
            await capture_screenshot(ws, "05_biblioteca_videos.png")

            # 7. Pack de Obra Modal
            log("\n7. Opening Pack de Obra modal...")
            await eval_js(ws, """
                document.getElementById('btn-subtab-manuales').click();
                document.getElementById('btn-abrir-modal-pack-obra').click();
            """)
            await asyncio.sleep(2)
            log("Capturing 06_pack_obra_modal.png...")
            await capture_screenshot(ws, "06_pack_obra_modal.png")

            # Close modal
            await eval_js(ws, """
                document.getElementById('btn-cerrar-modal-pack').click();
            """)
            await asyncio.sleep(1)

            # 8. Admin Panel: Usuarios
            log("\n8. Navigating to Usuarios (Admin)...")
            await eval_js(ws, """
                document.querySelector('[data-vista="usuarios"]').click();
            """)
            await asyncio.sleep(2.5)
            log("Capturing 07_gestion_usuarios.png...")
            await capture_screenshot(ws, "07_gestion_usuarios.png")

            # 9. Indexar / Subir Documentación
            log("\n9. Navigating to Indexar Documentación...")
            await eval_js(ws, """
                document.querySelector('[data-vista="subir"]').click();
            """)
            await asyncio.sleep(2)
            log("Capturing 08_indexar_documentacion.png...")
            await capture_screenshot(ws, "08_indexar_documentacion.png")

            log("\n[SUCCESS] All screenshots captured!")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)
        log("Chrome closed and temp dir cleaned up.")

if __name__ == "__main__":
    asyncio.run(run())
