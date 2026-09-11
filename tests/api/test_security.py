"""
Suite de tests de seguridad (RBAC, SSRF, subida de archivos, cabeceras).

Porta a pytest los escenarios de valor de los antiguos scripts manuales
tools/manual_checks/test_security_audit.py y test_docker_stack.py, usando
TestClient en vez de peticiones contra un servidor real en localhost:8000.

Nota 1: los payloads de "archivo malicioso" usan contenido inerte (no un
webshell/exploit real) porque el endpoint solo valida la extensión del
archivo, no su contenido, y un payload realista dispara falsos positivos
de antivirus al escribir el archivo de test en disco.

Nota 2: todos los tests de este módulo usan la fixture `mock_users` (que
sustituye `database.SessionLocal`) igual que el resto de la suite, siguiendo
la misma convención que ya usan tests/api/test_rbac.py y test_tickets_sat.py:
el contenedor de PostgreSQL de docker-compose expone su puerto solo a la red
interna, no al host (ver docker-compose.yml), así que ningún test de pytest
ejecutado desde el host puede depender de una conexión real a Postgres; solo
se automatizan aquí los escenarios en los que el RBAC/validación corta la
petición antes de tocar la base de datos. Los escenarios que sí necesitan
ejecutar una consulta SQL real con payloads maliciosos (inyección SQL contra
/api/buscar y /api/sat/tickets) siguen viviendo solo en
tools/manual_checks/test_security_audit.py, que se ejecuta contra un servidor
real con Postgres accesible.
"""

import pytest


@pytest.mark.parametrize("ruta", [
    "/api/me",
    "/api/usuarios",
    "/api/sat/tickets",
    "/api/sat/tickets/stats",
    "/api/manuales",
    "/api/videos",
    "/api/filtros",
    "/api/buscar?q=test",
    "/api/dispositivos",
])
def test_rutas_protegidas_requieren_autenticacion(client, ruta):
    """Sin token, cualquier ruta protegida debe responder 401, nunca datos."""
    response = client.get(ruta)
    assert response.status_code == 401


def test_jwt_con_firma_manipulada_es_rechazado(client):
    headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"}
    response = client.get("/api/me", headers=headers)
    assert response.status_code == 401


def test_tecnico_bloqueado_en_reindexar(client, mock_users):
    response = client.post("/api/reindexar", headers=mock_users["headers"]["tecnico"])
    assert response.status_code == 403


def test_comercial_bloqueado_en_sincronizar_videos(client, mock_users):
    response = client.post(
        "/api/videos/sincronizar",
        json={"canal_url": "https://www.youtube.com/@MySmartWindow/videos"},
        headers=mock_users["headers"]["comercial"],
    )
    assert response.status_code == 403


@pytest.mark.parametrize("canal_url", [
    "http://169.254.169.254/latest/meta-data/",
    "http://localhost:5432",
    "http://malicious-external-domain.com/evil",
    "file:///etc/passwd",
])
def test_sincronizar_videos_bloquea_urls_fuera_de_whitelist_ssrf(client, mock_users, canal_url):
    """_validar_url_youtube debe rechazar cualquier URL que no sea youtube.com antes de hacer red."""
    response = client.post(
        "/api/videos/sincronizar",
        json={"canal_url": canal_url},
        headers=mock_users["headers"]["admin"],
    )
    assert response.status_code == 400
    assert "youtube.com" in response.text.lower()


@pytest.mark.parametrize("nombre,contenido,mimetype", [
    ("archivo_no_pdf.txt", b"contenido de prueba inerte, no ejecutable", "text/plain"),
    ("disfrazado.pdf.bin", b"contenido binario de prueba inerte", "application/octet-stream"),
])
def test_subir_rechaza_archivos_no_pdf(client, mock_users, test_manuals_dir, nombre, contenido, mimetype):
    files = {"archivos": (nombre, contenido, mimetype)}
    response = client.post("/api/subir", files=files, headers=mock_users["headers"]["admin"])
    assert response.status_code == 200
    resultado = response.json()["resultados"][0]
    assert resultado["ok"] is False


@pytest.mark.parametrize("ruta", [
    "/.env",
    "/.env.example",
    "/.git/config",
    "/.git/HEAD",
    "/Dockerfile",
    "/docker-compose.yml",
    "/app/main.py",
    "/app/database.py",
])
def test_archivos_de_configuracion_no_se_sirven_como_estaticos(client, ruta):
    response = client.get(ruta)
    assert response.status_code in (404, 403, 405)
    assert "POSTGRES_PASSWORD" not in response.text
    assert "[core]" not in response.text


def test_cabeceras_de_seguridad_en_raiz(client):
    response = client.get("/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert "X-Frame-Options" in response.headers
