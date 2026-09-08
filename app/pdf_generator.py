"""
Generador de Documentos Oficiales PDF para Partes de Asistencia SAT y Órdenes de RMA.
Utiliza ReportLab para componer documentos A4 vectoriales con formato profesional.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm


def generar_pdf_ticket_sat(ticket) -> io.BytesIO:
    """
    Genera un documento PDF oficial A4 para el ticket SAT proporcionado.
    Devuelve un buffer BytesIO listo para ser servido por FastAPI o descargado.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Parte_SAT_{ticket.numero_ticket}",
        author="Soporte Técnico IoT Fenster"
    )

    styles = getSampleStyleSheet()

    # Paleta Corporativa
    COLOR_PRIMARY = colors.HexColor("#0f2233")
    COLOR_TEAL = colors.HexColor("#0097b2")
    COLOR_ACCENT = colors.HexColor("#0284c7")
    COLOR_BG_LIGHT = colors.HexColor("#f1f5f9")
    COLOR_TEXT_MAIN = colors.HexColor("#0f172a")
    COLOR_TEXT_MUTED = colors.HexColor("#475569")
    COLOR_BORDER = colors.HexColor("#cbd5e1")
    COLOR_WHITE = colors.HexColor("#ffffff")

    # Estilos de Párrafo
    style_header_title = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=COLOR_PRIMARY
    )

    style_header_sub = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=COLOR_TEXT_MUTED
    )

    style_ticket_badge = ParagraphStyle(
        "TicketBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        alignment=2, # Derecha
        textColor=COLOR_TEAL
    )

    style_ticket_sub = ParagraphStyle(
        "TicketSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        alignment=2,
        textColor=COLOR_TEXT_MUTED
    )

    style_section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=COLOR_WHITE
    )

    style_cell_label = ParagraphStyle(
        "CellLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=COLOR_TEXT_MUTED
    )

    style_cell_val = ParagraphStyle(
        "CellVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=COLOR_TEXT_MAIN
    )

    style_cell_val_bold = ParagraphStyle(
        "CellValBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=COLOR_PRIMARY
    )

    style_desc_text = ParagraphStyle(
        "DescText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=COLOR_TEXT_MAIN
    )

    style_footer = ParagraphStyle(
        "FooterText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        alignment=1, # Centro
        textColor=COLOR_TEXT_MUTED
    )

    elementos = []

    # -------------------------------------------------------------
    # 1. ENCABEZADO PRINCIPAL (Logo simulado + Título + Referencia)
    # -------------------------------------------------------------
    fecha_emision = ticket.fecha_creacion.strftime("%d/%m/%Y %H:%M") if getattr(ticket, "fecha_creacion", None) else datetime.now().strftime("%d/%m/%Y %H:%M")
    
    estado_nombres = {
        "en_espera": "EN ESPERA (PRUEBA EN OBRA)",
        "resuelto": "RESUELTO Y VERIFICADO",
        "rma_pendiente": "PENDIENTE SUSTITUCIÓN RMA",
        "descartado": "DESCARTADO"
    }
    estado_texto = estado_nombres.get(ticket.estado, (ticket.estado or "EN ESPERA").upper())
    
    encabezado_data = [
        [
            Paragraph("<b>IOT FENSTER</b> · SOPORTE TÉCNICO OFICIAL<br/><font size=7 color='#64748b'>PARTE OFICIAL DE ASISTENCIA TÉCNICA Y ORDEN DE RMA</font>", style_header_title),
            Paragraph(f"<b>Nº PARTE: {ticket.numero_ticket}</b><br/>Fecha: {fecha_emision}<br/>Estado: <b>{estado_texto}</b>", style_ticket_badge)
        ]
    ]

    t_encabezado = Table(encabezado_data, colWidths=[110 * mm, 72 * mm])
    t_encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elementos.append(t_encabezado)
    elementos.append(Spacer(1, 2 * mm))
    elementos.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_TEAL, spaceAfter=4 * mm))

    # -------------------------------------------------------------
    # 2. BLOQUE: DATOS DEL INSTALADOR Y DE LA OBRA
    # -------------------------------------------------------------
    sec1_banner = Table([[Paragraph("1. DATOS DEL INSTALADOR Y DE LA OBRA", style_section_title)]], colWidths=[182 * mm])
    sec1_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(sec1_banner)

    distribuidor_val = ticket.distribuidor if ticket.distribuidor else "Directo Fenster"
    tel_val = ticket.telefono if ticket.telefono else "(No especificado)"
    obra_val = ticket.obra if ticket.obra else "(No especificada)"
    prioridad_val = "URGENTE (En Obra)" if getattr(ticket, "prioridad", "") == "urgente" else "Normal"

    datos_obra = [
        [
            Paragraph("Instalador / Técnico:", style_cell_label),
            Paragraph(ticket.instalador or "-", style_cell_val_bold),
            Paragraph("Teléfono de Contacto:", style_cell_label),
            Paragraph(tel_val, style_cell_val)
        ],
        [
            Paragraph("Referencia / Obra:", style_cell_label),
            Paragraph(obra_val, style_cell_val),
            Paragraph("Distribuidor / Partner:", style_cell_label),
            Paragraph(distribuidor_val, style_cell_val)
        ],
        [
            Paragraph("Atendido Por:", style_cell_label),
            Paragraph(getattr(ticket, "creado_por", "-") or "Soporte Central", style_cell_val),
            Paragraph("Nivel de Prioridad:", style_cell_label),
            Paragraph(prioridad_val, style_cell_val_bold)
        ]
    ]

    t_obra = Table(datos_obra, colWidths=[35 * mm, 56 * mm, 38 * mm, 53 * mm])
    t_obra.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elementos.append(t_obra)
    elementos.append(Spacer(1, 4 * mm))

    # -------------------------------------------------------------
    # 3. BLOQUE: CONFIGURACIÓN DEL EQUIPO Y MOTOR
    # -------------------------------------------------------------
    sec2_banner = Table([[Paragraph("2. IDENTIFICACIÓN DE EQUIPOS Y CABLEADO ELÉCTRICO", style_section_title)]], colWidths=[182 * mm])
    sec2_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(sec2_banner)

    disp_val = ticket.dispositivo if ticket.dispositivo else "Connect-1 (Estándar)"
    motor_val = ticket.motor if ticket.motor else "Motor mecánico tubular 4 hilos (Somfy / Cherubini compatible)"

    datos_equipos = [
        [
            Paragraph("Dispositivo IoT:", style_cell_label),
            Paragraph(disp_val, style_cell_val_bold),
            Paragraph("Tensión Nominal:", style_cell_label),
            Paragraph("230V AC Monofásica · 50Hz", style_cell_val)
        ],
        [
            Paragraph("Motor / Accionador:", style_cell_label),
            Paragraph(motor_val, style_cell_val),
            Paragraph("Capacidad Máx. Relé:", style_cell_label),
            Paragraph("2.2 A / 500W (Protección Térmica)", style_cell_val)
        ]
    ]

    t_equipos = Table(datos_equipos, colWidths=[35 * mm, 56 * mm, 38 * mm, 53 * mm])
    t_equipos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elementos.append(t_equipos)
    elementos.append(Spacer(1, 4 * mm))

    # -------------------------------------------------------------
    # 4. BLOQUE: DIAGNÓSTICO TÉCNICO Y SOLUCIÓN APLICADA
    # -------------------------------------------------------------
    sec3_banner = Table([[Paragraph("3. PERITAJE TÉCNICO, CAUSA RAÍZ Y RESOLUCIÓN", style_section_title)]], colWidths=[182 * mm])
    sec3_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(sec3_banner)

    sintoma_texto = ticket.sintoma or "Sin descripción del síntoma."
    diagnostico_texto = ticket.diagnostico or "Diagnóstico pendiente de validación en obra."
    solucion_texto = ticket.solucion or "Procedimiento estándar según manual técnico de instalación."

    datos_dictamen = [
        [
            Paragraph("<b>Síntoma Notificado:</b>", style_cell_label),
            Paragraph(sintoma_texto, style_desc_text)
        ],
        [
            Paragraph("<b>Causa Raíz Diagnosticada:</b>", style_cell_label),
            Paragraph(diagnostico_texto, style_desc_text)
        ],
        [
            Paragraph("<b>Procedimiento Técnico:</b>", style_cell_label),
            Paragraph(solucion_texto.replace("\n", "<br/>"), style_desc_text)
        ]
    ]

    t_dictamen = Table(datos_dictamen, colWidths=[35 * mm, 147 * mm])
    t_dictamen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elementos.append(t_dictamen)
    elementos.append(Spacer(1, 4 * mm))

    # -------------------------------------------------------------
    # 5. BLOQUE: DICTAMEN DE GARANTÍA Y ORDEN DE RMA
    # -------------------------------------------------------------
    sec4_banner = Table([[Paragraph("4. EVALUACIÓN DE GARANTÍA OFICIAL Y DICTAMEN RMA", style_section_title)]], colWidths=[182 * mm])
    sec4_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(sec4_banner)

    es_rma = (ticket.estado == "rma_pendiente")
    chk_garantia = "[ X ]" if es_rma else "[   ]"
    chk_no_garantia = "[   ]" if es_rma else "[ X ]"

    datos_rma = [
        [
            Paragraph("<b>Veredicto de Garantía:</b>", style_cell_label),
            Paragraph(
                f"<b>{chk_garantia} CUBIERTO POR GARANTÍA OFICIAL DE FÁBRICA</b> (Defecto interno de electrónica / sustitución o abono procedente).<br/>"
                f"<b>{chk_no_garantia} EXCLUSIÓN DE GARANTÍA / FALLO DE MONTAJE</b> (Error en conexión 230V, cable apantallado cortado en obra o sobretensión ajena).",
                style_desc_text
            )
        ]
    ]
    if getattr(ticket, "notas", None):
        datos_rma.append([
            Paragraph("<b>Observaciones / Taller:</b>", style_cell_label),
            Paragraph(ticket.notas, style_desc_text)
        ])

    t_rma = Table(datos_rma, colWidths=[35 * mm, 147 * mm])
    t_rma.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elementos.append(t_rma)
    elementos.append(Spacer(1, 5 * mm))

    # -------------------------------------------------------------
    # 6. BLOQUE: FIRMAS Y CONFORMIDAD
    # -------------------------------------------------------------
    firmas_data = [
        [
            Paragraph("<b>CONFORMIDAD DEL INSTALADOR / CLIENTE</b><br/><font size=6.5 color='#64748b'>Declara haber recibido las indicaciones técnicas y estar conforme con el peritaje.</font>", style_cell_label),
            Paragraph("<b>RESPONSABLE TÉCNICO SAT IOT FENSTER</b><br/><font size=6.5 color='#64748b'>Validación oficial del departamento de ingeniería y soporte de producto.</font>", style_cell_label)
        ],
        [
            Paragraph("<br/><br/><br/>Firma y Sello:<br/>DNI / CIF:", style_cell_label),
            Paragraph("<br/><br/><br/>Firma Autorizada SAT:<br/>ID Técnico: SAT-" + (getattr(ticket, "creado_por", "TECH") or "TECH").split("@")[0].upper(), style_cell_label)
        ]
    ]

    t_firmas = Table(firmas_data, colWidths=[91 * mm, 91 * mm])
    t_firmas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_WHITE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(KeepTogether([t_firmas]))
    elementos.append(Spacer(1, 4 * mm))

    # Pie de página oficial
    elementos.append(Paragraph("Este documento es un comprobante técnico oficial generado por la plataforma IoT Fenster. Válido a efectos de tramitación de RMA y garantía técnica según la Ley de Garantías de Bienes de Consumo.", style_footer))

    # Compilar documento
    doc.build(elementos)
    buffer.seek(0)
    return buffer
