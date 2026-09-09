import requests
import json
import sys

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("COMPROBACION COMPLETA DE FUNCIONAMIENTO (DOCKER STACK)")
print("=" * 70)

# 1. UI HTML
r_home = requests.get(f"{BASE_URL}/")
assert r_home.status_code == 200, f"Error en home: {r_home.status_code}"
assert "<!DOCTYPE html>" in r_home.text or "<html" in r_home.text
print("[OK] 1. Servidor Web & UI HTML (GET /): OK (Status 200)")

# 2. Static Assets
r_js = requests.get(f"{BASE_URL}/static/app.js")
assert r_js.status_code == 200, f"Error en app.js: {r_js.status_code}"
print(f"[OK] 2. Recursos Estaticos (GET /static/app.js): OK ({len(r_js.text):,} bytes)")

# 3. Autenticación (POST /api/token)
r_login = requests.post(
    f"{BASE_URL}/api/token",
    data={"username": "admin@empresa.com", "password": "admin123"}
)
assert r_login.status_code == 200, f"Error en login: {r_login.status_code}, {r_login.text}"
token_data = r_login.json()
token = token_data["access_token"]
role = token_data.get("role")
print(f"[OK] 3. Autenticacion JWT (POST /api/token): OK (Role: {role}, Token emitido)")

headers = {"Authorization": f"Bearer {token}"}

# 4. Usuario Actual (GET /api/me)
r_me = requests.get(f"{BASE_URL}/api/me", headers=headers)
assert r_me.status_code == 200
me_data = r_me.json()
print(f"[OK] 4. Sesion de Usuario (GET /api/me): OK (Email: {me_data.get('email')}, Role: {me_data.get('role')})")

# 5. Filtros Dinámicos (GET /api/filtros)
r_filtros = requests.get(f"{BASE_URL}/api/filtros", headers=headers)
assert r_filtros.status_code == 200
filtros = r_filtros.json()
print(f"[OK] 5. Catalogo de Filtros (GET /api/filtros): OK ({len(filtros.get('dispositivos', []))} dispositivos, {len(filtros.get('categorias', []))} categorias, {len(filtros.get('etiquetas', []))} etiquetas)")

# 6. Sugerencias (GET /api/sugerencias)
r_sug = requests.get(f"{BASE_URL}/api/sugerencias", headers=headers)
assert r_sug.status_code == 200
sugerencias = r_sug.json()
print(f"[OK] 6. Sugerencias Autocompletado (GET /api/sugerencias): OK ({len(sugerencias)} terminos indexados)")

# 7. Motor de Búsqueda Full-Text (GET /api/buscar?q=wifi)
r_search = requests.get(f"{BASE_URL}/api/buscar", params={"q": "wifi"}, headers=headers)
assert r_search.status_code == 200
res_search = r_search.json()
print(f"[OK] 7. Motor de Busqueda (GET /api/buscar?q=wifi): OK ({len(res_search.get('resultados', []))} resultados encontrados en {res_search.get('tiempo_ms', 0)} ms)")
for r in res_search.get('resultados', [])[:2]:
    print(f"    - [{r.get('tipo').upper()}] {r.get('nombre')} (Pag/Pos: {r.get('pagina_encontrada')})")

# 8. Biblioteca de Manuales (GET /api/manuales)
r_man = requests.get(f"{BASE_URL}/api/manuales", headers=headers)
assert r_man.status_code == 200
manuales = r_man.json()
print(f"[OK] 8. Biblioteca PDF (GET /api/manuales): OK ({len(manuales.get('manuales', []))} manuales en BD)")

# 9. Biblioteca de Videos (GET /api/videos)
r_vid = requests.get(f"{BASE_URL}/api/videos", headers=headers)
assert r_vid.status_code == 200
videos = r_vid.json()
print(f"[OK] 9. Biblioteca Videos YouTube (GET /api/videos): OK ({len(videos.get('videos', []))} videos sincronizados)")

# 10. Módulo SAT - Crear Ticket de Prueba (POST /api/sat/tickets)
r_create_ticket = requests.post(
    f"{BASE_URL}/api/sat/tickets",
    headers=headers,
    json={
        "instalador": "Instalaciones Lopez SL",
        "telefono": "+34600123456",
        "obra": "Residencial Mirasierra",
        "distribuidor": "IoT Fenster",
        "dispositivo": "Connect-1",
        "motor": "Somfy Ilmo 50 WT",
        "sintoma": "El motor gira en sentido invertido",
        "diagnostico": "Cables marrón y negro de fase intercambiados en bornera",
        "solucion": "Invertir fase subida y bajada o alternar switch de fase",
        "estado": "resuelto",
        "prioridad": "alta"
    }
)
assert r_create_ticket.status_code == 201, f"Error creando ticket: {r_create_ticket.status_code}"
nuevo_ticket = r_create_ticket.json()
ticket_id = nuevo_ticket["id"]
numero_ticket = nuevo_ticket["numero_ticket"]
print(f"[OK] 10. Crear Ticket SAT (POST /api/sat/tickets): OK (Ticket #{numero_ticket}, ID: {ticket_id})")

# 11. Módulo SAT - Generación de PDF Oficial A4 (GET /api/sat/tickets/{id}/pdf)
r_pdf = requests.get(f"{BASE_URL}/api/sat/tickets/{ticket_id}/pdf", headers=headers)
assert r_pdf.status_code == 200
assert r_pdf.headers.get("content-type") == "application/pdf"
assert len(r_pdf.content) > 1000
print(f"[OK] 11. Generacion de Parte PDF A4 (GET /api/sat/tickets/{ticket_id}/pdf): OK ({len(r_pdf.content):,} bytes PDF)")

# 12. Módulo SAT - Estadísticas (GET /api/sat/tickets/stats)
r_stats = requests.get(f"{BASE_URL}/api/sat/tickets/stats", headers=headers)
assert r_stats.status_code == 200
stats = r_stats.json()
print(f"[OK] 12. Estadisticas SAT (GET /api/sat/tickets/stats): OK (Total: {stats.get('total')}, Resueltos: {stats.get('resueltos')})")

# 13. Limpieza de Ticket de Prueba (DELETE /api/sat/tickets/{id})
r_del = requests.delete(f"{BASE_URL}/api/sat/tickets/{ticket_id}", headers=headers)
assert r_del.status_code == 200
print(f"[OK] 13. Eliminar Ticket de Prueba (DELETE /api/sat/tickets/{ticket_id}): OK")

# 14. Gestión de Usuarios (GET /api/usuarios)
r_users = requests.get(f"{BASE_URL}/api/usuarios", headers=headers)
assert r_users.status_code == 200
users = r_users.json()
print(f"[OK] 14. Gestion de Usuarios (GET /api/usuarios): OK ({len(users)} usuarios en el sistema)")

print("=" * 70)
print("TODAS LAS COMPROBACIONES (14/14) HAN SIDO COMPLETADAS CON EXITO (100%)")
print("=" * 70)
