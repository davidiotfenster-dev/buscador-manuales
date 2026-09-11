"""
Módulo de Envío Automático de Correos Electrónicos para Partes SAT y Asistencia Técnica.
Envía correos profesionales HTML con el Parte Técnico Oficial en PDF adjunto.
"""

import os
import smtplib
import logging
import html
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional

logger = logging.getLogger("buscador_manuales")

# Configuración SMTP desde variables de entorno
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "soporte@iotfenster.com")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Soporte Técnico IoT Fenster")
SMTP_TLS = os.environ.get("SMTP_TLS", "true").lower() in ("true", "1", "yes")


def generar_cuerpo_html_ticket(ticket, manual_info: Optional[Dict[str, Any]] = None) -> str:
    """Genera una plantilla HTML responsive y moderna para el correo de resolución SAT."""
    numero_ticket = html.escape(str(getattr(ticket, "numero_ticket", "SAT-2026")))
    instalador = html.escape(str(getattr(ticket, "instalador", "Técnico / Instalador")))
    dispositivo = html.escape(str(getattr(ticket, "dispositivo", "Dispositivo IoT Fenster")))
    distribuidor = html.escape(str(getattr(ticket, "distribuidor", "IoT Fenster")))
    obra = html.escape(str(getattr(ticket, "obra", "")))
    sintoma = html.escape(str(getattr(ticket, "sintoma", "")))
    diagnostico = html.escape(str(getattr(ticket, "diagnostico", "")))
    solucion = str(getattr(ticket, "solucion", ""))
    
    # Formatear pasos de solución en lista HTML (escapando cada paso)
    lineas_solucion = [html.escape(s.strip()) for s in solucion.split("\n") if s.strip()]
    if not lineas_solucion:
        lineas_solucion = [html.escape(solucion)] if solucion else ["Revisar conexionado y alimentación eléctrica."]
        
    items_solucion_html = "".join(
        f'<li style="margin-bottom: 8px; color: #334155; line-height: 1.5;">{paso}</li>'
        for paso in lineas_solucion
    )

    info_obra_html = f'<p style="margin: 4px 0; color: #64748b; font-size: 13px;"><strong>Obra / Ubicación:</strong> {obra}</p>' if obra else ''
    info_manual_html = ''
    if manual_info and manual_info.get("nombre"):
        info_manual_html = f'''
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; margin-top: 15px;">
            <p style="margin: 0; color: #166534; font-size: 13px; font-weight: bold;">📄 Documentación Oficial de Referencia:</p>
            <p style="margin: 4px 0 0 0; color: #15803d; font-size: 12px;">{manual_info.get("nombre")} (Página {manual_info.get("pagina", 1)})</p>
        </div>
        '''

    cuerpo_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Parte Técnico Oficial #{numero_ticket}</title>
    </head>
    <body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 20px; color: #0f172a;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 620px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
            
            <!-- Cabecera Corporativa -->
            <tr>
                <td style="background-color: #0a1620; padding: 24px 30px; border-bottom: 3px solid #0097b2;">
                    <table width="100%" border="0" cellpadding="0" cellspacing="0">
                        <tr>
                            <td>
                                <span style="color: #0097b2; font-size: 20px; font-weight: 800; letter-spacing: 0.5px;">IOT FENSTER</span>
                                <span style="color: #94a3b8; font-size: 13px; display: block; margin-top: 2px;">Soporte Técnico Oficial & Ingeniería</span>
                            </td>
                            <td align="right">
                                <span style="background-color: rgba(0,151,178,0.2); color: #5eead4; border: 1px solid rgba(0,151,178,0.4); font-family: monospace; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 6px;">
                                    {numero_ticket}
                                </span>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>

            <!-- Saludo & Resumen -->
            <tr>
                <td style="padding: 24px 30px;">
                    <h2 style="color: #0f2233; font-size: 18px; margin: 0 0 10px 0; font-weight: bold;">
                        Parte Oficial de Asistencia Técnica & Resolución
                    </h2>
                    <p style="color: #475569; font-size: 14px; line-height: 1.5; margin: 0 0 16px 0;">
                        Hola <strong>{instalador}</strong>, a continuación le remitimos el informe técnico oficial emitido por nuestro departamento de soporte para la incidencia registrada.
                    </p>

                    <!-- Tarjeta de Datos del Equipo -->
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 18px; margin-bottom: 20px;">
                        <p style="margin: 0 0 4px 0; color: #0f172a; font-size: 13px;"><strong>Dispositivo:</strong> <span style="color: #0097b2; font-weight: bold;">{dispositivo}</span> {f'({distribuidor})' if distribuidor else ''}</p>
                        {info_obra_html}
                        <p style="margin: 4px 0 0 0; color: #64748b; font-size: 13px;"><strong>Síntoma notificado:</strong> {sintoma}</p>
                    </div>

                    <!-- Diagnóstico Técnico -->
                    <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; border-radius: 4px; padding: 12px 16px; margin-bottom: 20px;">
                        <p style="margin: 0; color: #991b1b; font-size: 12px; font-weight: bold; text-transform: uppercase;">🔍 Causa Raíz Identificada:</p>
                        <p style="margin: 4px 0 0 0; color: #7f1d1d; font-size: 13px; font-weight: 600; line-height: 1.4;">
                            {diagnostico or 'Verificación de conexionado y configuración recomendada.'}
                        </p>
                    </div>

                    <!-- Pasos de Acción Recomendados -->
                    <h3 style="color: #0f2233; font-size: 15px; margin: 0 0 10px 0; font-weight: bold;">
                        🛠️ Instrucciones de Resolución Paso a Paso:
                    </h3>
                    <ol style="margin: 0 0 20px 0; padding-left: 20px; font-size: 13px;">
                        {items_solucion_html}
                    </ol>

                    {info_manual_html}

                    <!-- Aviso de PDF Adjunto -->
                    <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 16px; margin-top: 20px;">
                        <table width="100%" border="0" cellpadding="0" cellspacing="0">
                            <tr>
                                <td width="30" valign="middle">
                                    <span style="font-size: 22px;">📎</span>
                                </td>
                                <td style="color: #1e40af; font-size: 12px; line-height: 1.4;">
                                    <strong>Documento Oficial Adjunto:</strong> Encontrará adjunto en este correo el documento <strong>Parte_SAT_{numero_ticket}.pdf</strong> firmado digitalmente para su archivo o justificación de garantía en obra.
                                </td>
                            </tr>
                        </table>
                    </div>

                </td>
            </tr>

            <!-- Pie de Página -->
            <tr>
                <td style="background-color: #f8fafc; padding: 20px 30px; border-top: 1px solid #e2e8f0; text-align: center;">
                    <p style="color: #94a3b8; font-size: 11px; margin: 0 0 6px 0;">
                        IoT Fenster S.L. · Departamento de Asistencia Técnica Oficial (SAT)<br/>
                        Canal Oficial de Vídeos: <a href="https://www.youtube.com/@MySmartWindow" style="color: #0097b2; text-decoration: none;">@MySmartWindow</a>
                    </p>
                    <p style="color: #cbd5e1; font-size: 10px; margin: 0;">
                        Este mensaje ha sido generado automáticamente por la plataforma de asistencia técnica.
                    </p>
                </td>
            </tr>

        </table>
    </body>
    </html>
    """
    return cuerpo_html


def enviar_email_resolucion_sat(
    ticket,
    pdf_bytes: bytes,
    destinatario_email: Optional[str] = None,
    manual_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Envía el correo electrónico de resolución SAT con el PDF oficial adjunto.
    Si no hay servidor SMTP configurado en variables de entorno, opera en modo
    simulación/log seguro para que el flujo de trabajo no se detenga.
    """
    email_destino = destinatario_email or getattr(ticket, "email", "") or ""
    numero_ticket = getattr(ticket, "numero_ticket", "SAT-2026")
    dispositivo = getattr(ticket, "dispositivo", "Dispositivo IoT")

    if not email_destino:
        return {
            "enviado": False,
            "motivo": "No se ha proporcionado un correo electrónico de destino para el instalador/cliente.",
            "destinatario": ""
        }

    asunto = f"[Soporte Técnico IoT Fenster] Parte Oficial de Asistencia #{numero_ticket} - {dispositivo}"
    cuerpo_html = generar_cuerpo_html_ticket(ticket, manual_info)

    # Crear mensaje MIME multipart
    msg = MIMEMultipart("mixed")
    msg["Subject"] = asunto
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
    msg["To"] = email_destino

    # Adjuntar cuerpo HTML
    parte_html = MIMEText(cuerpo_html, "html", "utf-8")
    msg.attach(parte_html)

    # Adjuntar documento PDF
    if pdf_bytes:
        nombre_adjunto = f"Parte_SAT_{numero_ticket}.pdf"
        parte_pdf = MIMEApplication(pdf_bytes, _subtype="pdf")
        parte_pdf.add_header("Content-Disposition", "attachment", filename=nombre_adjunto)
        msg.attach(parte_pdf)

    # Comprobar si SMTP está configurado en producción
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            logger.info(f"Conectando a servidor SMTP {SMTP_HOST}:{SMTP_PORT} para enviar a {email_destino}...")
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as servidor:
                if SMTP_TLS:
                    servidor.starttls()
                servidor.login(SMTP_USER, SMTP_PASSWORD)
                servidor.sendmail(SMTP_FROM, [email_destino], msg.as_string())
            logger.info(f"Correo SAT #{numero_ticket} enviado exitosamente a {email_destino}.")
            return {
                "enviado": True,
                "destinatario": email_destino,
                "asunto": asunto,
                "adjunto": f"Parte_SAT_{numero_ticket}.pdf",
                "modo": "smtp_real"
            }
        except Exception as e:
            logger.error(f"Error al enviar correo por SMTP: {e}")
            return {
                "enviado": False,
                "error": str(e),
                "destinatario": email_destino,
                "modo": "smtp_error"
            }
    else:
        # Modo simulación / sandbox (desarrollo o local sin SMTP activo)
        logger.info(f"[SIMULACIÓN CORREO SAT] Correo #{numero_ticket} preparado para {email_destino} con PDF adjunto ({len(pdf_bytes)} bytes).")
        return {
            # No se ha enviado nada: devolver True aquí hacía creer al técnico que el
            # parte SAT había salido cuando solo se había escrito una línea de log.
            "enviado": False,
            "destinatario": email_destino,
            "asunto": asunto,
            "adjunto": f"Parte_SAT_{numero_ticket}.pdf",
            "modo": "simulado",
            "mensaje": f"Correo NO enviado: SMTP no está configurado. El parte para {email_destino} se ha generado pero no ha salido."
        }
