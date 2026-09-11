"""
Router de Asistencia Técnica SAT, Triaje Inteligente y Mini-CRM de Incidencias.
"""

import csv
import io
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from .. import database
from ..auth import require_tecnico_or_admin, get_current_user_optional

router = APIRouter(tags=["SAT y Tickets"])

def _serializar_ticket(t) -> Dict[str, Any]:
    """Serializa un TicketSAT al dict de respuesta común de la API (evita repetir el mismo bloque en cada endpoint)."""
    return {
        "id": t.id,
        "numero_ticket": t.numero_ticket,
        "instalador": t.instalador,
        "telefono": t.telefono,
        "email": t.email or "",
        "obra": t.obra,
        "distribuidor": t.distribuidor,
        "dispositivo": t.dispositivo,
        "motor": t.motor,
        "sintoma": t.sintoma,
        "diagnostico": t.diagnostico,
        "solucion": t.solucion,
        "estado": t.estado,
        "prioridad": t.prioridad,
        "creado_por": t.creado_por,
        "notas": t.notas,
        "fecha_creacion": t.fecha_creacion.isoformat() if t.fecha_creacion else None,
        "fecha_actualizacion": t.fecha_actualizacion.isoformat() if t.fecha_actualizacion else None,
    }

class TicketComentarioCreate(BaseModel):
    texto: str
    tipo: Optional[str] = "nota"
    metadata_json: Optional[str] = ""

class TicketSATCreate(BaseModel):
    instalador: str
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    obra: Optional[str] = ""
    distribuidor: Optional[str] = ""
    dispositivo: Optional[str] = ""
    motor: Optional[str] = ""
    sintoma: str
    diagnostico: Optional[str] = ""
    solucion: Optional[str] = ""
    estado: Optional[str] = "en_espera"
    prioridad: Optional[str] = "normal"
    notas: Optional[str] = ""

class TicketSATUpdate(BaseModel):
    instalador: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    obra: Optional[str] = None
    distribuidor: Optional[str] = None
    dispositivo: Optional[str] = None
    motor: Optional[str] = None
    sintoma: Optional[str] = None
    diagnostico: Optional[str] = None
    solucion: Optional[str] = None
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    notas: Optional[str] = None

class AutoTicketRequest(BaseModel):
    instalador: str
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    obra: Optional[str] = ""
    distribuidor: Optional[str] = ""
    dispositivo: Optional[str] = ""
    motor: Optional[str] = ""
    sintoma: str
    diagnostico: Optional[str] = ""
    solucion: Optional[str] = ""
    estado: Optional[str] = "resuelto"
    prioridad: Optional[str] = "normal"
    notas: Optional[str] = ""
    enviar_email: Optional[bool] = True
    manual_info: Optional[Dict[str, Any]] = None

class EnviarEmailTicketRequest(BaseModel):
    email: Optional[str] = None
    manual_info: Optional[Dict[str, Any]] = None

@router.get("/api/sat/tickets")
def listar_tickets_sat(
    q: Optional[str] = None,
    estado: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    response: Response = None,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    db = database.SessionLocal()
    try:
        tickets_res = database.obtener_tickets_sat(db, q=q, estado=estado, limit=limit, offset=offset)
        if isinstance(tickets_res, tuple):
            tickets, total = tickets_res
        else:
            tickets, total = tickets_res, len(tickets_res)

        if response:
            response.headers["X-Total-Count"] = str(total)
            response.headers["X-Limit"] = str(limit)
            response.headers["X-Offset"] = str(offset)

        return [_serializar_ticket(t) for t in tickets]
    finally:
        db.close()

@router.get("/api/sat/tickets/export/csv")
def exportar_tickets_csv(
    q: Optional[str] = None,
    estado: Optional[str] = None,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    """Exporta todos los tickets filtrados a un archivo CSV con codificación UTF-8 BOM."""
    db = database.SessionLocal()
    try:
        tickets = database.obtener_tickets_para_export(db, q=q, estado=estado)
        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "ID", "Número Ticket", "Fecha Creación", "Instalador", "Teléfono", "Email",
            "Obra", "Distribuidor", "Dispositivo", "Motor", "Síntoma", "Diagnóstico",
            "Solución", "Estado", "Prioridad", "Creado Por", "Notas"
        ])
        for t in tickets:
            writer.writerow([
                t.id,
                t.numero_ticket,
                t.fecha_creacion.strftime("%Y-%m-%d %H:%M") if t.fecha_creacion else "",
                t.instalador or "",
                t.telefono or "",
                t.email or "",
                t.obra or "",
                t.distribuidor or "",
                t.dispositivo or "",
                t.motor or "",
                (t.sintoma or "").replace("\r\n", " ").replace("\n", " "),
                (t.diagnostico or "").replace("\r\n", " ").replace("\n", " "),
                (t.solucion or "").replace("\r\n", " ").replace("\n", " "),
                t.estado or "",
                t.prioridad or "",
                t.creado_por or "",
                (t.notas or "").replace("\r\n", " ").replace("\n", " ")
            ])
        csv_bytes = output.getvalue().encode("utf-8-sig")
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="tickets_sat_export.csv"'}
        )
    finally:
        db.close()

@router.get("/api/sat/tickets/stats")
def stats_tickets_sat(current_user: database.User = Depends(require_tecnico_or_admin)):
    db = database.SessionLocal()
    try:
        return database.obtener_stats_tickets_sat(db)
    finally:
        db.close()

@router.get("/api/sat/tickets/{ticket_id}")
def obtener_ticket_sat(ticket_id: int, current_user: database.User = Depends(require_tecnico_or_admin)):
    db = database.SessionLocal()
    try:
        t = database.obtener_ticket_por_id(db, ticket_id)
        if not t:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return _serializar_ticket(t)
    finally:
        db.close()

@router.post("/api/sat/tickets", status_code=status.HTTP_201_CREATED)
def crear_ticket_sat_endpoint(
    ticket: TicketSATCreate,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    if not ticket.instalador.strip() or not ticket.sintoma.strip():
        raise HTTPException(status_code=400, detail="El instalador y el síntoma son campos obligatorios")
    db = database.SessionLocal()
    try:
        payload = ticket.model_dump() if hasattr(ticket, "model_dump") else ticket.dict()
        nuevo = database.crear_ticket_sat(db, payload, creado_por=current_user.email)
        database.agregar_comentario_ticket(
            db,
            ticket_id=nuevo.id,
            autor=current_user.email,
            texto="Ticket registrado manualmente en el CRM.",
            tipo="creacion"
        )
        return _serializar_ticket(nuevo)
    finally:
        db.close()

@router.post("/api/sat/tickets/auto-registrar-enviar", status_code=status.HTTP_201_CREATED)
def auto_registrar_y_enviar_ticket(
    req: AutoTicketRequest,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    from ..pdf_generator import generar_pdf_ticket_sat
    from ..email_sender import enviar_email_resolucion_sat

    if not req.instalador.strip():
        req.instalador = "Técnico / Instalador"
    if not req.sintoma.strip():
        req.sintoma = "Incidencia de asistencia técnica asistida por IA"

    db = database.SessionLocal()
    try:
        payload = {
            "instalador": req.instalador.strip(),
            "telefono": req.telefono.strip() if req.telefono else "",
            "email": req.email.strip() if req.email else "",
            "obra": req.obra.strip() if req.obra else "",
            "distribuidor": req.distribuidor.strip() if req.distribuidor else "",
            "dispositivo": req.dispositivo.strip() if req.dispositivo else "Connect-1",
            "motor": req.motor.strip() if req.motor else "",
            "sintoma": req.sintoma.strip(),
            "diagnostico": req.diagnostico.strip() if req.diagnostico else "",
            "solucion": req.solucion.strip() if req.solucion else "",
            "estado": req.estado or "resuelto",
            "prioridad": req.prioridad or "normal",
            "notas": req.notas.strip() if req.notas else "Registrado automáticamente desde Asistencia Técnica SAT.",
        }

        nuevo_ticket = database.crear_ticket_sat(db, payload, creado_por=current_user.email)
        database.agregar_comentario_ticket(
            db,
            ticket_id=nuevo_ticket.id,
            autor=current_user.email,
            texto="Ticket registrado automáticamente desde Asistencia Técnica SAT.",
            tipo="creacion"
        )
        pdf_buffer = generar_pdf_ticket_sat(nuevo_ticket)
        pdf_bytes = pdf_buffer.getvalue()

        email_resultado = {"enviado": False, "motivo": "No se solicitó envío de correo"}
        if req.enviar_email and req.email and req.email.strip():
            email_resultado = enviar_email_resolucion_sat(
                nuevo_ticket,
                pdf_bytes=pdf_bytes,
                destinatario_email=req.email.strip(),
                manual_info=req.manual_info
            )
            if email_resultado.get("enviado"):
                database.agregar_comentario_ticket(
                    db,
                    ticket_id=nuevo_ticket.id,
                    autor=current_user.email,
                    texto=f"Parte oficial enviado por email a {req.email.strip()}",
                    tipo="email_enviado"
                )

        return {
            "ok": True,
            "ticket": _serializar_ticket(nuevo_ticket),
            "pdf_url": f"/api/sat/tickets/{nuevo_ticket.id}/pdf",
            "pdf_filename": f"Parte_SAT_{nuevo_ticket.numero_ticket}.pdf",
            "email_resultado": email_resultado
        }
    finally:
        db.close()

@router.post("/api/sat/tickets/{ticket_id}/enviar-email")
def enviar_email_ticket_sat_endpoint(
    ticket_id: int,
    datos: Optional[EnviarEmailTicketRequest] = None,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    from ..pdf_generator import generar_pdf_ticket_sat
    from ..email_sender import enviar_email_resolucion_sat

    db = database.SessionLocal()
    try:
        ticket = database.obtener_ticket_por_id(db, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")

        dest_email = ""
        if datos and datos.email and datos.email.strip():
            dest_email = datos.email.strip()
            if not ticket.email:
                database.actualizar_ticket_sat(db, ticket_id, {"email": dest_email})
        elif ticket.email:
            dest_email = ticket.email.strip()

        if not dest_email:
            raise HTTPException(status_code=400, detail="No se ha especificado ninguna dirección de correo electrónico.")

        pdf_buffer = generar_pdf_ticket_sat(ticket)
        manual_info = datos.manual_info if datos else None
        res_email = enviar_email_resolucion_sat(
            ticket,
            pdf_bytes=pdf_buffer.getvalue(),
            destinatario_email=dest_email,
            manual_info=manual_info
        )
        if res_email.get("enviado"):
            database.agregar_comentario_ticket(
                db,
                ticket_id=ticket_id,
                autor=current_user.email,
                texto=f"Parte oficial reenviado por email a {dest_email}",
                tipo="email_enviado"
            )
        return {"ok": res_email.get("enviado", False), "resultado": res_email}
    finally:
        db.close()

@router.put("/api/sat/tickets/{ticket_id}")
def actualizar_ticket_sat_endpoint(
    ticket_id: int,
    ticket_update: TicketSATUpdate,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    db = database.SessionLocal()
    try:
        ticket_prev = database.obtener_ticket_por_id(db, ticket_id)
        if not ticket_prev:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        estado_prev = ticket_prev.estado

        raw_dict = ticket_update.model_dump() if hasattr(ticket_update, "model_dump") else ticket_update.dict()
        datos = {k: v for k, v in raw_dict.items() if v is not None}
        actualizado = database.actualizar_ticket_sat(db, ticket_id, datos)

        if "estado" in datos and datos["estado"] != estado_prev:
            database.agregar_comentario_ticket(
                db,
                ticket_id=ticket_id,
                autor=current_user.email,
                texto=f"Estado modificado de '{estado_prev}' a '{datos['estado']}'",
                tipo="cambio_estado",
                metadata_json=json.dumps({"estado_anterior": estado_prev, "estado_nuevo": datos["estado"]})
            )
        if "notas" in datos and datos["notas"] and datos["notas"] != ticket_prev.notas:
            database.agregar_comentario_ticket(
                db,
                ticket_id=ticket_id,
                autor=current_user.email,
                texto=f"Nota actualizada: {datos['notas']}",
                tipo="nota"
            )
        return _serializar_ticket(actualizado)
    finally:
        db.close()

@router.delete("/api/sat/tickets/{ticket_id}")
def eliminar_ticket_sat_endpoint(
    ticket_id: int,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    db = database.SessionLocal()
    try:
        exito = database.eliminar_ticket_sat(db, ticket_id)
        if not exito:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return {"ok": True, "mensaje": f"Ticket {ticket_id} eliminado"}
    finally:
        db.close()

@router.get("/api/sat/tickets/{ticket_id}/pdf")
def descargar_pdf_ticket_sat_endpoint(
    ticket_id: int,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    from ..pdf_generator import generar_pdf_ticket_sat
    db = database.SessionLocal()
    try:
        ticket = database.obtener_ticket_por_id(db, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        pdf_buffer = generar_pdf_ticket_sat(ticket)
        filename = f"Parte_SAT_{ticket.numero_ticket}.pdf"
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    finally:
        db.close()

@router.get("/api/sat/tickets/{ticket_id}/comentarios")
def listar_comentarios_ticket_endpoint(
    ticket_id: int,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    """Obtiene el historial cronológico de comentarios y eventos de un ticket."""
    db = database.SessionLocal()
    try:
        ticket = database.obtener_ticket_por_id(db, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        comentarios = database.obtener_comentarios_ticket(db, ticket_id)
        return [{
            "id": c.id,
            "ticket_id": c.ticket_id,
            "autor": c.autor,
            "texto": c.texto,
            "tipo": c.tipo,
            "metadata_json": c.metadata_json or "",
            "fecha": c.fecha.isoformat() if c.fecha else None
        } for c in comentarios]
    finally:
        db.close()

@router.post("/api/sat/tickets/{ticket_id}/comentarios", status_code=status.HTTP_201_CREATED)
def agregar_comentario_ticket_endpoint(
    ticket_id: int,
    comentario: TicketComentarioCreate,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    """Agrega una nota manual o comentario al historial de un ticket."""
    if not comentario.texto.strip():
        raise HTTPException(status_code=400, detail="El texto del comentario no puede estar vacío")
    db = database.SessionLocal()
    try:
        ticket = database.obtener_ticket_por_id(db, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        c = database.agregar_comentario_ticket(
            db,
            ticket_id=ticket_id,
            autor=current_user.email,
            texto=comentario.texto.strip(),
            tipo=comentario.tipo or "nota",
            metadata_json=comentario.metadata_json or ""
        )
        return {
            "id": c.id,
            "ticket_id": c.ticket_id,
            "autor": c.autor,
            "texto": c.texto,
            "tipo": c.tipo,
            "metadata_json": c.metadata_json or "",
            "fecha": c.fecha.isoformat() if c.fecha else None
        }
    finally:
        db.close()

@router.post("/api/sat/asistencia-triage")
def endpoint_asistencia_triage(
    datos: dict,
    request: Request,
    current_user: Optional[database.User] = Depends(get_current_user_optional)
):
    from .. import sat_autoresolver
    db = database.SessionLocal()
    try:
        return sat_autoresolver.evaluar_cuestionario_asistencia(datos, db)
    finally:
        db.close()

