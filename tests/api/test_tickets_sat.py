"""
Tests de API y control de acceso (RBAC) para el Mini-CRM de Tickets SAT.
"""

from datetime import datetime
import pytest
from app import database


@pytest.fixture(autouse=True)
def mock_tickets_db(monkeypatch):
    tickets_store = []
    secuencia = [1]

    def mock_crear_ticket(db, ticket_data, creado_por=""):
        t_id = secuencia[0]
        secuencia[0] += 1
        ticket = database.TicketSAT(
            id=t_id,
            numero_ticket=f"SAT-2026-{t_id:04d}",
            instalador=ticket_data.get("instalador", ""),
            telefono=ticket_data.get("telefono", ""),
            obra=ticket_data.get("obra", ""),
            distribuidor=ticket_data.get("distribuidor", ""),
            dispositivo=ticket_data.get("dispositivo", ""),
            motor=ticket_data.get("motor", ""),
            sintoma=ticket_data.get("sintoma", ""),
            diagnostico=ticket_data.get("diagnostico", ""),
            solucion=ticket_data.get("solucion", ""),
            estado=ticket_data.get("estado", "en_espera"),
            prioridad=ticket_data.get("prioridad", "normal"),
            creado_por=creado_por,
            notas=ticket_data.get("notas", ""),
            fecha_creacion=datetime.now(),
            fecha_actualizacion=datetime.now()
        )
        tickets_store.append(ticket)
        return ticket

    # **kwargs absorbe los filtros que se vayan anadiendo a la firma real (grupo,
    # y los que vengan). Este mock solo existe para los tests de RBAC del router;
    # el comportamiento del filtrado se prueba de verdad en tests/integration/.
    def mock_obtener_tickets(db, q=None, estado=None, limit=100, offset=0, **kwargs):
        res = tickets_store[:]
        if estado and estado != "todos":
            res = [t for t in res if t.estado == estado]
        if q and q.strip():
            term = q.strip().lower()
            res = [
                t for t in res
                if term in (t.instalador or "").lower()
                or term in (t.obra or "").lower()
                or term in (t.sintoma or "").lower()
                or term in (t.numero_ticket or "").lower()
            ]
        return res

    def mock_obtener_ticket_id(db, ticket_id):
        for t in tickets_store:
            if t.id == ticket_id:
                return t
        return None

    def mock_actualizar_ticket(db, ticket_id, datos):
        t = mock_obtener_ticket_id(db, ticket_id)
        if not t:
            return None
        for k, v in datos.items():
            if hasattr(t, k) and v is not None:
                setattr(t, k, v)
        return t

    def mock_registrar_cierre(db, ticket_id, datos, autor=""):
        t = mock_obtener_ticket_id(db, ticket_id)
        if not t:
            return None
        for k, v in datos.items():
            if hasattr(t, k) and v is not None:
                setattr(t, k, v)
        t.cierre_fecha = datetime.now()
        t.cierre_por = autor
        return t

    def mock_eliminar_ticket(db, ticket_id):
        t = mock_obtener_ticket_id(db, ticket_id)
        if not t:
            return False
        tickets_store.remove(t)
        return True

    def mock_stats(db):
        return {
            "total": len(tickets_store),
            "en_espera": len([t for t in tickets_store if t.estado == "en_espera"]),
            "resuelto": len([t for t in tickets_store if t.estado == "resuelto"]),
            "rma_pendiente": len([t for t in tickets_store if t.estado == "rma_pendiente"])
        }

    comentarios_store = []
    comentario_seq = [1]

    def mock_agregar_comentario(db, ticket_id, autor, texto, tipo="nota", metadata_json=""):
        c_id = comentario_seq[0]
        comentario_seq[0] += 1
        c = database.TicketComentario(
            id=c_id,
            ticket_id=ticket_id,
            autor=autor,
            texto=texto,
            tipo=tipo,
            metadata_json=metadata_json,
            fecha=datetime.now()
        )
        comentarios_store.append(c)
        return c

    def mock_obtener_comentarios(db, ticket_id):
        return [c for c in comentarios_store if c.ticket_id == ticket_id]

    def mock_obtener_para_export(db, q=None, estado=None):
        return mock_obtener_tickets(db, q=q, estado=estado)

    monkeypatch.setattr(database, "crear_ticket_sat", mock_crear_ticket)
    monkeypatch.setattr(database, "obtener_tickets_sat", mock_obtener_tickets)
    monkeypatch.setattr(database, "obtener_ticket_por_id", mock_obtener_ticket_id)
    monkeypatch.setattr(database, "actualizar_ticket_sat", mock_actualizar_ticket)
    monkeypatch.setattr(database, "eliminar_ticket_sat", mock_eliminar_ticket)
    monkeypatch.setattr(database, "registrar_cierre_tecnico", mock_registrar_cierre)
    monkeypatch.setattr(database, "obtener_stats_tickets_sat", mock_stats)
    monkeypatch.setattr(database, "agregar_comentario_ticket", mock_agregar_comentario)
    monkeypatch.setattr(database, "obtener_comentarios_ticket", mock_obtener_comentarios)
    monkeypatch.setattr(database, "obtener_tickets_para_export", mock_obtener_para_export)


def test_tecnico_puede_crear_y_listar_ticket(client, mock_users):
    """Verifica que un técnico puede crear un ticket y recuperarlo de la lista."""
    headers = mock_users["headers"]["tecnico"]

    ticket_payload = {
        "instalador": "Instalaciones Paco",
        "telefono": "612345678",
        "obra": "Residencial Las Rozas Ch-14",
        "distribuidor": "Solven",
        "dispositivo": "Connect-1",
        "motor": "Somfy 4 hilos",
        "sintoma": "Persiana sube al pulsar bajar",
        "diagnostico": "Inversión de fases marrón y negro",
        "solucion": "Intercambiar cables en bornes L1 y L2",
        "estado": "en_espera",
        "prioridad": "normal",
        "notas": "Quedan en probar el jueves"
    }

    # 1. Crear
    res_post = client.post("/api/sat/tickets", json=ticket_payload, headers=headers)
    assert res_post.status_code == 201
    data = res_post.json()
    assert data["instalador"] == "Instalaciones Paco"
    assert data["numero_ticket"].startswith("SAT-")
    ticket_id = data["id"]

    # 2. Listar
    res_list = client.get("/api/sat/tickets", headers=headers)
    assert res_list.status_code == 200
    tickets = res_list.json()
    assert any(t["id"] == ticket_id for t in tickets)

    # 3. Stats
    res_stats = client.get("/api/sat/tickets/stats", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total"] >= 1
    assert stats["en_espera"] >= 1


def test_tecnico_puede_actualizar_estado_ticket(client, mock_users):
    """Verifica que el técnico puede cambiar el estado y notas del ticket."""
    headers = mock_users["headers"]["tecnico"]

    # Crear ticket
    res_crear = client.post("/api/sat/tickets", json={
        "instalador": "Aluminios Gómez",
        "sintoma": "Parpadeo continuo C-Pulsar",
        "dispositivo": "C-Pulsar"
    }, headers=headers)
    assert res_crear.status_code == 201
    ticket_id = res_crear.json()["id"]

    # G10: sin cierre técnico, el paso a 'resuelto' se rechaza
    res_sin_cierre = client.put(f"/api/sat/tickets/{ticket_id}", json={
        "estado": "resuelto"
    }, headers=headers)
    assert res_sin_cierre.status_code == 400
    assert "cierre técnico" in res_sin_cierre.json()["detail"]

    # Con el cierre registrado, ya se puede
    res_cierre = client.post(f"/api/sat/tickets/{ticket_id}/cierre", json={
        "resuelto": True,
        "documentacion_suficiente": True,
        "marcar_resuelto": False
    }, headers=headers)
    assert res_cierre.status_code == 200

    res_put = client.put(f"/api/sat/tickets/{ticket_id}", json={
        "estado": "resuelto",
        "notas": "Confirmado por teléfono, cable arreglado"
    }, headers=headers)
    assert res_put.status_code == 200
    assert res_put.json()["estado"] == "resuelto"
    assert "cable arreglado" in res_put.json()["notas"]


def test_comercial_bloqueado_en_tickets_sat(client, mock_users):
    """CRÍTICO RBAC: Un comercial NO puede acceder al registro de tickets SAT (403)."""
    headers = mock_users["headers"]["comercial"]

    # Listar
    res_get = client.get("/api/sat/tickets", headers=headers)
    assert res_get.status_code == 403

    # Crear
    res_post = client.post("/api/sat/tickets", json={
        "instalador": "Intento Comercial",
        "sintoma": "Fallo"
    }, headers=headers)
    assert res_post.status_code == 403


def test_anonimo_bloqueado_en_tickets_sat(client):
    """Un usuario anónimo debe recibir 401 Unauthorized."""
    res_get = client.get("/api/sat/tickets")
    assert res_get.status_code == 401


def test_busqueda_filtrada_tickets(client, mock_users):
    """Verifica el filtro de búsqueda por instalador u obra."""
    headers = mock_users["headers"]["admin"]

    # Crear ticket con nombre único
    client.post("/api/sat/tickets", json={
        "instalador": "ZetaVentanas Pozuelo",
        "obra": "Edificio Singular 99",
        "sintoma": "Fallo final de carrera"
    }, headers=headers)

    # Buscar por texto que coincida
    res_search = client.get("/api/sat/tickets?q=ZetaVentanas", headers=headers)
    assert res_search.status_code == 200
    encontrados = res_search.json()
    assert len(encontrados) >= 1
    assert any("ZetaVentanas" in t["instalador"] for t in encontrados)

    # Buscar por texto que no coincida
    res_empty = client.get("/api/sat/tickets?q=TextoInexistenteXYZ123", headers=headers)
    assert res_empty.status_code == 200
    assert len(res_empty.json()) == 0


def test_descargar_pdf_ticket_sat_tecnico(client, mock_users):
    """Verifica que un técnico puede generar y descargar el PDF oficial A4 del ticket."""
    headers = mock_users["headers"]["tecnico"]

    # Crear ticket
    res_post = client.post("/api/sat/tickets", json={
        "instalador": "Instalaciones Norte",
        "telefono": "655443322",
        "obra": "Edificio Mirasierra",
        "distribuidor": "Solven",
        "dispositivo": "Connect-1",
        "sintoma": "Inversión de giro",
        "diagnostico": "Fases intercambiadas",
        "solucion": "Permutar marrón y negro"
    }, headers=headers)
    assert res_post.status_code == 201
    ticket_id = res_post.json()["id"]
    numero = res_post.json()["numero_ticket"]

    # Descargar PDF
    res_pdf = client.get(f"/api/sat/tickets/{ticket_id}/pdf", headers=headers)
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert f"Parte_SAT_{numero}.pdf" in res_pdf.headers["content-disposition"]
    assert res_pdf.content.startswith(b"%PDF-")


def test_comercial_no_puede_descargar_pdf_ticket(client, mock_users):
    """Verifica que el rol comercial no puede descargar el PDF del ticket (403)."""
    headers = mock_users["headers"]["comercial"]
    res_pdf = client.get("/api/sat/tickets/1/pdf", headers=headers)
    assert res_pdf.status_code == 403


def test_comentarios_ticket_historial(client, mock_users):
    """Verifica el flujo de auditoría y comentarios: creación automática, cambio de estado y nota manual."""
    headers = mock_users["headers"]["tecnico"]

    # 1. Crear ticket
    res_post = client.post("/api/sat/tickets", json={
        "instalador": "Paco Instalaciones",
        "sintoma": "Fallo wifi en Connect-1"
    }, headers=headers)
    assert res_post.status_code == 201
    ticket_id = res_post.json()["id"]

    # 2. Agregar nota manual
    res_com = client.post(f"/api/sat/tickets/{ticket_id}/comentarios", json={
        "texto": "Se llama al instalador y se le indica revisar la banda 2.4 GHz",
        "tipo": "seguimiento"
    }, headers=headers)
    assert res_com.status_code == 201
    assert res_com.json()["tipo"] == "seguimiento"
    assert "revisar la banda 2.4" in res_com.json()["texto"]

    # 3. Cerrar técnicamente (G10): registra el cierre y pasa a 'resuelto'
    res_put = client.post(f"/api/sat/tickets/{ticket_id}/cierre", json={
        "resuelto": True,
        "documentacion_suficiente": False,
        "alternativa": "Se guio por teléfono paso a paso"
    }, headers=headers)
    assert res_put.status_code == 200
    assert res_put.json()["estado"] == "resuelto"

    # 4. Listar comentarios y verificar trazabilidad
    res_list = client.get(f"/api/sat/tickets/{ticket_id}/comentarios", headers=headers)
    assert res_list.status_code == 200
    comentarios = res_list.json()
    assert len(comentarios) >= 3
    tipos = [c["tipo"] for c in comentarios]
    assert "creacion" in tipos
    assert "seguimiento" in tipos
    assert "cambio_estado" in tipos


def test_exportar_tickets_csv(client, mock_users):
    """Verifica la exportación del listado de tickets a formato CSV con cabeceras y delimitador."""
    headers = mock_users["headers"]["tecnico"]

    # Crear al menos un ticket
    client.post("/api/sat/tickets", json={
        "instalador": "Cerramientos Levante",
        "obra": "Residencial Palmeras",
        "sintoma": "Motor no responde a pulsador C-Wall"
    }, headers=headers)

    res_csv = client.get("/api/sat/tickets/export/csv", headers=headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "tickets_sat_export.csv" in res_csv.headers["content-disposition"]
    contenido = res_csv.content.decode("utf-8-sig")
    assert "Número Ticket" in contenido
    assert "Cerramientos Levante" in contenido
    assert "Residencial Palmeras" in contenido


def test_cuestionario_asistencia_top_diagnosticos(client, mock_users):
    """Verifica que el triaje de cuestionario de asistencia devuelve top_diagnosticos y ticket_prefill."""
    headers = mock_users["headers"]["tecnico"]

    payload = {
        "dispositivo": "Connect-1",
        "partner": "IoT Fenster",
        "area_incidencia": "Motor / instalación",
        "estado_control_fisico": "Sí",
        "estado_control_app": "No",
        "sintomas_observados": ["Giro invertido", "bajar sube"]
    }
    res = client.post("/api/sat/asistencia-triage", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["exito"] is True
    assert "top_diagnosticos" in data
    assert "ticket_prefill" in data
    assert data["ticket_prefill"]["dispositivo"] == "Connect-1"


def test_cuestionario_12_bloques_evaluaciones(client, mock_users):
    """Verifica reglas avanzadas del cuestionario de 12 bloques: equivalencias de marca, comprobaciones hardware y filtrado de pasos."""
    headers = mock_users["headers"]["tecnico"]

    # Caso 1: VBH GreenTeQ con inversión de fases y paso ya probado
    res1 = client.post("/api/sat/asistencia-triage", json={
        "partner": "VBH / GreenTeQ",
        "dispositivo": "Connect-1",
        "sintomas_observados": ["Sube en vez de bajar (giro invertido)"],
        "acciones_realizadas": ["Inversión de fases o sentido de giro en app"]
    }, headers=headers)
    assert res1.status_code == 200
    d1 = res1.json()
    assert "Inversión" in d1["diagnostico_titulo"]
    assert "GreenTeQ Wave 1" in d1["equivalencia_partner"]
    probados = [p for p in d1["pasos_accion"] if p["ya_probado"]]
    assert len(probados) >= 1

    # Caso 2: Connect-1 relés conmutan pero motor no responde
    res2 = client.post("/api/sat/asistencia-triage", json={
        "partner": "IoT Fenster",
        "dispositivo": "Connect-1",
        "sintomas_observados": ["Funciona por app pero no por pulsador"],
        "info_especifica": {
            "hw_c1": {
                "controla_persiana": True,
                "motor_responde": False,
                "oyen_reles": True,
                "calib_termina": False
            }
        }
    }, headers=headers)
    assert res2.status_code == 200
    d2 = res2.json()
    assert "Relés" in d2["diagnostico_titulo"] or "Neutro" in d2["causa_raiz"]

    # Caso 3: Incompatibilidad WPA3 / Wi-Fi 6
    res3 = client.post("/api/sat/asistencia-triage", json={
        "partner": "Procomsa / ICON",
        "dispositivo": "Connect-1",
        "wifi_info": {
            "seguridad": "WPA3",
            "generacion": "Wi-Fi 6"
        },
        "sintomas_observados": ["Aparece offline"]
    }, headers=headers)
    assert res3.status_code == 200
    d3 = res3.json()
    assert "WPA3" in d3["diagnostico_titulo"]

    # Caso 4: Incidencia global (todos los dispositivos de la vivienda afectados)
    res4 = client.post("/api/sat/asistencia-triage", json={
        "partner": "Kömmerling / Konect",
        "dispositivo": "Connect-1",
        "num_dispositivos_afectados": "Todos los de la vivienda/instalación",
        "area_incidencia": "Wi-Fi / conectividad",
        "sintomas_observados": ["Aparece offline / desconectado"]
    }, headers=headers)
    assert res4.status_code == 200
    d4 = res4.json()
    assert "General" in d4["diagnostico_titulo"] or "Global" in d4["diagnostico_titulo"]




# ---------------------------------------------------------------------
# Cierre técnico estructurado (G10)
# ---------------------------------------------------------------------

def _crear_ticket(client, headers) -> int:
    res = client.post("/api/sat/tickets", json={
        "instalador": "Ventanas del Sur",
        "sintoma": "No vincula el mando tras cambiar el router",
        "dispositivo": "Connect-2"
    }, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def test_cierre_requiere_los_dos_campos_clave(client, mock_users):
    """Sin 'resuelto' y 'documentacion_suficiente' el cuerpo no valida (422).

    Son los dos campos que sostienen las métricas de G15; el resto del cierre
    es opcional a propósito para no frenar al técnico.
    """
    headers = mock_users["headers"]["tecnico"]
    ticket_id = _crear_ticket(client, headers)

    res = client.post(f"/api/sat/tickets/{ticket_id}/cierre", json={
        "descripcion": "Se solucionó, pero no digo cómo"
    }, headers=headers)

    assert res.status_code == 422
    faltan = {tuple(e["loc"])[-1] for e in res.json()["detail"]}
    assert {"resuelto", "documentacion_suficiente"} <= faltan


def test_cierre_marca_resuelto_y_devuelve_el_bloque_de_cierre(client, mock_users):
    headers = mock_users["headers"]["tecnico"]
    ticket_id = _crear_ticket(client, headers)

    res = client.post(f"/api/sat/tickets/{ticket_id}/cierre", json={
        "resuelto": True,
        "documentacion_suficiente": True,
        "descripcion": "Reconfigurado en 2.4 GHz",
        "escalado": False
    }, headers=headers)

    assert res.status_code == 200
    cuerpo = res.json()
    assert cuerpo["estado"] == "resuelto"
    assert cuerpo["cierre"]["resuelto"] is True
    assert cuerpo["cierre"]["documentacion_suficiente"] is True
    assert cuerpo["cierre"]["descripcion"] == "Reconfigurado en 2.4 GHz"
    assert cuerpo["cierre"]["por"]


def test_cierre_sin_resolver_no_cambia_el_estado(client, mock_users):
    """Cerrar diciendo que no se resolvió documenta el caso sin falsear el flujo."""
    headers = mock_users["headers"]["tecnico"]
    ticket_id = _crear_ticket(client, headers)

    res = client.post(f"/api/sat/tickets/{ticket_id}/cierre", json={
        "resuelto": False,
        "documentacion_suficiente": False,
        "alternativa": "Pendiente de recambio, se abre RMA"
    }, headers=headers)

    assert res.status_code == 200
    assert res.json()["estado"] == "en_espera"
    assert res.json()["cierre"]["resuelto"] is False


def test_ticket_sin_cerrar_devuelve_cierre_nulo(client, mock_users):
    """None y un cierre con todo a false son cosas distintas."""
    headers = mock_users["headers"]["tecnico"]
    ticket_id = _crear_ticket(client, headers)

    res = client.get(f"/api/sat/tickets/{ticket_id}", headers=headers)

    assert res.status_code == 200
    assert res.json()["cierre"] is None


def test_cierre_en_ticket_inexistente_devuelve_404(client, mock_users):
    headers = mock_users["headers"]["tecnico"]

    res = client.post("/api/sat/tickets/999999/cierre", json={
        "resuelto": True, "documentacion_suficiente": True
    }, headers=headers)

    assert res.status_code == 404


def test_comercial_no_puede_cerrar_tickets(client, mock_users):
    """RBAC: el cierre técnico es de técnicos y administradores."""
    headers_tecnico = mock_users["headers"]["tecnico"]
    ticket_id = _crear_ticket(client, headers_tecnico)

    res = client.post(f"/api/sat/tickets/{ticket_id}/cierre", json={
        "resuelto": True, "documentacion_suficiente": True
    }, headers=mock_users["headers"]["comercial"])

    assert res.status_code == 403
