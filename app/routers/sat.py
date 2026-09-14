"""
Router de Asistencia Técnica SAT, Triaje Inteligente y Mini-CRM de Incidencias.
"""

import csv
import io
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from .. import database
from ..auth import require_admin, require_tecnico_or_admin, get_current_user_optional

logger = logging.getLogger("buscador_manuales.sat")

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
        "grupo": t.grupo.code if t.grupo else "",
        "grupo_nombre": t.grupo.name if t.grupo else "",
        "sintoma": t.sintoma,
        "diagnostico": t.diagnostico,
        "solucion": t.solucion,
        "estado": t.estado,
        "prioridad": t.prioridad,
        "creado_por": t.creado_por,
        "notas": t.notas,
        "fecha_creacion": t.fecha_creacion.isoformat() if t.fecha_creacion else None,
        "fecha_actualizacion": t.fecha_actualizacion.isoformat() if t.fecha_actualizacion else None,
        "cierre": _serializar_cierre(t),
    }


def _serializar_cierre(t) -> Optional[Dict[str, Any]]:
    """El cierre técnico del ticket, o None si todavía no se ha cerrado.

    Devolver None en vez de un dict con todo a null deja que la interfaz
    distinga de un vistazo «sin cerrar» de «cerrado diciendo que no»."""
    if not t.cierre_fecha:
        return None
    return {
        "resuelto": t.cierre_resuelto,
        "descripcion": t.cierre_descripcion or "",
        "documentacion_suficiente": t.cierre_doc_suficiente,
        "manual_id": t.cierre_manual_id,
        "manual_nombre": t.cierre_manual.nombre_original if t.cierre_manual else "",
        "video_id": t.cierre_video_id,
        "video_titulo": t.cierre_video.titulo if t.cierre_video else "",
        "doc_texto": t.cierre_doc_texto or "",
        "alternativa": t.cierre_alternativa or "",
        "escalado": t.cierre_escalado,
        "fecha": t.cierre_fecha.isoformat(),
        "por": t.cierre_por or "",
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
    # Codigo del grupo de incidencia (VINCULACION, CONECTIVIDAD...). Faltaba
    # aqui, asi que el selector del formulario enviaba el grupo y pydantic lo
    # descartaba sin decir nada: los 47 tickets de la base tienen grupo_id nulo
    # no por ser anteriores a G2, sino porque el alta nunca lo acepto.
    grupo: Optional[str] = None

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
    # Sin esto no habia forma de clasificar despues un ticket mal etiquetado,
    # ni siquiera a mano.
    grupo: Optional[str] = None

class GrupoIncidenciaCrear(BaseModel):
    code: str
    name: str
    description: Optional[str] = ""
    is_active: Optional[bool] = True
    sort_order: Optional[int] = None
    # Nace 'nuevo': un grupo creado durante una llamada no esta al mismo nivel
    # que los 9 que salieron del analisis de 119 incidencias reales.
    estado_revision: Optional[str] = "nuevo"


class GrupoIncidenciaEditar(BaseModel):
    """El `code` no se edita: es la referencia estable que usan la API y las
    exportaciones. Para renombrar de verdad un grupo, se fusiona con otro."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    estado_revision: Optional[str] = None


class GruposReordenar(BaseModel):
    codigos: List[str]


class GruposFusionar(BaseModel):
    origen: str
    destino: str


class TicketCierreTecnico(BaseModel):
    """Cierre técnico de un ticket (G10).

    `resuelto` y `documentacion_suficiente` no tienen valor por defecto: son los
    dos únicos campos obligatorios, porque son los que sostienen las métricas de
    G15. El resto es opcional a propósito — un técnico al teléfono no puede
    rellenar seis campos, y exigírselos acabaría en tickets sin cerrar.
    """
    resuelto: bool
    documentacion_suficiente: bool
    descripcion: Optional[str] = ""
    manual_id: Optional[int] = None
    video_id: Optional[int] = None
    doc_texto: Optional[str] = ""
    alternativa: Optional[str] = ""
    escalado: Optional[bool] = False
    marcar_resuelto: Optional[bool] = True  # además del cierre, pasar el estado a 'resuelto'


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
    # Lo devuelve el triaje. Ata el ticket con las respuestas que lo originaron,
    # que es lo que permite preguntar despues si el diagnostico acerto.
    cuestionario_id: Optional[int] = None

class EnviarEmailTicketRequest(BaseModel):
    email: Optional[str] = None
    manual_info: Optional[Dict[str, Any]] = None

def _serializar_grupo(g) -> Dict[str, Any]:
    return {
        "code": g.code,
        "name": g.name,
        "description": g.description or "",
        "is_active": g.is_active,
        "sort_order": g.sort_order,
        "estado_revision": g.estado_revision or "estable",
    }


@router.get("/api/sat/grupos")
def listar_grupos_incidencia(
    incluir_inactivos: bool = False,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    """Taxonomía de grupos de incidencia.

    El formulario de alta y el cuestionario leen de aquí, en lugar de la lista
    fija que hasta ahora estaba escrita en el HTML.
    """
    db = database.SessionLocal()
    try:
        grupos = database.obtener_grupos_incidencia(db, solo_activos=not incluir_inactivos)
        return [_serializar_grupo(g) for g in grupos]
    finally:
        db.close()


# ---------------------------------------------------------------------
# Administración de grupos (G2.4) — solo admin
#
# Hasta aquí, añadir o renombrar un grupo exigía escribir una migración: la
# taxonomía era "configurable" solo para quien tocara el repositorio, que era
# justo la crítica original.
# ---------------------------------------------------------------------

@router.post("/api/sat/grupos", status_code=status.HTTP_201_CREATED)
def crear_grupo_incidencia_endpoint(
    grupo: GrupoIncidenciaCrear,
    current_user: database.User = Depends(require_admin)
):
    db = database.SessionLocal()
    try:
        datos = grupo.model_dump() if hasattr(grupo, "model_dump") else grupo.dict()
        return _serializar_grupo(database.crear_grupo_incidencia(db, datos))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.put("/api/sat/grupos/{code}")
def actualizar_grupo_incidencia_endpoint(
    code: str,
    cambios: GrupoIncidenciaEditar,
    current_user: database.User = Depends(require_admin)
):
    db = database.SessionLocal()
    try:
        datos = cambios.model_dump() if hasattr(cambios, "model_dump") else cambios.dict()
        actualizado = database.actualizar_grupo_incidencia(db, code, datos)
        if not actualizado:
            raise HTTPException(status_code=404, detail=f"No existe el grupo {code}")
        return _serializar_grupo(actualizado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.put("/api/sat/grupos/orden/actualizar")
def reordenar_grupos_endpoint(
    orden: GruposReordenar,
    current_user: database.User = Depends(require_admin)
):
    db = database.SessionLocal()
    try:
        grupos = database.reordenar_grupos_incidencia(db, orden.codigos)
        return [_serializar_grupo(g) for g in grupos]
    finally:
        db.close()


@router.post("/api/sat/grupos/fusionar")
def fusionar_grupos_endpoint(
    fusion: GruposFusionar,
    current_user: database.User = Depends(require_admin)
):
    """Mueve los tickets del grupo origen al destino y borra el origen.

    Es lo que hace falta cuando el workshop decide que dos grupos eran el mismo.
    """
    db = database.SessionLocal()
    try:
        return database.fusionar_grupos_incidencia(db, fusion.origen, fusion.destino)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/api/sat/grupos/{code}")
def eliminar_grupo_incidencia_endpoint(
    code: str,
    current_user: database.User = Depends(require_admin)
):
    """Borra un grupo sin usar. Con tickets detrás hay que fusionar o desactivar."""
    db = database.SessionLocal()
    try:
        resultado = database.eliminar_grupo_incidencia(db, code)
        if resultado.get("ok"):
            return {"ok": True, "code": code.strip().upper()}
        if resultado.get("motivo") == "no_existe":
            raise HTTPException(status_code=404, detail=f"No existe el grupo {code}")
        raise HTTPException(
            status_code=409,
            detail=f"El grupo {code.strip().upper()} lo usan {resultado['tickets']} tickets "
                   f"({resultado['secundarios']} como grupo secundario). "
                   f"Fusiónalo con otro o desactívalo en vez de borrarlo.",
        )
    finally:
        db.close()


@router.get("/api/sat/tickets")
def listar_tickets_sat(
    q: Optional[str] = None,
    estado: Optional[str] = None,
    grupo: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    response: Response = None,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    db = database.SessionLocal()
    try:
        tickets_res = database.obtener_tickets_sat(db, q=q, estado=estado, grupo=grupo, limit=limit, offset=offset)
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

        # El cuestionario se guardó antes de que existiera el ticket, así que la
        # relación se completa aquí. Si falla, el ticket sigue siendo válido: lo
        # que se pierde es poder mirar después qué se contestó.
        if req.cuestionario_id:
            try:
                database.vincular_cuestionario_a_ticket(db, req.cuestionario_id, nuevo_ticket.id)
            except Exception as e:
                logger.warning(f"No se pudo vincular el cuestionario {req.cuestionario_id}: {e}")

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

        # G10: no se puede dar por resuelto un ticket sin cierre técnico. Solo se
        # exigen los dos campos que sostienen las métricas; el resto del cierre es
        # opcional. Se comprueba sobre el ticket ya guardado, así que basta con
        # haber pasado antes por POST /cierre.
        pasa_a_resuelto = datos.get("estado") == "resuelto" and estado_prev != "resuelto"
        if pasa_a_resuelto and (ticket_prev.cierre_resuelto is None or ticket_prev.cierre_doc_suficiente is None):
            raise HTTPException(
                status_code=400,
                detail="Para marcar el ticket como resuelto falta el cierre técnico: "
                       "contesta si se resolvió y si la documentación fue suficiente "
                       f"en POST /api/sat/tickets/{ticket_id}/cierre",
            )

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

@router.get("/api/sat/tickets/{ticket_id}/documentacion-sugerida")
def documentacion_sugerida_endpoint(
    ticket_id: int,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    """Vídeos que responden a este ticket, ordenados y con el motivo de cada uno.

    El selector del cierre ofrecía los 43 vídeos del canal en una lista plana:
    dar con el que servía dependía de recordar el título. Esto cruza el grupo de
    incidencia, el dispositivo y el síntoma, que son datos que el ticket ya
    tiene, y devuelve además el segundo exacto en el que aparece lo buscado.

    No sustituye a la lista completa, que se sigue ofreciendo debajo: la
    sugerencia puede equivocarse y el operador tiene que poder ignorarla.
    """
    db = database.SessionLocal()
    try:
        if not database.obtener_ticket_por_id(db, ticket_id):
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return database.sugerir_documentacion_para_ticket(db, ticket_id)
    finally:
        db.close()


@router.post("/api/sat/tickets/{ticket_id}/cierre")
def registrar_cierre_tecnico_endpoint(
    ticket_id: int,
    cierre: TicketCierreTecnico,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    """Registra el cierre técnico y, si procede, pasa el ticket a 'resuelto'."""
    db = database.SessionLocal()
    try:
        ticket = database.obtener_ticket_por_id(db, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")

        # Validar las referencias antes de escribir: si no, la clave foránea
        # revienta con un 500 y el operador no sabe qué ha hecho mal.
        if cierre.manual_id is not None and not db.get(database.Manual, cierre.manual_id):
            raise HTTPException(status_code=400, detail=f"El manual {cierre.manual_id} no existe")
        if cierre.video_id is not None and not db.get(database.Video, cierre.video_id):
            raise HTTPException(status_code=400, detail=f"El vídeo {cierre.video_id} no existe")

        estado_prev = ticket.estado
        actualizado = database.registrar_cierre_tecnico(
            db, ticket_id,
            {
                "cierre_resuelto": cierre.resuelto,
                "cierre_descripcion": cierre.descripcion,
                "cierre_doc_suficiente": cierre.documentacion_suficiente,
                "cierre_manual_id": cierre.manual_id,
                "cierre_video_id": cierre.video_id,
                "cierre_doc_texto": cierre.doc_texto,
                "cierre_alternativa": cierre.alternativa,
                "cierre_escalado": cierre.escalado,
            },
            autor=current_user.email,
        )

        resumen = "resuelto" if cierre.resuelto else "sin resolver"
        documentacion = "suficiente" if cierre.documentacion_suficiente else "insuficiente"
        database.agregar_comentario_ticket(
            db, ticket_id=ticket_id, autor=current_user.email,
            texto=f"Cierre técnico: {resumen}, documentación {documentacion}."
                  + (f" {cierre.descripcion}" if cierre.descripcion else ""),
            tipo="cierre_tecnico",
            metadata_json=json.dumps({
                "resuelto": cierre.resuelto,
                "documentacion_suficiente": cierre.documentacion_suficiente,
                "escalado": bool(cierre.escalado),
            }),
        )

        if cierre.marcar_resuelto and cierre.resuelto and estado_prev != "resuelto":
            actualizado = database.actualizar_ticket_sat(db, ticket_id, {"estado": "resuelto"})
            database.agregar_comentario_ticket(
                db, ticket_id=ticket_id, autor=current_user.email,
                texto=f"Estado modificado de '{estado_prev}' a 'resuelto'",
                tipo="cambio_estado",
                metadata_json=json.dumps({"estado_anterior": estado_prev, "estado_nuevo": "resuelto"}),
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
        resultado = sat_autoresolver.evaluar_cuestionario_asistencia(datos, db)

        # Hasta ahora las respuestas se evaluaban y se tiraban. Guardarlas es lo
        # que permite diseñar la tabla de preguntas (G3.2) con datos en vez de a
        # ojo, y medir si el triaje acierta.
        #
        # Nunca debe tumbar el triaje: si el registro falla, el técnico sigue
        # viendo su diagnóstico. Lo que se pierde es una fila, no la respuesta
        # al cliente.
        try:
            registro = database.guardar_cuestionario_asistencia(
                db, datos, resultado,
                creado_por=current_user.email if current_user else "",
            )
            resultado["cuestionario_id"] = registro.id
        except Exception as e:
            logger.warning(f"No se pudo guardar el cuestionario de asistencia: {e}")

        return resultado
    finally:
        db.close()


@router.get("/api/sat/cuestionarios/stats")
def stats_cuestionarios_endpoint(current_user: database.User = Depends(require_tecnico_or_admin)):
    """Qué se contesta de verdad en el cuestionario.

    Sirve para lo que viene después: un campo que no rellena nadie sobra del
    formulario, y uno que se rellena siempre es candidato a obligatorio. Sin
    esto, la tabla de preguntas de G3.2 se diseñaría a ojo, que es exactamente
    como se llegó a los doce bloques que nadie ha validado.
    """
    db = database.SessionLocal()
    try:
        return database.estadisticas_cuestionarios(db)
    finally:
        db.close()


@router.get("/api/sat/cuestionarios")
def listar_cuestionarios_endpoint(
    limite: int = 50,
    ticket_id: Optional[int] = None,
    current_user: database.User = Depends(require_tecnico_or_admin)
):
    """Los cuestionarios contestados, o los de un ticket concreto."""
    import json

    db = database.SessionLocal()
    try:
        registros = database.obtener_cuestionarios_asistencia(db, limite=limite, ticket_id=ticket_id)
        salida = []
        for r in registros:
            try:
                respuestas = json.loads(r.respuestas_json or "{}")
            except (ValueError, TypeError):
                respuestas = {}
            salida.append({
                "id": r.id,
                "ticket_id": r.ticket_id,
                "creado_por": r.creado_por or "",
                "dispositivo": r.dispositivo or "",
                "area_incidencia": r.area_incidencia or "",
                "diagnostico_titulo": r.diagnostico_titulo or "",
                "confianza": r.confianza,
                "respuestas": respuestas,
                "fecha": r.fecha.isoformat() if r.fecha else None,
            })
        return {"cuestionarios": salida, "total": len(salida)}
    finally:
        db.close()

