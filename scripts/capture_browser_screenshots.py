import os
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("docs/screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Iniciando captura con Playwright y Chrome...")

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=["--no-sandbox", "--disable-gpu", "--window-size=1440,920"]
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 920},
        device_scale_factor=1.25
    )
    page = context.new_page()

    print("1. Cargando pagina inicial...")
    page.goto("http://localhost:8000", wait_until="domcontentloaded", timeout=15000)
    time.sleep(1)

    print("2. Iniciando sesión con admin@empresa.com ...")
    page.fill("#login-email", "admin@empresa.com")
    page.fill("#login-password", "admin1234")
    page.click("button[type='submit']")
    
    # Esperar a que el modal de login se oculte y aparezca la pestaña esquemas
    page.wait_for_selector("#login-modal", state="hidden", timeout=10000)
    page.wait_for_selector("#tab-esquemas:not(.hidden)", state="visible", timeout=10000)
    print("   Sesión autenticada correctamente.")

    # Asegurar tema oscuro
    page.evaluate("() => { if (typeof aplicarTema === 'function') aplicarTema('dark'); }")
    time.sleep(0.5)

    print("3. Navegando a pestaña 'Esquemas & SAT'...")
    page.click("#tab-esquemas")
    page.wait_for_selector("#vista-esquemas.vista-activa", state="visible", timeout=5000)
    time.sleep(1)

    # ----------------------------------------------------
    # SCREENSHOT 16: Simulador Eléctrico 230V Interactivo
    # ----------------------------------------------------
    print("4. Generando 16_esquemas_electricos_230v.png ...")
    page.click("#subtab-btn-simulador")
    time.sleep(0.5)
    page.click("#btn-sim-subir")
    time.sleep(1)

    path_16 = os.path.join(OUTPUT_DIR, "16_esquemas_electricos_230v.png")
    page.screenshot(path=path_16)
    print(f"   [OK] Guardado: 16_esquemas_electricos_230v.png ({os.path.getsize(path_16)} bytes)")

    # ----------------------------------------------------
    # SCREENSHOT 17: Esquema en Modo Pantalla Completa / Ampliado
    # ----------------------------------------------------
    print("5. Generando 17_esquema_fullscreen.png ...")
    page.click("#btn-sim-fullscreen")
    time.sleep(1)

    path_17 = os.path.join(OUTPUT_DIR, "17_esquema_fullscreen.png")
    page.screenshot(path=path_17)
    print(f"   [OK] Guardado: 17_esquema_fullscreen.png ({os.path.getsize(path_17)} bytes)")

    # Cerrar pantalla completa
    page.click("#btn-sim-fullscreen")
    time.sleep(0.5)

    # ----------------------------------------------------
    # SCREENSHOT 18: Asistente Guiado de Triage SAT (Wizard)
    # ----------------------------------------------------
    print("6. Generando 18_triage_sat_wizard.png ...")
    page.click("#subtab-btn-triage")
    time.sleep(1)

    # Clic en rama motor y luego en triage-1 (giro invertido)
    page.click("button.btn-wizard-opcion[data-target='rama_motor']")
    time.sleep(0.8)
    page.click("button.btn-wizard-opcion[data-target='triage-1']")
    time.sleep(1)

    # Scroll hacia abajo para capturar el cuadro de resolución completo con botones WhatsApp y Ticket
    page.evaluate("() => { window.scrollBy(0, 240); }")
    time.sleep(0.5)

    path_18 = os.path.join(OUTPUT_DIR, "18_triage_sat_wizard.png")
    page.screenshot(path=path_18)
    print(f"   [OK] Guardado: 18_triage_sat_wizard.png ({os.path.getsize(path_18)} bytes)")

    # ----------------------------------------------------
    # SCREENSHOT 19: Mini-CRM de Tickets SAT
    # ----------------------------------------------------
    print("7. Generando 19_mini_crm_tickets_sat.png ...")
    page.click("#subtab-btn-tickets")
    time.sleep(2)  # Dar tiempo a que el fetch cargue los tickets de PostgreSQL

    path_19 = os.path.join(OUTPUT_DIR, "19_mini_crm_tickets_sat.png")
    page.screenshot(path=path_19)
    print(f"   [OK] Guardado: 19_mini_crm_tickets_sat.png ({os.path.getsize(path_19)} bytes)")

    browser.close()
    print("¡Todas las capturas 16, 17, 18 y 19 se han generado con éxito!")
