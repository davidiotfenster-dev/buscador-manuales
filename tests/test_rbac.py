"""
Suite de tests de seguridad RBAC y prevención de vulnerabilidades
para el Buscador de Manuales IoT Fenster.
"""

import pytest


def test_comercial_no_accede_a_tecnico(client, test_manuals_dir, mock_users):
    """
    CRÍTICO RBAC: Un usuario con rol 'comercial' NO debe poder acceder
    a un manual clasificado como 'tecnico' (debe devolver HTTP 403).
    """
    headers = mock_users["headers"]["comercial"]
    response = client.get(
        f"/manuales/{test_manuals_dir['tecnico']}",
        headers=headers
    )
    assert response.status_code == 403
    assert "No tienes acceso a este documento" in response.text or "Acceso Restringido" in response.text


def test_comercial_accede_a_publico(client, test_manuals_dir, mock_users):
    """
    Verifica que un comercial sí puede acceder a un manual con nivel_acceso 'publico'.
    """
    headers = mock_users["headers"]["comercial"]
    response = client.get(
        f"/manuales/{test_manuals_dir['publico']}",
        headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_tecnico_accede_a_tecnico(client, test_manuals_dir, mock_users):
    """
    Verifica que un usuario con rol 'tecnico' sí puede acceder a un manual técnico.
    """
    headers = mock_users["headers"]["tecnico"]
    response = client.get(
        f"/manuales/{test_manuals_dir['tecnico']}",
        headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_admin_accede_a_tecnico(client, test_manuals_dir, mock_users):
    """
    Verifica que un usuario con rol 'admin' tiene acceso total a manuales técnicos.
    """
    headers = mock_users["headers"]["admin"]
    response = client.get(
        f"/manuales/{test_manuals_dir['tecnico']}",
        headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


@pytest.mark.parametrize("payload_malicioso", [
    "../../app/main.py",
    "..%2F..%2Fapp%2Fmain.py",
    "..\\..\\app\\main.py",
    "..%5C..%5Capp%5Cmain.py",
    "....//....//app/main.py",
    "/etc/passwd",
    "C:\\Windows\\win.ini",
    "..%2F..%2Fetc%2Fpasswd"
])
def test_path_traversal_bloqueado(client, test_manuals_dir, mock_users, payload_malicioso):
    """
    CRÍTICO SEGURIDAD: Cualquier intento de Path Traversal debe ser interceptado y bloqueado
    con código 403 o 404, impidiendo leer archivos fuera del directorio seguro de manuales.
    """
    headers = mock_users["headers"]["admin"]
    response = client.get(f"/manuales/{payload_malicioso}", headers=headers)
    # Debe ser denegado o no encontrado, jamás HTTP 200 exponiendo el archivo externo
    assert response.status_code in (403, 404)
    # Asegurar que el contenido devuelto no es código fuente de python ni archivo de sistema
    assert "from fastapi import" not in response.text
    assert "[fonts]" not in response.text


def test_comercial_no_accede_a_miniatura_tecnica(client, test_manuals_dir, mock_users, monkeypatch):
    """
    Verifica que el endpoint de miniaturas de páginas también aplica RBAC
    y deniega el acceso a un comercial para un manual técnico (id=102).
    """
    # Simular disponibilidad de pypdfium2 para que llegue a la comprobación RBAC
    monkeypatch.setattr("app.main._PYPDFIUM_DISPONIBLE", True)

    headers = mock_users["headers"]["comercial"]
    response = client.get("/api/miniatura/102/1", headers=headers)
    assert response.status_code == 403


def test_usuario_no_autenticado_recibe_401(client, test_manuals_dir):
    """
    Verifica que solicitudes a manuales sin token JWT son rechazadas con HTTP 401.
    """
    response = client.get(f"/manuales/{test_manuals_dir['publico']}")
    assert response.status_code == 401


def test_error_html_para_navegador_y_json_para_api(client, test_manuals_dir, mock_users):
    """
    Verifica la negociación de contenido (Content Negotiation):
    - Navegador/iframe (Accept: text/html) recibe la plantilla HTML amigable de IoT Fenster.
    - Llamada API (Accept: application/json) recibe JSON estándar con {'detail': ...}.
    """
    headers_comercial = mock_users["headers"]["comercial"]

    # 1. Petición simulando navegador / iframe
    headers_html = {**headers_comercial, "Accept": "text/html,application/xhtml+xml"}
    resp_html = client.get(f"/manuales/{test_manuals_dir['tecnico']}", headers=headers_html)
    assert resp_html.status_code == 403
    assert "text/html" in resp_html.headers.get("content-type", "")
    assert "IoT Fenster" in resp_html.text
    assert "Acceso Restringido" in resp_html.text
    assert "403" in resp_html.text

    # 2. Petición simulando cliente API
    headers_json = {**headers_comercial, "Accept": "application/json"}
    resp_json = client.get(f"/manuales/{test_manuals_dir['tecnico']}", headers=headers_json)
    assert resp_json.status_code == 403
    assert "application/json" in resp_json.headers.get("content-type", "")
    data = resp_json.json()
    assert "detail" in data
    assert "No tienes acceso" in data["detail"]


def test_archivo_inexistente_retorna_404(client, test_manuals_dir, mock_users):
    """
    Verifica que un archivo inexistente devuelve 404 (HTML para navegador, JSON para API).
    """
    headers_admin = mock_users["headers"]["admin"]

    # API JSON
    headers_json = {**headers_admin, "Accept": "application/json"}
    resp_json = client.get("/manuales/archivo_fantasma_123.pdf", headers=headers_json)
    assert resp_json.status_code == 404
    assert "detail" in resp_json.json()

    # Navegador HTML
    headers_html = {**headers_admin, "Accept": "text/html"}
    resp_html = client.get("/manuales/archivo_fantasma_123.pdf", headers=headers_html)
    assert resp_html.status_code == 404
    assert "text/html" in resp_html.headers.get("content-type", "")
    assert "Documento No Encontrado" in resp_html.text
    assert "404" in resp_html.text


def test_admin_requerido_para_gestion_usuarios(client, mock_users, monkeypatch):
    """
    Verifica que los endpoints administrativos como /api/usuarios deniegan
    el acceso a comerciales y técnicos (HTTP 403) y lo permiten a administradores.
    """
    monkeypatch.setattr("app.database.listar_usuarios", lambda: [])

    # Comercial -> 403
    resp_com = client.get("/api/usuarios", headers=mock_users["headers"]["comercial"])
    assert resp_com.status_code == 403

    # Tecnico -> 403
    resp_tec = client.get("/api/usuarios", headers=mock_users["headers"]["tecnico"])
    assert resp_tec.status_code == 403

    # Admin -> 200
    resp_adm = client.get("/api/usuarios", headers=mock_users["headers"]["admin"])
    assert resp_adm.status_code == 200


def test_archivo_huerfano_en_disco_no_se_sirve_sin_registro_bd(client, test_manuals_dir, mock_users):
    """
    CRÍTICO FAIL-CLOSED: Si un archivo PDF existe físicamente en disco pero no tiene fila en BD,
    el sistema NO debe servirlo (debe devolver 404 en vez de eludir la comprobación RBAC).
    """
    # Crear archivo huérfano en disco que no existe en el mock de la BD
    huerfano = test_manuals_dir["dir"] / "manual_huerfano.pdf"
    huerfano.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

    # Usuario comercial intenta acceder
    resp = client.get("/manuales/manual_huerfano.pdf", headers=mock_users["headers"]["comercial"])
    assert resp.status_code == 404


def test_ip_cliente_con_proxy_inverso():
    """
    Verifica que _obtener_ip_cliente extrae la IP real de X-Forwarded-For cuando hay proxy inverso.
    """
    from starlette.requests import Request
    from app.main import _obtener_ip_cliente

    # Petición detrás de proxy (Nginx / Cloudflare / Traefik)
    scope_proxy = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.195, 70.41.3.18")],
        "client": ("10.0.0.1", 12345)
    }
    req_proxy = Request(scope_proxy)
    assert _obtener_ip_cliente(req_proxy) == "203.0.113.195"

    # Petición directa sin proxy
    scope_directo = {
        "type": "http",
        "headers": [],
        "client": ("192.168.1.50", 12345)
    }
    req_directo = Request(scope_directo)
    assert _obtener_ip_cliente(req_directo) == "192.168.1.50"


def test_miniatura_cache_creacion_y_reutilizacion(client, test_manuals_dir, mock_users, monkeypatch):
    """
    Verifica que la primera petición genera la miniatura y la guarda en disco,
    y que la segunda petición la sirve directamente desde la caché sin re-renderizar.
    """
    from PIL import Image
    llamadas_render = []

    def mock_render(ruta_pdf, numero_pagina, escala=0.6):
        llamadas_render.append((ruta_pdf, numero_pagina))
        return Image.new("RGB", (50, 50), color="blue")

    monkeypatch.setattr("app.main._PYPDFIUM_DISPONIBLE", True)
    monkeypatch.setattr("app.main._renderizar_pagina_como_imagen", mock_render)

    headers = mock_users["headers"]["comercial"]  # 101 es público
    cache_path = test_manuals_dir["cache_dir"] / "101_1.png"
    assert not cache_path.exists()

    # Primera petición: se renderiza y se guarda en caché
    resp1 = client.get("/api/miniatura/101/1", headers=headers)
    assert resp1.status_code == 200
    assert resp1.headers["content-type"] == "image/png"
    assert len(llamadas_render) == 1
    assert cache_path.exists()

    # Segunda petición: se sirve desde la caché de disco (no se vuelve a renderizar)
    resp2 = client.get("/api/miniatura/101/1", headers=headers)
    assert resp2.status_code == 200
    assert resp2.headers["content-type"] == "image/png"
    assert len(llamadas_render) == 1  # No se incrementó


def test_miniatura_rbac_bloquea_incluso_si_esta_en_cache(client, test_manuals_dir, mock_users, monkeypatch):
    """
    CRÍTICO SEGURIDAD: Aunque una miniatura técnica (id=102) ya esté generada en disco
    (por ejemplo, por una visita previa de un admin), un usuario comercial DEBE recibir 403.
    """
    monkeypatch.setattr("app.main._PYPDFIUM_DISPONIBLE", True)

    # Crear manualmente la miniatura en caché simulando una carga previa de admin
    cache_path = test_manuals_dir["cache_dir"] / "102_1.png"
    cache_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")

    # El comercial intenta acceder a la miniatura técnica
    headers = mock_users["headers"]["comercial"]
    resp = client.get("/api/miniatura/102/1", headers=headers)
    assert resp.status_code == 403
    assert "No tienes acceso a este documento" in resp.text


def test_invalidar_cache_miniaturas(test_manuals_dir):
    """
    Verifica que la función _invalidar_cache_miniaturas borra selectivamente
    o totalmente los archivos de miniaturas.
    """
    from app.main import _invalidar_cache_miniaturas

    cache_dir = test_manuals_dir["cache_dir"]
    # Crear archivos de prueba
    (cache_dir / "101_1.png").write_text("dummy")
    (cache_dir / "101_2.png").write_text("dummy")
    (cache_dir / "102_1.png").write_text("dummy")

    # Invalidar solo manual 101
    _invalidar_cache_miniaturas(101)
    assert not (cache_dir / "101_1.png").exists()
    assert not (cache_dir / "101_2.png").exists()
    assert (cache_dir / "102_1.png").exists()

    # Invalidar toda la caché
    _invalidar_cache_miniaturas(None)
    assert not (cache_dir / "102_1.png").exists()


def test_expansion_sinonimos_tecnicos():
    """
    Verifica que el gestor de sinónimos técnicos expande correctamente
    consultas coloquiales de técnicos a términos formales de los manuales.
    """
    from app.sinonimos import expandir_query

    # 1. Avería típica: 'no enciende' debe buscar también 'sin alimentacion'
    exp1 = expandir_query("no enciende")
    assert "no enciende" in exp1
    assert "sin alimentacion" in exp1 or "sin corriente" in exp1

    # 2. Equivalencia de marcas: 'wave 1' debe expandir a marcas partner ('connect-1' / 'icon1')
    exp2 = expandir_query("wave 1")
    assert "wave 1" in exp2
    assert "connect-1" in exp2 or "icon1" in exp2 or "icon.1" in exp2

    # 3. Red y conectividad: 'cgnat' debe expandir a 'carrier grade nat' o 'doble nat'
    exp3 = expandir_query("cgnat")
    assert "cgnat" in exp3
    assert "carrier grade nat" in exp3 or "doble nat" in exp3 or "ip compartida" in exp3

    # 4. Término sin sinónimos: permanece inalterado
    assert expandir_query("termino_inexistente_xyz123") == "termino_inexistente_xyz123"
