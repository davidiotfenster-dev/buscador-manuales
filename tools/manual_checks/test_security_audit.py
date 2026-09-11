import sys
import requests
import json
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_URL = "http://localhost:8000"

def log_test(category, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    symbol = "[OK]" if passed else "[WARN]"
    print(f"[{status}] {symbol} {category} -> {name}")
    if detail:
        print(f"       Detalle: {detail}")

def run_security_audit():
    print("=" * 75)
    print("AUDITORÍA DE SEGURIDAD INTEGRAL Y TESTS DE PENETRACIÓN (AST / DAST)")
    print("Target:", BASE_URL)
    print("=" * 75)

    results = []

    # -------------------------------------------------------------
    # 1. AUTENTICACIÓN Y CONTROL DE ACCESO (RBAC)
    # -------------------------------------------------------------
    print("\n--- 1. AUTENTICACIÓN Y CONTROL DE ACCESO (RBAC) ---")

    # 1.1 Intentar acceder a rutas protegidas sin token
    protected_get_routes = [
        ("/api/me", 401),
        ("/api/usuarios", 401),
        ("/api/sat/tickets", 401),
        ("/api/sat/tickets/stats", 401),
        ("/api/manuales", 401),
        ("/api/videos", 401),
        ("/api/filtros", 401),
        ("/api/buscar?q=test", 401),
        ("/api/dispositivos", 401),
        ("/manuales/test.pdf", 401),
    ]

    for route, expected_code in protected_get_routes:
        r = requests.get(f"{BASE_URL}{route}")
        ok = r.status_code in (401, 403)
        log_test("Auth/Unauthenticated", f"GET {route}", ok, f"HTTP {r.status_code} (Esperado 401/403)")
        results.append(ok)

    # 1.2 Token JWT inválido / manipulado
    headers_forged = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"}
    r = requests.get(f"{BASE_URL}/api/me", headers=headers_forged)
    ok = r.status_code == 401
    log_test("Auth/JWT", "Firma JWT manipulada / inválida rechazada", ok, f"HTTP {r.status_code}")
    results.append(ok)

    # 1.3 Obtener token válido de admin
    r_login = requests.post(
        f"{BASE_URL}/api/token",
        data={"username": "admin@empresa.com", "password": "admin123"}
    )
    admin_token = None
    if r_login.status_code == 200:
        admin_token = r_login.json().get("access_token")
        log_test("Auth/Login", "Login admin exitoso con credencial admin@empresa.com", True)
    else:
        log_test("Auth/Login", "Login admin con admin123", False, f"HTTP {r_login.status_code}")

    admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

    # 1.4 Crear usuario de prueba con rol 'tecnico' y 'comercial' para probar escalada de privilegios
    tecnico_token = None
    comercial_token = None
    if admin_token:
        # Crear tecnico de prueba
        requests.post(
            f"{BASE_URL}/api/usuarios",
            json={"email": "audit_tecnico@test.com", "password": "PasswordTest123!", "role": "tecnico"},
            headers=admin_headers
        )
        r_log_tec = requests.post(f"{BASE_URL}/api/token", data={"username": "audit_tecnico@test.com", "password": "PasswordTest123!"})
        if r_log_tec.status_code == 200:
            tecnico_token = r_log_tec.json().get("access_token")

        # Crear comercial de prueba
        requests.post(
            f"{BASE_URL}/api/usuarios",
            json={"email": "audit_comercial@test.com", "password": "PasswordTest123!", "role": "comercial"},
            headers=admin_headers
        )
        r_log_com = requests.post(f"{BASE_URL}/api/token", data={"username": "audit_comercial@test.com", "password": "PasswordTest123!"})
        if r_log_com.status_code == 200:
            comercial_token = r_log_com.json().get("access_token")

    # 1.5 Escalada de privilegios: ¿Puede un técnico acceder a la gestión de usuarios (/api/usuarios)?
    if tecnico_token:
        r_esc = requests.get(f"{BASE_URL}/api/usuarios", headers={"Authorization": f"Bearer {tecnico_token}"})
        ok = r_esc.status_code == 403
        log_test("RBAC/Escalada", "Técnico bloqueado en gestión de usuarios (403)", ok, f"HTTP {r_esc.status_code}")
        results.append(ok)

        # ¿Puede un técnico subir o reindexar manuales?
        r_sub = requests.post(f"{BASE_URL}/api/reindexar", headers={"Authorization": f"Bearer {tecnico_token}"})
        ok = r_sub.status_code == 403
        log_test("RBAC/Escalada", "Técnico bloqueado en reindexar manuales (403)", ok, f"HTTP {r_sub.status_code}")
        results.append(ok)

    # 1.6 Escalada de privilegios: ¿Puede un comercial acceder a tickets SAT o asistencia técnica?
    if comercial_token:
        r_com_sat = requests.get(f"{BASE_URL}/api/sat/tickets", headers={"Authorization": f"Bearer {comercial_token}"})
        ok = r_com_sat.status_code == 403
        log_test("RBAC/Escalada", "Comercial bloqueado en tickets SAT (403)", ok, f"HTTP {r_com_sat.status_code}")
        results.append(ok)

    # -------------------------------------------------------------
    # 2. PATH TRAVERSAL / ARBITRARY FILE READ (LFI)
    # -------------------------------------------------------------
    print("\n--- 2. PATH TRAVERSAL / LFI (LOCAL FILE INCLUSION) ---")

    traversal_payloads = [
        "../../../../etc/passwd",
        "..%2f..%2f..%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc%252fpasswd",
        "....//....//....//etc/passwd",
        "../app/main.py",
        "..%5c..%5capp%5cmain.py",
        "%2e%2e%2f%2e%2e%2fapp/main.py",
        "manuales/../../.env",
    ]

    for payload in traversal_payloads:
        url = f"{BASE_URL}/manuales/{payload}"
        r = requests.get(url, headers=admin_headers)
        # Debe dar 403 Forbidden o 404 Not Found, NUNCA 200 con contenido sensible
        is_safe = r.status_code in (400, 403, 404) and "root:x:" not in r.text and "FastAPI" not in r.text
        log_test("PathTraversal", f"GET /manuales/{payload[:25]}...", is_safe, f"HTTP {r.status_code}")
        results.append(is_safe)

    # Path traversal en endpoint de pack de obra
    r_pack = requests.get(f"{BASE_URL}/api/dispositivos/..%2F..%2Fetc/pack", headers=admin_headers)
    is_safe = r_pack.status_code in (400, 403, 404)
    log_test("PathTraversal", "GET /api/dispositivos/../../pack", is_safe, f"HTTP {r_pack.status_code}")
    results.append(is_safe)

    # -------------------------------------------------------------
    # 3. INYECCIÓN SQL (SQLi) EN MOTOR FTS Y PGVECTOR
    # -------------------------------------------------------------
    print("\n--- 3. INYECCIÓN SQL (SQLi) ---")

    sqli_payloads = [
        "' OR 1=1 --",
        "'; DROP TABLE manuales; --",
        "1' UNION SELECT null, null, null, null, null, null, null, null, null, null, null, null --",
        "' AND 1=cast((SELECT version()) as int) --",
        "' OR '1'='1",
        "test' AND pg_sleep(2) --"
    ]

    for payload in sqli_payloads:
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/buscar", params={"q": payload}, headers=admin_headers)
        elapsed = time.time() - t0

        # Si hay inyección con pg_sleep, elapsed sería > 2 segundos
        # Si la consulta falla por sintaxis SQL rota, FastAPI devolvería 500 con error de PostgreSQL
        no_500 = r.status_code != 500
        no_sleep = elapsed < 1.5
        ok = no_500 and no_sleep and r.status_code == 200
        log_test("SQLi", f"Búsqueda con: {payload[:25]}", ok, f"HTTP {r.status_code} ({elapsed:.2f}s)")
        results.append(ok)

    # Inyección SQL en filtros de tickets SAT
    for payload in sqli_payloads[:3]:
        r = requests.get(f"{BASE_URL}/api/sat/tickets", params={"q": payload, "estado": payload}, headers=admin_headers)
        ok = r.status_code == 200
        log_test("SQLi", f"Tickets SAT filtro: {payload[:20]}", ok, f"HTTP {r.status_code}")
        results.append(ok)

    # -------------------------------------------------------------
    # 4. SERVER-SIDE REQUEST FORGERY (SSRF) EN SINCRONIZACIÓN YOUTUBE
    # -------------------------------------------------------------
    print("\n--- 4. SSRF (SERVER-SIDE REQUEST FORGERY) ---")

    ssrf_payloads = [
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:5432",
        "http://127.0.0.1:8000/api/usuarios",
        "http://malicious-external-domain.com/evil",
        "file:///etc/passwd"
    ]

    for ssrf_url in ssrf_payloads:
        r = requests.post(
            f"{BASE_URL}/api/videos/sincronizar",
            json={"canal_url": ssrf_url},
            headers=admin_headers
        )
        # El validador _validar_url_youtube debe bloquearlo con HTTP 400 antes de hacer cualquier request
        blocked = r.status_code == 400 and "Solo se aceptan URLs de youtube.com" in r.text
        log_test("SSRF", f"Canal URL: {ssrf_url[:30]}", blocked, f"HTTP {r.status_code} - Bloqueado por whitelist")
        results.append(blocked)

    # -------------------------------------------------------------
    # 5. VALIDACIÓN DE SUBIDA DE ARCHIVOS (ARBITRARY FILE UPLOAD)
    # -------------------------------------------------------------
    print("\n--- 5. VALIDACIÓN DE ARCHIVOS SUBIDOS ---")

    # 5.1 Intentar subir script ejecutable (.py, .php, .exe, .sh)
    malicious_files = [
        ("malicious.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
        ("exploit.py", b"import os; os.system('whoami')", "text/x-python"),
        ("script.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh"),
        ("fake.pdf.exe", b"MZ\x90\x00\x03", "application/x-msdownload")
    ]

    for fname, content, mtype in malicious_files:
        files = {"archivos": (fname, content, mtype)}
        r = requests.post(f"{BASE_URL}/api/subir", files=files, headers=admin_headers)
        # Debe rechazarlo porque no termina en .pdf
        rejected = r.status_code == 200 and r.json().get("resultados", [{}])[0].get("ok") is False
        log_test("Upload/MIME", f"Rechazo de archivo no-PDF: {fname}", rejected)
        results.append(rejected)

    # 5.2 Intentar subir archivo con Path Traversal en el nombre
    files = {"archivos": ("../../test_escape.pdf", b"%PDF-1.4 header dummy", "application/pdf")}
    r = requests.post(f"{BASE_URL}/api/subir", files=files, headers=admin_headers)
    # El archivo debe guardarse sanitizado dentro de manuales/ sin escapar
    if r.status_code == 200:
        res = r.json().get("resultados", [{}])[0]
        # Verificar que la operación se procesó y que no existe ningún archivo fuera de manuales/
        import os
        escaped_file_exists = os.path.exists("test_escape.pdf") or os.path.exists("../test_escape.pdf")
        safe = not escaped_file_exists
        log_test("Upload/Traversal", "Nombre con Path Traversal contenido dentro de manuales/", safe)
        results.append(safe)

    # -------------------------------------------------------------
    # 6. EXPOSICIÓN DE ARCHIVOS SENSIBLES Y CONFIGURACIONES
    # -------------------------------------------------------------
    print("\n--- 6. EXPOSICIÓN DE ARCHIVOS SENSIBLES Y METADATOS ---")

    sensitive_paths = [
        "/.env",
        "/.env.example",
        "/.git/config",
        "/.git/HEAD",
        "/.admin_initial_password",
        "/Dockerfile",
        "/docker-compose.yml",
        "/app/main.py",
        "/app/database.py"
    ]

    for spath in sensitive_paths:
        r = requests.get(f"{BASE_URL}{spath}")
        # FastAPI no debe servir estos archivos como estáticos (debe dar 404 o redirigir)
        is_blocked = r.status_code in (404, 403, 405) and "POSTGRES_PASSWORD" not in r.text and "[core]" not in r.text
        log_test("InfoLeak/SensitiveFiles", f"Acceso a {spath}", is_blocked, f"HTTP {r.status_code}")
        results.append(is_blocked)

    # -------------------------------------------------------------
    # 7. CABECERAS DE SEGURIDAD Y PROTECCIÓN CLICKJACKING
    # -------------------------------------------------------------
    print("\n--- 7. CABECERAS DE SEGURIDAD Y CLICKJACKING ---")

    r_home = requests.get(f"{BASE_URL}/")
    headers = r_home.headers
    
    # Comprobar cabeceras recomendadas
    has_xframe = "X-Frame-Options" in headers
    has_nosniff = headers.get("X-Content-Type-Options") == "nosniff"
    server_header = headers.get("server", "")

    log_test("SecurityHeaders", "X-Content-Type-Options: nosniff en raíz", has_nosniff, f"Valor: {headers.get('X-Content-Type-Options')}")
    log_test("SecurityHeaders", "X-Frame-Options en raíz", has_xframe, f"Valor: {headers.get('X-Frame-Options')}")
    log_test("SecurityHeaders", "Ocultamiento de versión de servidor", "uvicorn" not in server_header.lower(), f"Server: {server_header}")

    # En /manuales/ si tiene X-Frame-Options: SAMEORIGIN
    r_man = requests.get(f"{BASE_URL}/manuales/test.pdf", headers=admin_headers)
    has_man_frame = r_man.headers.get("X-Frame-Options") == "SAMEORIGIN" or r_man.headers.get("x-frame-options") == "SAMEORIGIN"
    log_test("SecurityHeaders", "X-Frame-Options: SAMEORIGIN en visor PDF", has_man_frame or r_man.status_code == 404)

    # -------------------------------------------------------------
    # RESUMEN FINAL DE AUDITORÍA
    # -------------------------------------------------------------
    print("\n" + "=" * 75)
    total_tests = len(results)
    passed_tests = sum(1 for x in results if x)
    pct = (passed_tests / total_tests) * 100 if total_tests else 0
    print(f"RESUMEN AUDITORÍA DE SEGURIDAD: {passed_tests}/{total_tests} superados ({pct:.1f}%)")
    print("=" * 75)

if __name__ == "__main__":
    run_security_audit()
