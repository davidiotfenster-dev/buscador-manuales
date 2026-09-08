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

    def mock_obtener_tickets(db, q=None, estado=None, limit=100, offset=0):
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

    monkeypatch.setattr(database, "crear_ticket_sat", mock_crear_ticket)
    monkeypatch.setattr(database, "obtener_tickets_sat", mock_obtener_tickets)
    monkeypatch.setattr(database, "obtener_ticket_por_id", mock_obtener_ticket_id)
    monkeypatch.setattr(database, "actualizar_ticket_sat", mock_actualizar_ticket)
    monkeypatch.setattr(database, "eliminar_ticket_sat", mock_eliminar_ticket)
    monkeypatch.setattr(database, "obtener_stats_tickets_sat", mock_stats)


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

    # Actualizar estado a 'resuelto'
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

