import os
import re
import zipfile
import xml.etree.ElementTree as ET
import logging
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("buscador_manuales")

# Rutas de los archivos Excel
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_INCIDENCIAS = os.path.join(BASE_DIR, "nuevo", "Incidencias.xlsx")
PATH_PROBLEMAS_SOL = os.path.join(BASE_DIR, "nuevo", "DOCUMENTACIÓN SAT", "Problemas- soluciones.xlsx")

# Caché en memoria para evitar re-parsear constantemente
_CACHE_INCIDENCIAS: Optional[List[Dict[str, Any]]] = None
_CACHE_PROBLEMAS_SOL: Optional[List[Dict[str, Any]]] = None

STOP_WORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "del", "un", "una", "unos",
    "unas", "por", "con", "no", "se", "su", "para", "al", "o", "es", "que", "lo"
}


def normalizar_texto(texto: str) -> str:
    """Normaliza texto eliminando acentos, mayúsculas y caracteres especiales."""
    if not texto:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFD", str(texto))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return " ".join(s.split())


def _parsear_xlsx(ruta_archivo: str) -> List[List[str]]:
    """Lee un archivo .xlsx sin dependencias externas usando zipfile y XML."""
    if not os.path.exists(ruta_archivo):
        logger.warning(f"Archivo Excel no encontrado: {ruta_archivo}")
        return []

    try:
        with zipfile.ZipFile(ruta_archivo) as z:
            # 1. Leer Shared Strings
            strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                    t = "".join([t_el.text or "" for t_el in si.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")])
                    strings.append(t)

            # 2. Leer Sheet1
            if "xl/worksheets/sheet1.xml" not in z.namelist():
                return []

            tree = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
            rows = tree.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row")
            data = []
            for row in rows:
                vals = []
                for c in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                    t_attr = c.get("t")
                    v_el = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                    if v_el is not None and v_el.text is not None:
                        if t_attr == "s" and v_el.text.isdigit():
                            idx = int(v_el.text)
                            vals.append(strings[idx] if idx < len(strings) else "")
                        else:
                            vals.append(v_el.text)
                    else:
                        vals.append("")
                if any(v.strip() for v in vals):
                    data.append(vals)
            return data
    except Exception as e:
        logger.error(f"Error al parsear Excel {ruta_archivo}: {e}")
        return []


def cargar_base_conocimiento_sat(force_reload: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Carga y cachea las incidencias históricas y la matriz de problemas-soluciones."""
    global _CACHE_INCIDENCIAS, _CACHE_PROBLEMAS_SOL

    if not force_reload and _CACHE_INCIDENCIAS is not None and _CACHE_PROBLEMAS_SOL is not None:
        return _CACHE_INCIDENCIAS, _CACHE_PROBLEMAS_SOL

    # 1. Cargar Incidencias.xlsx (120 casos reales)
    filas_inc = _parsear_xlsx(PATH_INCIDENCIAS)
    incidencias = []
    if filas_inc and len(filas_inc) > 1:
        headers = [normalizar_texto(h) for h in filas_inc[0]]
        for row in filas_inc[1:]:
            # Pad row if needed
            r = row + [""] * (len(headers) - len(row))
            item = {
                "nombre": r[0] if len(r) > 0 else "",
                "id_vivienda": r[1] if len(r) > 1 else "",
                "tipo_cliente": r[2] if len(r) > 2 else "",
                "distribuidor": r[3] if len(r) > 3 else "",
                "dispositivo": r[4] if len(r) > 4 else "",
                "num_dispositivos": r[5] if len(r) > 5 else "",
                "compania_internet": r[6] if len(r) > 6 else "",
                "os_movil": r[7] if len(r) > 7 else "",
                "correo": r[8] if len(r) > 8 else "",
                "fecha_entrada": r[9] if len(r) > 9 else "",
                "problema": r[10] if len(r) > 10 else "",
                "telefono": r[11] if len(r) > 11 else "",
                "estado": r[12] if len(r) > 12 else "",
                "accion_correctiva": r[13] if len(r) > 13 else "",
                "fecha_solucion": r[14] if len(r) > 14 else "",
                "comentario": r[15] if len(r) > 15 else "",
                "id_incidencia": r[16] if len(r) > 16 else "",
            }
            # Campo combinado para búsqueda
            texto_busqueda = f"{item['problema']} {item['comentario']} {item['dispositivo']} {item['accion_correctiva']} {item['distribuidor']}"
            item["texto_norm"] = normalizar_texto(texto_busqueda)
            incidencias.append(item)

    # 2. Cargar Problemas- soluciones.xlsx
    filas_prob = _parsear_xlsx(PATH_PROBLEMAS_SOL)
    problemas = []
    if filas_prob and len(filas_prob) > 1:
        for row in filas_prob[1:]:
            if len(row) >= 3 and any(row):
                item_prob = {
                    "dispositivo": row[0].strip(),
                    "problema": row[1].strip(),
                    "solucion": row[2].strip(),
                    "texto_norm": normalizar_texto(f"{row[0]} {row[1]} {row[2]}")
                }
                problemas.append(item_prob)

    _CACHE_INCIDENCIAS = incidencias
    _CACHE_PROBLEMAS_SOL = problemas
    logger.info(f"Base de conocimiento SAT cargada: {len(incidencias)} incidencias históricas y {len(problemas)} problemas-soluciones.")
    return _CACHE_INCIDENCIAS, _CACHE_PROBLEMAS_SOL


# Palabras clave de parada para no sesgar búsqueda
STOP_WORDS = {"de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "unos", "unas", "por", "para", "con", "no", "si", "se", "lo", "al", "del", "que", "es", "su", "sus", "le", "les", "me"}

def calcular_similitud(texto_consulta: str, texto_objetivo: str, dispositivo_consulta: str = "", dispositivo_objetivo: str = "") -> float:
    """Calcula el score de similitud entre la consulta del usuario y un caso."""
    if not texto_consulta or not texto_objetivo:
        return 0.0

    tokens_q = set(normalizar_texto(texto_consulta).split()) - STOP_WORDS
    tokens_obj = set(normalizar_texto(texto_objetivo).split()) - STOP_WORDS

    if not tokens_q:
        return 0.0

    interseccion = tokens_q.intersection(tokens_obj)
    score_jaccard = len(interseccion) / len(tokens_q)

    # Bonus por coincidencia de frases clave
    norm_q = normalizar_texto(texto_consulta)
    norm_obj = normalizar_texto(texto_objetivo)

    # Conceptos clave de SAT con alto peso
    conceptos_clave = [
        ("rotura", 1.5), ("inversion", 2.0), ("bajar sube", 2.5), ("subir baja", 2.5),
        ("faraday", 2.0), ("jaula", 2.0), ("fuera de linea", 2.0), ("offline", 2.0),
        ("reset", 1.5), ("gestual", 1.8), ("oscilo", 2.2), ("candado", 2.0),
        ("alexa", 1.5), ("wifi", 1.2), ("parpadea", 1.6), ("final de carrera", 2.0),
        ("calibrar", 1.8), ("cable cortado", 2.2), ("pulsador", 1.4), ("alimentacion", 1.5)
    ]
    bonus = 0.0
    for kw, peso in conceptos_clave:
        if kw in norm_q and kw in norm_obj:
            bonus += 0.25 * peso

    # Bonus por dispositivo coincidente
    disp_bonus = 0.0
    if dispositivo_consulta and dispositivo_objetivo:
        norm_d_q = normalizar_texto(dispositivo_consulta)
        norm_d_obj = normalizar_texto(dispositivo_objetivo)
        if norm_d_q in norm_d_obj or norm_d_obj in norm_d_q or "todos" in norm_d_obj:
            disp_bonus = 0.35

    return min(1.0, (score_jaccard * 0.5) + bonus + disp_bonus)


def autoresolver_ticket_sat(
    sintoma: str,
    dispositivo: str = "",
    distribuidor: str = "",
    motor: str = "",
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Motor Inteligente de Auto-Resolución SAT.
    Cruza el síntoma reportado con:
    1. Matriz directa de problemas-soluciones
    2. Casos históricos reales de Incidencias.xlsx
    3. Manuales PDF indexados (página y fragmento exacto)
    4. Videos de YouTube indexados
    """
    incidencias, problemas_sol = cargar_base_conocimiento_sat()

    sintoma_norm = normalizar_texto(sintoma)
    if not sintoma_norm:
        return {
            "exito": False,
            "mensaje": "Debes indicar el síntoma reportado para obtener una solución automática."
        }

    # 1. Buscar en la matriz directa de problemas-soluciones
    mejores_problemas = []
    for prob in problemas_sol:
        score = calcular_similitud(sintoma, prob["problema"], dispositivo, prob["dispositivo"])
        if score > 0.15:
            mejores_problemas.append((score, prob))
    mejores_problemas.sort(key=lambda x: x[0], reverse=True)

    # 2. Buscar en los 120 casos reales históricos
    mejores_historicos = []
    for inc in incidencias:
        score = calcular_similitud(sintoma, inc["comentario"] + " " + inc["problema"], dispositivo, inc["dispositivo"])
        if score > 0.15:
            mejores_historicos.append((score, inc))
    mejores_historicos.sort(key=lambda x: x[0], reverse=True)

    # 3. Recopilar candidatos de todas las fuentes
    candidatos = []

    # A) Reglas expertas automáticas para casos comunes
    if "bajar sube" in sintoma_norm or "al reves" in sintoma_norm or "invertid" in sintoma_norm or "sube cuando bajo" in sintoma_norm:
        candidatos.append({
            "titulo": "Inversión de fases de maniobra o sentido de giro invertido",
            "diagnostico": "Inversión de fases de maniobra (Marrón/Negro) o sentido de giro invertido.",
            "solucion": "1. En la App MySmartWindow / BlickDomi: Activar la opción 'Invertir Sentido de Giro'.\n2. O en regleta física: Intercambiar los cables de los bornes OUT1 (▲) y OUT2 (▼).",
            "confianza": 98.0,
            "fuente": "regla_experta"
        })
    if "oscilo" in sintoma_norm:
        candidatos.append({
            "titulo": "Incompatibilidad sensor en oscilobatiente",
            "diagnostico": "Incompatibilidad de sensor gestual en apertura oscilobatiente.",
            "solucion": "El sensor gestual queda desalineado al abrir en oscilobatiente por seguridad. Informar al usuario de que debe maniobrarse desde la app o con ventana en posición cerrada.",
            "confianza": 95.0,
            "fuente": "regla_experta"
        })
    if "candado" in sintoma_norm or "bloquead" in sintoma_norm:
        candidatos.append({
            "titulo": "Modo Candado infantil activo",
            "diagnostico": "Modo Candado / Bloqueo de Seguridad infantil activo en la App.",
            "solucion": "Abrir la App y desactivar el 'Modo Candado' en los ajustes de la ventana afectada.",
            "confianza": 94.0,
            "fuente": "regla_experta"
        })
    if "movistar" in sintoma_norm or "digi" in sintoma_norm or "router" in sintoma_norm or "cambio contrasena" in sintoma_norm:
        candidatos.append({
            "titulo": "Desconfiguración Wi-Fi o banda 5GHz",
            "diagnostico": "Desconfiguración de red Wi-Fi o red 5GHz exclusiva tras cambio de router.",
            "solucion": "1. Separar las bandas 2.4 GHz y 5 GHz en el router del cliente.\n2. Poner el módulo en modo emparejamiento (parpadeo rápido) y vincular introduciendo la nueva clave Wi-Fi 2.4 GHz.",
            "confianza": 92.0,
            "fuente": "regla_experta"
        })
    if "parpadea" in sintoma_norm and ("pulsador" in sintoma_norm or "cortad" in sintoma_norm):
        candidatos.append({
            "titulo": "Fallo bus pulsador o cable pellizcado",
            "diagnostico": "Fallo de comunicación en el bus de pulsador o cable cortado/aplastado.",
            "solucion": "Revisar la continuidad del cable plano que une el pulsador C-Pulsar con el módulo Connect. Si el cable está pellizcado por las lamas, sustituirlo.",
            "confianza": 90.0,
            "fuente": "regla_experta"
        })

    # B) Feedback Loop: Casos reales resueltos en la Base de Datos
    if db:
        try:
            from . import database
            tickets_bd = database.buscar_tickets_resueltos_similares(db, sintoma_norm, dispositivo=dispositivo, limite=3)
            for t_sim in tickets_bd:
                conf_bd = min(96.0, round(75.0 + (float(t_sim.get("relevancia", 0.1)) * 20.0), 1))
                candidatos.append({
                    "titulo": f"Ticket Resuelto #{t_sim.get('numero_ticket', '')} ({t_sim.get('dispositivo', 'SAT')})",
                    "diagnostico": t_sim.get("diagnostico") or f"Caso resuelto: {t_sim.get('sintoma', '')}",
                    "solucion": t_sim.get("solucion") or "Solución aplicada en soporte técnico.",
                    "confianza": conf_bd,
                    "fuente": "tickets_bd",
                    "ticket_id": t_sim.get("ticket_id"),
                    "numero_ticket": t_sim.get("numero_ticket")
                })
        except Exception as e:
            logger.warning(f"Error consultando tickets resueltos similares: {e}")

    # C) Matriz de problemas-soluciones (Excel)
    for score, prob in mejores_problemas[:4]:
        candidatos.append({
            "titulo": prob.get("problema", "Problema detectado"),
            "diagnostico": f"Causa detectada: {prob.get('problema', '')}",
            "solucion": prob.get("solucion", ""),
            "confianza": min(95.0, round(score * 100, 1)),
            "fuente": "matriz_problemas"
        })

    # D) Historial de Incidencias (Excel)
    caso_historico_top = mejores_historicos[0][1] if mejores_historicos else None
    for score, inc in mejores_historicos[:3]:
        candidatos.append({
            "titulo": inc.get("problema", "Incidencia histórica"),
            "diagnostico": f"Incidencia tipo '{inc.get('problema', '')}': {inc.get('comentario', '')}",
            "solucion": f"Acción correctiva aplicada en SAT: {inc.get('accion_correctiva', '')}. {inc.get('comentario', '')}".strip(),
            "confianza": min(93.0, round(score * 100, 1)),
            "fuente": "historico_excel"
        })

    # Ordenar y seleccionar Top 3 diagnósticos únicos
    candidatos.sort(key=lambda x: x["confianza"], reverse=True)
    top_diagnosticos = []
    seen_diag = set()
    for c in candidatos:
        diag_key = c["diagnostico"].strip()[:40].lower()
        if diag_key not in seen_diag:
            seen_diag.add(diag_key)
            top_diagnosticos.append(c)
            if len(top_diagnosticos) >= 3:
                break

    # Fallback si no hay coincidencias
    if not top_diagnosticos:
        fallback = {
            "titulo": "Revisión general 230V y conectividad",
            "diagnostico": "Revisión general de conexionado 230V, alimentación y estado del LED de red.",
            "solucion": "Verificar presencia de 230V en bornes L/N, realizar Reset de fábrica (pulsación 10s) y re-vincular cerca del router.",
            "confianza": 45.0,
            "fuente": "general"
        }
        top_diagnosticos = [fallback]

    diagnostico_sugerido = top_diagnosticos[0]["diagnostico"]
    solucion_sugerida = top_diagnosticos[0]["solucion"]
    confianza_score = top_diagnosticos[0]["confianza"]

    # 4. Buscar Manual PDF relacionado en la BD (si se pasó sesión de BD)
    manual_recomendado = None
    if db:
        try:
            # Query Full-text search en páginas de manuales
            palabras_query = [w for w in sintoma_norm.split() if w not in STOP_WORDS][:5]
            if palabras_query:
                terminos_sql = " | ".join(palabras_query)
                query_manual = text("""
                    SELECT p.id, p.numero_pagina, p.texto, m.id as manual_id, m.nombre_original, m.nombre_archivo, m.dispositivo
                    FROM paginas p
                    JOIN manuales m ON p.manual_id = m.id
                    WHERE to_tsvector('spanish_unaccent', p.texto) @@ to_tsquery('spanish_unaccent', :q)
                    ORDER BY ts_rank(to_tsvector('spanish_unaccent', p.texto), to_tsquery('spanish_unaccent', :q)) DESC
                    LIMIT 1;
                """)
                res_man = db.execute(query_manual, {"q": terminos_sql}).fetchone()
                if res_man:
                    snippet = res_man.texto[:220] + "..." if len(res_man.texto) > 220 else res_man.texto
                    manual_recomendado = {
                        "manual_id": res_man.manual_id,
                        "nombre": res_man.nombre_original,
                        "archivo": res_man.nombre_archivo,
                        "pagina": res_man.numero_pagina,
                        "dispositivo": res_man.dispositivo or dispositivo,
                        "snippet": snippet
                    }
        except Exception as e:
            logger.error(f"Error buscando manual para auto-resolución: {e}")

    # Fallback de manual si no se encontró en BD
    if not manual_recomendado:
        manual_recomendado = {
            "manual_id": 1,
            "nombre": "Guía Rápida de Instalación y SAT",
            "archivo": "C-PULSAR_Documentacion_MySmartWindow.pdf",
            "pagina": 1,
            "dispositivo": dispositivo or "Connect-1",
            "snippet": "Instrucciones paso a paso para cableado 230V, modo emparejamiento Wi-Fi y configuración de finales de carrera."
        }

    # 5. Buscar Video Tutorial en la BD
    video_recomendado = None
    if db:
        try:
            terminos_video = " | ".join([w for w in sintoma_norm.split() if w not in STOP_WORDS][:4])
            if terminos_video:
                query_video = text("""
                    SELECT id, video_id, titulo, url, miniatura_url, transcripcion_texto
                    FROM videos
                    WHERE to_tsvector('spanish_unaccent', titulo || ' ' || transcripcion_texto) @@ to_tsquery('spanish_unaccent', :q)
                    LIMIT 1;
                """)
                res_vid = db.execute(query_video, {"q": terminos_video}).fetchone()
                if res_vid:
                    video_recomendado = {
                        "id": res_vid.id,
                        "video_id": res_vid.video_id,
                        "titulo": res_vid.titulo,
                        "url": res_vid.url,
                        "miniatura_url": res_vid.miniatura_url or f"https://img.youtube.com/vi/{res_vid.video_id}/hqdefault.jpg"
                    }
        except Exception as e:
            logger.error(f"Error buscando video para auto-resolución: {e}")

    if not video_recomendado:
        video_recomendado = {
            "id": 1,
            "video_id": "j7V8uHqqbq0",
            "titulo": "Tutorial de Vinculación y Reset de Dispositivos MySmartWindow",
            "url": "https://www.youtube.com/watch?v=j7V8uHqqbq0",
            "miniatura_url": "https://img.youtube.com/vi/j7V8uHqqbq0/hqdefault.jpg"
        }

    # 6. Generar Plantilla Formateada para WhatsApp / Correo
    disp_nombre = dispositivo if dispositivo else "persiana motorizada"
    plantilla_whatsapp = (
        f"🛠️ *ASISTENCIA TÉCNICA SAT - SOPORTE DE INSTALACIÓN*\n\n"
        f"Hola, respecto a la incidencia con tu equipo *{disp_nombre}*:\n\n"
        f"🔍 *Diagnóstico*: {diagnostico_sugerido}\n\n"
        f"✅ *Solución paso a paso*:\n{solucion_sugerida}\n\n"
        f"📄 *Manual oficial*: Consulta la pág. {manual_recomendado['pagina']} de {manual_recomendado['nombre']}.\n"
        f"🎥 *Video Tutorial explicativo*: {video_recomendado['url']}\n\n"
        f"Si tras estos pasos persiste la incidencia, indícanoslo para gestionar el seguimiento. ¡Un saludo!"
    )

    return {
        "exito": True,
        "confianza": confianza_score,
        "diagnostico_sugerido": diagnostico_sugerido,
        "solucion_sugerida": solucion_sugerida,
        "top_diagnosticos": top_diagnosticos,
        "caso_historico_similar": {
            "nombre": caso_historico_top["nombre"] if caso_historico_top else "",
            "distribuidor": caso_historico_top["distribuidor"] if caso_historico_top else distribuidor,
            "dispositivo": caso_historico_top["dispositivo"] if caso_historico_top else dispositivo,
            "problema": caso_historico_top["problema"] if caso_historico_top else "",
            "comentario": caso_historico_top["comentario"] if caso_historico_top else "",
            "accion_correctiva": caso_historico_top["accion_correctiva"] if caso_historico_top else ""
        } if caso_historico_top else None,
        "manual_recomendado": manual_recomendado,
        "video_recomendado": video_recomendado,
        "plantilla_whatsapp": plantilla_whatsapp
    }


def evaluar_cuestionario_asistencia(datos: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Evalúa el Cuestionario Inicial de Soporte IoT (12 módulos) y genera:
    - Diagnóstico experto categorizado
    - Tags de soluciones técnicas
    - Plan de acción paso a paso (omitiendo acciones ya realizadas)
    - Manuales PDF y esquemas exactos recomendados
    - Plantilla lista para WhatsApp
    - Datos pre-rellenados para ticket SAT
    """
    partner = datos.get("partner", "IoT Fenster / MySmartWindow")
    dispositivo = datos.get("dispositivo", "Connect-1")
    modelo_comercial = datos.get("modelo_comercial", "")
    num_afectados = datos.get("num_dispositivos_afectados", "1")
    area = datos.get("area_incidencia", "No identificado")
    
    estado_vinculado = datos.get("estado_vinculado", "Sí")
    estado_app = datos.get("estado_app", "Sí")
    control_fisico = datos.get("estado_control_fisico", "Sí")
    control_app = datos.get("estado_control_app", "Sí")
    
    sintomas = datos.get("sintomas_observados", [])
    if isinstance(sintomas, str):
        sintomas = [s.strip() for s in sintomas.split(",") if s.strip()]
        
    wifi = datos.get("wifi_info", {})
    app_info = datos.get("app_info", {})
    alcance = datos.get("alcance_fisico", {})
    especifica = datos.get("info_especifica", {})
    momento = datos.get("momento_fallo", "Durante uso normal")
    reproducibilidad = datos.get("reproducibilidad", "Siempre")
    detonante = datos.get("accion_detonante", "")
    descripcion = datos.get("descripcion_detallada", "")
    acciones_hechas = datos.get("acciones_realizadas", [])
    if isinstance(acciones_hechas, str):
        acciones_hechas = [a.strip() for a in acciones_hechas.split(",") if a.strip()]

    # 1. Normalización de Equivalencias de Marca
    equivalencia_partner = ""
    dispositivo_efectivo = dispositivo
    if "VBH" in partner or "GreenTeQ" in partner:
        if dispositivo == "Connect-1":
            equivalencia_partner = "GreenTeQ Wave 1 (Equivalente a Connect-1)"
        elif dispositivo == "Connect-2":
            equivalencia_partner = "GreenTeQ Wave 2 (Equivalente a Connect-2)"
    elif "Procomsa" in partner or "ICON" in partner:
        if dispositivo == "Connect-1":
            equivalencia_partner = "ICON 1 (Equivalente a Connect-1)"
        elif dispositivo == "Connect-2":
            equivalencia_partner = "ICON 2 (Equivalente a Connect-2)"
    elif "Kömmerling" in partner or "Konect" in partner:
        equivalencia_partner = "Konect Shutter / Box (Kömmerling Partner Series)"

    # 2. Inferencia de Matriz de Estados (Físico vs App)
    matriz_estado = ""
    tags = set()
    diagnostico_titulo = ""
    causa_raiz = ""
    pasos_recomendados = []
    nivel_gravedad = "media"
    confianza = 85.0

    sintomas_str = " ".join(sintomas).lower() + " " + descripcion.lower()

    # Evaluación de Inversión de Giros
    if any(k in sintomas_str for k in ["bajar sube", "sube cuando bajo", "al reves", "invertid", "giro"]):
        diagnostico_titulo = "Inversión de Fases de Maniobra / Sentido de Giro Motor"
        causa_raiz = "Las salidas de motor OUT1 (Subida) y OUT2 (Bajada) están intercambiadas o el motor está instalado en el lado opuesto del tambor."
        tags.update(["#InvertirFasesMotor", "#AppSwapGiro", "#VerificarSentidoGiro"])
        pasos_recomendados = [
            "En la App MySmartWindow/BlickDomi: Entrar en Ajustes de Ventana > 'Invertir Sentido de Giro' y activar la casilla.",
            "Si se prefiere por cableado: Desconectar magnetotérmico 230V e intercambiar los cables Marrón y Negro en las salidas del módulo.",
            "Comprobar que al pulsar ▲ la persiana sube y al pulsar ▼ la persiana baja.",
            "Lanzar una calibración completa desde la App."
        ]
        confianza = 96.0

    # Evaluación de Control Físico KO + App KO (Alimentación / Final de carrera)
    elif control_fisico == "No" and control_app == "No":
        diagnostico_titulo = "Fallo General de Alimentación 230V o Bloqueo Térmico de Motor"
        causa_raiz = "El dispositivo no recibe tensión eléctrica de línea (230V L/N) o el protector térmico interno del motor ha saltado tras uso continuado."
        tags.update(["#Revisar230V", "#ProteccionTermica", "#ComprobarNeutro", "#Magnetotermico"])
        nivel_gravedad = "alta"
        pasos_recomendados = [
            "Verificar con multímetro que llegan 230V AC entre los bornes L_IN (Fase) y N_IN (Neutro).",
            "Comprobar si el LED de estado del módulo está completamente apagado (sin alimentación).",
            "Si el motor estuvo funcionando intensamente, esperar 15-20 minutos a que se enfríe la protección térmica.",
            "Revisar el apriete de los bornes de tornillo / clemas WAGO en la caja de mecanismo o cajón."
        ]
        confianza = 92.0

    # Evaluación de Control Físico OK + App KO (Conectividad / Wi-Fi / Cloud)
    elif control_fisico == "Sí" and (control_app == "No" or estado_app == "Aparece pero offline"):
        diagnostico_titulo = "Incidencia de Conectividad Wi-Fi / Aislamiento de Red Local"
        causa_raiz = "El módulo opera correctamente a nivel electromecánico pero ha perdido el enlace con el router Wi-Fi o con los servidores Cloud MQTT (puerto 8883)."
        tags.update(["#SepararSSID24GHz", "#DesactivarWPA3Only", "#VerificarCanalWiFi", "#AislamientoAP"])
        pasos_recomendados = [
            "Comprobar en el router que la red 2.4 GHz está activa y tiene un SSID diferenciado de la red 5 GHz.",
            "Verificar que la seguridad del Wi-Fi es WPA2-PSK (AES) o WPA2/WPA3 Mixto (evitar WPA3-Enterprise o WPA3-Only).",
            "Comprobar que el router o repetidor no tiene activo el 'Aislamiento de Clientes' (AP Isolation).",
            "Si el módulo está dentro del cajón de persiana metálico, reubicarlo junto a la tapa de PVC para evitar efecto Jaula de Faraday."
        ]
        confianza = 94.0

    # Evaluación de Vinculación: 0 dispositivos o no encuentra dispositivo
    elif any(k in sintomas_str for k in ["no descubre", "0 dispositivos", "cero dispositivos", "menos dispositivos", "vincula pero no aparece"]):
        diagnostico_titulo = "Fallo de Descubrimiento BLE / Emparejamiento Wi-Fi 2.4 GHz"
        causa_raiz = "El smartphone está conectado a 5 GHz durante la vinculación, no tiene permisos de Ubicación/Bluetooth activados, o el router fuerza Band Steering."
        tags.update(["#PermisosBluetooth", "#Forzar24GHz", "#ModoEmparejamiento", "#Reset10Segundos"])
        pasos_recomendados = [
            "En el teléfono: Activar Bluetooth, Ubicación (GPS) y permisos de 'Dispositivos Cercanos' en la App.",
            "Conectar el móvil expresamente a la red Wi-Fi 2.4 GHz del domicilio (desactivar datos móviles temporalmente).",
            "Poner el dispositivo en modo emparejamiento pulsando 5 segundos el botón de configuración hasta que el LED parpadee rápidamente.",
            "Si persiste, realizar un Reset de fábrica pulsando 10 segundos continuados y reiniciar la vinculación."
        ]
        confianza = 95.0

    # Evaluación de Calibración
    elif any(k in sintomas_str for k in ["calibracion", "no calibra", "parada a medias", "no memoriza"]):
        diagnostico_titulo = "Fallo de Detección de Finales de Carrera en Calibración"
        causa_raiz = "Los finales de carrera del motor tubular no están correctamente regulados o el motor se detiene por rozamiento mecánico antes de alcanzar el tope."
        tags.update(["#AjustarFinalesCarrera", "#RecorridoMecanico", "#CalibracionApp"])
        pasos_recomendados = [
            "Ajustar los tornillos de finales de carrera superior e inferior del motor con la varilla de regulación.",
            "Asegurarse de que la persiana puede subir y bajar libremente por las guías sin enganches ni deformación de lamas.",
            "Iniciar la calibración desde la App con la persiana en posición intermedia y no interrumpir el ciclo.",
            "Verificar que el tiempo de maniobra supera los 8 segundos para que el sensor de consumo detecte el corte."
        ]
        confianza = 90.0

    # Evaluación de Sensorización Connect-2 / Oscilobatiente
    elif "Connect-2" in dispositivo and any(k in sintomas_str for k in ["oscilo", "sensor", "temperatura", "co2", "humedad", "voc"]):
        diagnostico_titulo = "Desalineación de Sensores en Hoja Oscilobatiente o Precalentamiento Ambiental"
        causa_raiz = "El sensor de apertura/gestual se desalinea físicamente con la hoja en posición oscilobatiente, o los sensores de CO2/VOC requieren tiempo de estabilización."
        tags.update(["#SensorOscilobatiente", "#AlineacionIman", "#PrecalentamientoCO2"])
        pasos_recomendados = [
            "Verificar que el imán sensor del marco y la hoja mantienen una distancia inferior a 8 mm en posición cerrada.",
            "Recordar que en posición oscilobatiente el sensor gestual se desactiva por seguridad estructural.",
            "Para lecturas de CO2 y VOC (calidad de aire), permitir 24-48h de conexión continua para la calibración del sensor térmico."
        ]
        confianza = 89.0

    # Evaluación de C-Wall
    elif "C-Wall" in dispositivo:
        diagnostico_titulo = "Configuración de Mecanismo de Pared C-Wall (Biestable / Monostable)"
        causa_raiz = "El modo de pulsador configurado en la App no coincide con el tipo de mecanismo físico montado (pulsador de persiana con retorno vs interruptor con enclavamiento)."
        tags.update(["#ConfiguracionPulsador", "#Caja60mm", "#TipoMecanismo"])
        pasos_recomendados = [
            "En la App: Ajustes de C-Wall > 'Tipo de Mecanismo' > Seleccionar 'Pulsador (Monostable)' si tiene muelle de retorno.",
            "Comprobar que en la caja de 60 mm los cables no quedan presionando el botón de emparejamiento posterior.",
            "Verificar que la tensión de fase llega al borne común L del C-Wall."
        ]
        confianza = 88.0

    # Evaluación por Entorno Wi-Fi / Cobertura
    elif wifi.get("rssi") in ["Bajo", "<-75 dBm"] or "Metal" in alcance.get("obstaculos", []):
        diagnostico_titulo = "Atenuación Severa de Señal RF (Efecto Jaula de Faraday o Distancia Excesiva)"
        causa_raiz = "El nivel de señal RSSI es inferior a -75 dBm debido a la distancia con el router o al blindaje metálico del cajón/carpintería."
        tags.update(["#AntenaExterior", "#RepetidorMesh", "#EfectoFaraday", "#MejorarCobertura"])
        pasos_recomendados = [
            "Instalar el módulo en la parte plástica (tapa de PVC de registro) del cajón y nunca embutido dentro del tubo metálico.",
            "Si la vivienda tiene varias plantas o muros gruesos, instalar un nodo Wi-Fi Mesh o repetidor a menos de 8 metros.",
            "Comprobar la atenuación midiendo con la App el RSSI en tiempo real (óptimo entre -40 y -65 dBm)."
        ]
        confianza = 91.0

    else:
        # Fallback genérico inteligente
        diagnostico_titulo = f"Incidencia Operativa en {dispositivo_efectivo} ({area})"
        causa_raiz = "Comportamiento anómalo en la lógica de control o desincronización de parámetros."
        tags.update(["#RevisionCableado", "#Reset10Segundos", "#ActualizacionOTA"])
        pasos_recomendados = [
            "Efectuar un reinicio eléctrico desconectando el automático general 10 segundos.",
            "Comprobar si hay alguna actualización de Firmware OTA pendiente en la App.",
            "Verificar el estado del cableado de maniobra y finales de carrera.",
            "Si el síntoma persiste, tramitar ticket de soporte con registro de logs."
        ]
        confianza = 75.0

    # 3. Filtrar los pasos recomendados excluyendo acciones ya realizadas
    pasos_filtrados = []
    acciones_hechas_norm = [normalizar_texto(a) for a in acciones_hechas]
    
    for paso in pasos_recomendados:
        paso_norm = normalizar_texto(paso)
        # Si el usuario ya hizo "reinicio dispositivo" y el paso habla de "reinicio electrico", lo marcamos como ya probado
        ya_probado = False
        if any(h in paso_norm for h in ["reinicio", "reiniciar"]) and any("reinicio" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["reset", "fabrica"]) and any("reset" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["separar", "2.4 ghz", "5 ghz"]) and any("2.4" in ah or "separar" in ah for ah in acciones_hechas_norm):
            ya_probado = True
            
        pasos_filtrados.append({
            "paso": paso,
            "ya_probado": ya_probado
        })

    # 4. Obtener Recursos Oficiales & Páginas de Manuales
    manual_encontrado = None
    if db:
        try:
            termino_busqueda = f"{dispositivo} {diagnostico_titulo}"
            palabras = [w for w in normalizar_texto(termino_busqueda).split() if w not in STOP_WORDS][:4]
            if palabras:
                terminos_sql = " | ".join(palabras)
                query_manual = text("""
                    SELECT p.id, p.numero_pagina, p.texto, m.id as manual_id, m.nombre_original, m.nombre_archivo, m.dispositivo
                    FROM paginas p
                    JOIN manuales m ON p.manual_id = m.id
                    WHERE to_tsvector('spanish_unaccent', p.texto) @@ to_tsquery('spanish_unaccent', :q)
                    ORDER BY ts_rank(to_tsvector('spanish_unaccent', p.texto), to_tsquery('spanish_unaccent', :q)) DESC
                    LIMIT 1;
                """)
                res_man = db.execute(query_manual, {"q": terminos_sql}).fetchone()
                if res_man:
                    manual_encontrado = {
                        "manual_id": res_man.manual_id,
                        "nombre": res_man.nombre_original,
                        "archivo": res_man.nombre_archivo,
                        "pagina": res_man.numero_pagina,
                        "snippet": res_man.texto[:200] + "..."
                    }
        except Exception as e:
            logger.warning(f"Error consultando BD de manuales en cuestionario: {e}")

    if not manual_encontrado:
        manual_encontrado = {
            "manual_id": 1,
            "nombre": f"Manual Técnico Oficial {dispositivo}",
            "archivo": "C-PULSAR_Documentacion_MySmartWindow.pdf" if "Pulsar" in dispositivo else "CONNECT-1_Manual_Usuario.pdf",
            "pagina": 3,
            "snippet": f"Instrucciones de cableado, compatibilidad de red 2.4 GHz y ajustes de {dispositivo}."
        }

    # 5. Generar Plantilla WhatsApp
    lista_pasos_txt = "\n".join([f"{idx+1}. {p['paso']}" for idx, p in enumerate(pasos_filtrados) if not p['ya_probado']])
    if not lista_pasos_txt:
        lista_pasos_txt = "\n".join([f"{idx+1}. {p['paso']}" for idx, p in enumerate(pasos_filtrados)])

    whatsapp_msg = (
        f"🛠️ *SOPORTE TÉCNICO IOT - ASISTENCIA EN OBRA*\n\n"
        f"📋 *Equipo*: {dispositivo_efectivo} ({partner})\n"
        f"🔍 *Diagnóstico*: {diagnostico_titulo}\n"
        f"💡 *Causa identificada*: {causa_raiz}\n\n"
        f"👉 *Pasos de resolución recomendados*:\n{lista_pasos_txt}\n\n"
        f"📄 *Manual de referencia*: {manual_encontrado['nombre']} (Pág. {manual_encontrado['pagina']})\n\n"
        f"Por favor, realiza estas verificaciones y confírmanos el resultado. ¡Gracias!"
    )

    # 6. Prefill para Ticket SAT
    ticket_prefill = {
        "dispositivo": dispositivo,
        "distribuidor": partner,
        "sintoma": f"[{area}] " + (", ".join(sintomas) if sintomas else descripcion[:120]),
        "diagnostico": f"{diagnostico_titulo}. Causa: {causa_raiz}",
        "solucion": "\n".join([p['paso'] for p in pasos_filtrados if not p['ya_probado']]),
        "estado": "en_espera",
        "prioridad": "urgente" if momento == "Durante instalación" or num_afectados == "Todos los de la vivienda/instalación" else "normal"
    }

    # 7. Construir Top Diagnósticos sugeridos (Feedback Loop)
    top_diagnosticos_cuestionario = [{
        "titulo": diagnostico_titulo,
        "diagnostico": diagnostico_titulo,
        "solucion": pasos_filtrados[0]["paso"] if pasos_filtrados else causa_raiz,
        "confianza": confianza,
        "fuente": "asistencia_guiada"
    }]

    if db:
        try:
            from . import database
            tickets_sim = database.buscar_tickets_resueltos_similares(
                db,
                sintoma_norm=normalizar_texto(f"{diagnostico_titulo} {sintomas_str}"),
                dispositivo=dispositivo,
                limite=2
            )
            for t_s in tickets_sim:
                top_diagnosticos_cuestionario.append({
                    "titulo": f"Ticket Resuelto #{t_s.get('numero_ticket', '')}",
                    "diagnostico": t_s.get("diagnostico") or t_s.get("sintoma", ""),
                    "solucion": t_s.get("solucion") or "",
                    "confianza": min(93.0, round(70.0 + (float(t_s.get("relevancia", 0.1)) * 20.0), 1)),
                    "fuente": "tickets_bd"
                })
        except Exception:
            pass

    return {
        "exito": True,
        "confianza": confianza,
        "diagnostico_titulo": diagnostico_titulo,
        "causa_raiz": causa_raiz,
        "nivel_gravedad": nivel_gravedad,
        "equivalencia_partner": equivalencia_partner,
        "tags_solucion": list(tags),
        "pasos_accion": pasos_filtrados,
        "manual_recomendado": manual_encontrado,
        "whatsapp_template": whatsapp_msg,
        "ticket_prefill": ticket_prefill,
        "top_diagnosticos": top_diagnosticos_cuestionario
    }


# Alias para compatibilidad de rutas
autoresolver_caso_sat = autoresolver_ticket_sat

