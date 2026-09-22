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
PATH_INCIDENCIAS = os.path.join(BASE_DIR, "data", "sat", "Incidencias.xlsx")
PATH_PROBLEMAS_SOL = os.path.join(BASE_DIR, "data", "sat", "Problemas- soluciones.xlsx")

# Caché en memoria para evitar re-parsear constantemente
_CACHE_INCIDENCIAS: Optional[List[Dict[str, Any]]] = None
_CACHE_PROBLEMAS_SOL: Optional[List[Dict[str, Any]]] = None

STOP_WORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "del", "un", "una", "unos",
    "unas", "por", "con", "no", "se", "su", "para", "al", "o", "es", "que", "lo",
    "si", "sus", "le", "les", "me"
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


# ---------------------------------------------------------------------------
# Motor de diagnóstico por puntuación
# ---------------------------------------------------------------------------
# Esto era una cadena de trece if/elif y ganaba la primera rama que enganchaba.
# La de Band Steering se cumplía con `tipo_red == "Dual 2,4/5 GHz"` y
# `ssid_separados == "No"`, que son EXACTAMENTE las dos primeras <option> del
# formulario: las que quedan puestas si el técnico no toca el bloque Wi-Fi. El
# resultado era que cualquier avería —una alarma sin batería incluida— salía
# como Band Steering con un 95 % de confianza, y las ramas 9 a 13 (calibración,
# sensores Connect-2, C-Wall, WAlarm, cobertura) eran inalcanzables en la
# práctica: solo se llegaba a ellas cambiando ese desplegable.
#
# Ahora cada regla suma el peso de las señales que encuentra y gana la de mayor
# puntuación. Lo que arregla el sesgo no es el orden, es el peso: una condición
# que puede venir puesta por defecto vale DÉBIL y no llega sola al umbral, así
# que no puede decidir por sí misma. Si nadie pasa el umbral se dice que no hay
# diagnóstico concluyente, en vez de afirmar el primero de la lista.
SENAL_FUERTE = 3.0    # evidencia explícita e inequívoca del fallo
SENAL_MEDIA = 2.0     # respuesta explícita distinta del valor por defecto
SENAL_DEBIL = 0.8     # condición de entorno que puede venir por defecto
SENAL_FAMILIA = 1.2   # orientación por familia de producto, nunca un diagnóstico

# Por debajo de esto no se afirma nada. Una señal DÉBIL sola (0.8) no llega, ni
# dos sumadas (1.6): hace falta al menos una respuesta explícita del técnico.
UMBRAL_DECISION = 2.0


def _tiene(texto: str, claves: List[str]) -> bool:
    return any(k in texto for k in claves)


def _reglas_diagnostico() -> List[Dict[str, Any]]:
    """Catálogo de reglas. `senales` devuelve [(peso, motivo)] de lo que encaja.

    El contenido técnico —título, causa y pasos— es el mismo que había en la
    cadena de if/elif: lo que cambia es cómo se elige, no lo que se sabe.
    """
    return [
        {
            "id": "reles_sin_motor",
            "titulo": "Relés Electrónicos Conmutan pero Motor Tubular no Responde",
            "causa": "El módulo Connect-1 maniobra correctamente pero la tensión no llega al bobinado del motor. Causas probables: neutro común (cable azul) suelto o desconectado, final de carrera superior/inferior completamente cerrado, corte térmico del motor tras esfuerzo o condensador averiado.",
            "tags": ["#NeutroComunAzul", "#VerificarFasesSalida", "#FinalesCarreraMotor", "#ProteccionTermica"],
            "gravedad": "alta",
            "techo": 97.0,
            "pasos": [
                "Comprobar con un multímetro que entre el Neutro (N) y OUT1/OUT2 se miden 230V AC al conmutar la subida o bajada.",
                "Verificar la conexión del cable Azul (Neutro del motor) en la regleta de bornes o clema WAGO.",
                "Girar los tornillos de final de carrera del motor 5-6 vueltas con la varilla reguladora para liberar posibles topes mecánicos forzados.",
                "Si el motor estuvo funcionando reiteradamente, dejar enfriar 20 minutos (disparo del protector bimetálico térmico).",
            ],
            "senales": lambda c: (
                [(SENAL_FUERTE, "Se oyen los relés pero el motor no responde (checklist de hardware)")]
                if c["dispositivo"] == "Connect-1" and c["hw_c1"].get("oyen_reles") and not c["hw_c1"].get("motor_responde") else []
            ) + (
                [(SENAL_FUERTE, "El técnico describe relés que conmutan sin movimiento")]
                if _tiene(c["sintomas"], ["reles pero no se mueve", "clic de rele pero no", "suena el rele pero no"]) else []
            ),
        },
        {
            "id": "inversion_giro",
            "titulo": "Inversión de Fases de Maniobra / Sentido de Giro Motor",
            "causa": "Los cables de maniobra están intercambiados en la salida del módulo, o el motor tiene el sentido de giro invertido de fábrica.",
            "tags": ["#SwapGiro", "#InvertirFases", "#CableadoManiobra"],
            "gravedad": "media",
            "techo": 96.0,
            "pasos": [
                "Pulsar el botón Swap Giro en la App para invertir el sentido por software, sin tocar el cableado.",
                "Si no hay Swap Giro disponible, intercambiar físicamente los bornes de subida y bajada en la salida del módulo.",
                "Recalibrar el recorrido después de invertir, porque los finales de carrera quedan cambiados.",
            ],
            "senales": lambda c: (
                [(SENAL_FUERTE, "El movimiento va al revés de lo que se ordena")]
                if _tiene(c["sintomas"], ["bajar sube", "sube cuando bajo", "al reves", "invertid"]) else []
            ) + (
                [(SENAL_MEDIA, "Se menciona el sentido de giro")]
                if "giro" in c["sintomas"] else []
            ),
        },
        {
            "id": "wpa3_wifi67",
            "titulo": "Incompatibilidad de Cifrado WPA3 o Trama Wi-Fi 6/7 en Red 2.4 GHz",
            "causa": "El módulo ESP solo admite WPA2-PSK sobre 802.11 b/g/n en 2,4 GHz. Un router con WPA3 obligatorio o tramas Wi-Fi 6/7 impide la asociación.",
            "tags": ["#WPA2Obligatorio", "#DesactivarWPA3", "#ModoCompatibilidad"],
            "gravedad": "alta",
            "techo": 95.0,
            "pasos": [
                "Entrar en la configuración del router y poner el cifrado en WPA2-PSK (AES), no en WPA2/WPA3 mixto.",
                "Desactivar el modo Wi-Fi 6 (802.11ax) en la banda de 2,4 GHz, dejándola en b/g/n.",
                "Reiniciar el router y repetir el emparejamiento del equipo.",
            ],
            "senales": lambda c: (
                [(SENAL_MEDIA, f"Cifrado declarado: {c['wifi_seg']}")] if "WPA3" in c["wifi_seg"] else []
            ) + (
                [(SENAL_MEDIA, f"Generación de red declarada: {c['wifi_gen']}")]
                if any(g in c["wifi_gen"] for g in ["Wi-Fi 6", "Wi-Fi 7"]) else []
            ) + (
                [(SENAL_FUERTE, "Se menciona WPA3 en la descripción")] if "wpa3" in c["sintomas"] else []
            ),
        },
        {
            "id": "incidencia_global",
            "titulo": "Incidencia General de Red Local, Router o Línea Eléctrica",
            "causa": "Fallan todos los equipos de la vivienda a la vez, o el fallo se repite en varios móviles: el problema no está en un dispositivo concreto sino en la infraestructura común.",
            "tags": ["#RevisarRouter", "#CorteElectrico", "#IncidenciaGlobal"],
            "gravedad": "alta",
            "techo": 94.0,
            "pasos": [
                "Comprobar que el router tiene conexión a internet y que no ha cambiado la contraseña del Wi-Fi.",
                "Verificar el diferencial y los automáticos del cuadro eléctrico de la vivienda.",
                "Reiniciar el router y esperar 5 minutos a que los equipos se reconecten solos.",
            ],
            "senales": lambda c: (
                [(SENAL_MEDIA, "Afecta a todos los equipos de la vivienda")]
                if "Todos los de la vivienda" in str(c["num_afectados"]) else []
            ) + (
                [(SENAL_MEDIA, "El fallo se reproduce en varios móviles")]
                if c["mas_de_un_movil"] in ["Sí (Común a la vivienda)", "Varios móviles con el mismo fallo"] else []
            ),
        },
        {
            "id": "disparidad_movil",
            "titulo": "Conflicto de Permisos Locales o Caché en Smartphone Específico",
            "causa": "El equipo responde bien, pero un móvil concreto no lo ve: permisos de red local, ubicación o Bluetooth denegados, o caché de la App corrupta.",
            "tags": ["#PermisosRedLocal", "#LimpiarCache", "#ReinstalarApp"],
            "gravedad": "baja",
            "techo": 93.0,
            "pasos": [
                "Revisar en los ajustes del móvil que la App tiene permisos de Ubicación, Red local y Bluetooth concedidos.",
                "Borrar la caché de la App y volver a entrar.",
                "Si persiste, desinstalar y reinstalar la App en ese móvil concreto.",
            ],
            "senales": lambda c: (
                [(SENAL_MEDIA, f"Comportamiento distinto según el móvil: {c['mas_de_un_movil']}")]
                if c["mas_de_un_movil"] in ["No (Solo en este móvil)", "En unos móviles funciona y en otros no"] else []
            ),
        },
        {
            "id": "alimentacion_termico",
            "titulo": "Fallo General de Alimentación 230V o Bloqueo Térmico de Motor",
            "causa": "No hay control ni físico ni por App: lo más probable es que no llegue tensión al módulo, o que el motor esté en corte térmico.",
            "tags": ["#Verificar230V", "#CorteTermico", "#RevisarAutomatico"],
            "gravedad": "alta",
            "techo": 92.0,
            "pasos": [
                "Medir con el multímetro que llegan 230V AC a la entrada de alimentación del módulo.",
                "Revisar el automático y el diferencial correspondientes a esa línea.",
                "Dejar enfriar el motor 20 minutos por si ha saltado el protector térmico y volver a probar.",
            ],
            "senales": lambda c: (
                [(SENAL_FUERTE, "No responde ni al pulsador físico ni a la App")]
                if c["control_fisico"] == "No" and c["control_app"] == "No" else []
            ),
        },
        {
            "id": "conectividad_wifi",
            "titulo": "Incidencia de Conectividad Wi-Fi / Aislamiento de Red Local",
            "causa": "El equipo funciona físicamente pero no responde por App: ha perdido la conexión con la nube o el router lo tiene aislado.",
            "tags": ["#AislamientoAP", "#ReconectarWiFi", "#RevisarCloud"],
            "gravedad": "media",
            "techo": 94.0,
            "pasos": [
                "Desactivar el Aislamiento de Punto de Acceso (AP Isolation) en el router.",
                "Comprobar que el equipo sigue asociado a la red de 2,4 GHz y no ha migrado a la de 5 GHz.",
                "Reiniciar eléctricamente el módulo 10 segundos y esperar a que vuelva a aparecer en línea.",
            ],
            "senales": lambda c: (
                [(SENAL_FUERTE, "Funciona el pulsador físico pero no la App")]
                if c["control_fisico"] == "Sí" and c["control_app"] == "No" else []
            ) + (
                [(SENAL_MEDIA, "El equipo aparece en la App pero fuera de línea")]
                if c["estado_app"] == "Aparece pero offline" else []
            ),
        },
        {
            "id": "band_steering",
            "titulo": "Band Steering Activo en Router / Frecuencia 5 GHz en Emparejamiento",
            "causa": "El router publica 2,4 y 5 GHz bajo el mismo SSID y empuja al móvil a la banda de 5 GHz durante el emparejamiento, que el módulo no puede ver.",
            "tags": ["#SepararSSID", "#BandSteering", "#Solo2GHzEnVinculacion"],
            "gravedad": "media",
            "techo": 95.0,
            "pasos": [
                "Separar temporalmente las bandas en el router creando un SSID distinto para 2,4 GHz.",
                "Conectar el móvil a la red de 2,4 GHz antes de iniciar el emparejamiento.",
                "Una vez vinculado el equipo, se pueden volver a unir las bandas.",
            ],
            # La condición de red vale DÉBIL a propósito: es justo la que venía
            # marcada por defecto en el formulario y la que se comía todos los
            # diagnósticos. Ahora acompaña, pero no decide sola.
            "senales": lambda c: (
                [(SENAL_FUERTE, "La App no descubre el equipo al vincular")]
                if _tiene(c["sintomas"], ["no descubre", "0 dispositivos", "cero dispositivos", "menos dispositivos", "vincula pero no aparece"]) else []
            ) + (
                [(SENAL_DEBIL, "La red publica ambas bandas con un único SSID (no confirmado por el técnico)")]
                if c["wifi"].get("tipo_red") in ["Red mixta 2.4/5 GHz (mismo SSID)", "Dual 2,4/5 GHz"] and c["wifi"].get("ssid_separados") == "No" else []
            ),
        },
        {
            "id": "calibracion",
            "titulo": "Fallo de Detección de Finales de Carrera en Calibración",
            "causa": "El módulo no consigue cerrar el ciclo de calibración porque no detecta los topes del recorrido, o el consumo del motor no cae lo suficiente al llegar al final.",
            "tags": ["#RecalibrarRecorrido", "#AjustarFinalesCarrera", "#UmbralMotor"],
            "gravedad": "media",
            "techo": 90.0,
            "pasos": [
                "Lanzar la calibración completa desde la App con la persiana libre de obstáculos.",
                "Ajustar los tornillos de final de carrera del motor para que los topes queden bien definidos.",
                "Si el motor es muy silencioso, subir el umbral de consumo para que detecte el tope.",
            ],
            "senales": lambda c: (
                [(SENAL_FUERTE, "Se describe un fallo de calibración o de recorrido")]
                if _tiene(c["sintomas"], ["calibracion", "no calibra", "parada a medias", "no memoriza"]) else []
            ) + (
                [(SENAL_FUERTE, "La calibración no termina (checklist de hardware)")]
                if c["hw_c1"] and c["hw_c1"].get("calib_termina") is False else []
            ),
        },
        {
            "id": "sensores_c2",
            "titulo": "Desalineación de Sensores en Hoja Oscilobatiente o Precalentamiento Ambiental",
            "causa": "Los sensores del Connect-2 están mal alineados con el imán de la hoja, o el sensor ambiental está leyendo el calor del propio módulo.",
            "tags": ["#AlinearIman", "#SeparacionSensor", "#DerivaTermica"],
            "gravedad": "baja",
            "techo": 89.0,
            "pasos": [
                "Comprobar que el imán y el sensor de apertura quedan a menos de 8 mm y enfrentados.",
                "Separar el módulo de fuentes de calor y de la electrónica de potencia antes de dar por mala la lectura.",
                "Dejar 30 minutos de estabilización antes de comparar la temperatura con un termómetro de referencia.",
            ],
            "senales": lambda c: (
                [(SENAL_MEDIA, "Checklist de sensores del Connect-2 marcada")]
                if "Connect-2" in c["dispositivo"] and any(c["hw_c2"].get(k) for k in ["oscilo", "apertura", "temp", "humedad", "co2", "voc", "impacto"]) else []
            ) + (
                [(SENAL_MEDIA, "Se describe un problema de sensor o de medida ambiental")]
                if _tiene(c["sintomas"], ["oscilo", "sensor", "temperatura", "co2", "humedad", "voc"]) else []
            ) + (
                [(SENAL_FAMILIA, "El equipo es un Connect-2")] if "Connect-2" in c["dispositivo"] else []
            ),
        },
        {
            "id": "cwall",
            "titulo": "Configuración de Mecanismo de Pared C-Wall (Biestable / Monostable)",
            "causa": "El mecanismo de pared está configurado en un modo que no corresponde al tipo de carga conectada.",
            "tags": ["#Biestable", "#Monostable", "#ConfiguracionCWall"],
            "gravedad": "baja",
            "techo": 88.0,
            "pasos": [
                "Verificar en la App si el mecanismo está declarado como persiana, luz o toldo.",
                "Comprobar el tipo de pulsación configurada (biestable o monostable) frente a lo que espera la carga.",
                "Recalibrar el pulsador capacitivo si responde de forma errática al tacto.",
            ],
            "senales": lambda c: (
                [(SENAL_FAMILIA, "El equipo es un C-Wall")] if "C-Wall" in c["dispositivo"] else []
            ) + (
                [(SENAL_MEDIA, "Se describe un problema del pulsador de pared")]
                if _tiene(c["sintomas"], ["pulsador", "capacitivo", "no responde al tacto", "biestable", "monostable"]) else []
            ),
        },
        {
            "id": "walarm",
            "titulo": "Verificación de Batería, Sabotaje y Contacto Magnético WAlarm",
            "causa": "La alarma no notifica porque la batería está agotada, el tamper está abierto o el contacto magnético no cierra.",
            "tags": ["#BateriaWAlarm", "#Tamper", "#ContactoMagnetico"],
            "gravedad": "media",
            "techo": 90.0,
            "pasos": [
                "Sustituir la pila y comprobar el nivel que reporta la App tras el cambio.",
                "Cerrar bien la carcasa para que el contacto de sabotaje (tamper) quede pulsado.",
                "Comprobar la separación entre imán y sensor con la hoja cerrada.",
            ],
            "senales": lambda c: (
                [(SENAL_FAMILIA, "El equipo es un WAlarm")] if "WAlarm" in c["dispositivo"] else []
            ) + (
                [(SENAL_MEDIA, "Se describen síntomas de alarma, batería o sabotaje")]
                if _tiene(c["sintomas"], ["alarma", "bateria", "pila", "sirena", "tamper", "sabotaje", "no suena"]) else []
            ),
        },
        {
            "id": "cobertura_rf",
            "titulo": "Atenuación Severa de Señal RF (Efecto Jaula de Faraday o Distancia Excesiva)",
            "causa": "El nivel de señal RSSI es inferior a -75 dBm debido a la distancia con el router o al blindaje metálico del cajón/carpintería.",
            "tags": ["#AntenaExterior", "#RepetidorMesh", "#EfectoFaraday", "#MejorarCobertura"],
            "gravedad": "media",
            "techo": 91.0,
            "pasos": [
                "Instalar el módulo en la parte plástica (tapa de PVC de registro) del cajón y nunca embutido dentro del tubo metálico.",
                "Si la vivienda tiene varias plantas o muros gruesos, instalar un nodo Wi-Fi Mesh o repetidor a menos de 8 metros.",
                "Comprobar la atenuación midiendo con la App el RSSI en tiempo real (óptimo entre -40 y -65 dBm).",
            ],
            "senales": lambda c: (
                [(SENAL_MEDIA, f"Cobertura declarada: {c['wifi'].get('rssi')}")]
                if c["wifi"].get("rssi") in ["Bajo", "<-75 dBm", "Bajo (-65 a -75 dBm)", "Muy débil / crítico (< -75 dBm)"] else []
            ) + (
                [(SENAL_MEDIA, "Obstáculos metálicos declarados en la instalación")]
                if "Metal" in str(c["alcance"].get("obstaculos", [])) else []
            ) + (
                [(SENAL_DEBIL, "Se menciona cobertura o alcance en la descripción")]
                if _tiene(c["sintomas"], ["cobertura", "senal debil", "señal debil", "lejos del router", "faraday"]) else []
            ),
        },
    ]


def puntuar_reglas(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Puntúa todas las reglas contra el contexto y las ordena de más a menos.

    Devuelve la lista entera, incluidas las de puntuación 0: quien llama decide
    si hay diagnóstico mirando el umbral, y las siguientes sirven de
    alternativas para que el técnico vea qué más se ha considerado y por qué se
    ha descartado.
    """
    puntuadas = []
    for regla in _reglas_diagnostico():
        try:
            senales = regla["senales"](ctx) or []
        except Exception as e:  # una regla rota no puede tumbar el triaje entero
            logger.warning(f"La regla de diagnóstico '{regla.get('id')}' falló al evaluarse: {e}")
            senales = []
        puntuacion = sum(peso for peso, _ in senales)
        puntuadas.append({
            "id": regla["id"],
            "titulo": regla["titulo"],
            "causa": regla["causa"],
            "tags": regla["tags"],
            "pasos": regla["pasos"],
            "gravedad": regla["gravedad"],
            "techo": regla["techo"],
            "puntuacion": round(puntuacion, 2),
            "motivos": [m for _, m in senales],
        })
    puntuadas.sort(key=lambda r: r["puntuacion"], reverse=True)
    return puntuadas


# `calcular_similitud` ya suma 0,35 solo por coincidir el dispositivo. Si el
# corte estuviera por debajo de eso, cualquier fila del mismo modelo entraría
# como "caso parecido" sin parecerse en nada —que es lo que pasaba: salían los
# mismos tres casos para consultas completamente distintas—. Pidiendo 0,45 hay
# que aportar además coincidencia real de texto.
UMBRAL_CASO_SIMILAR = 0.45


def buscar_casos_similares(texto_consulta: str, dispositivo: str, limite: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """Casos reales parecidos, sacados de los dos Excel de la base SAT.

    Estos ficheros se parseaban bien y no los leía nadie:
    `cargar_base_conocimiento_sat()` no se llamaba desde ningún punto del
    proyecto, así que las 119 incidencias históricas y las 10 parejas de
    problema-solución eran código muerto. Aquí se usan para acompañar al
    diagnóstico con precedentes, no para elegirlo: quien decide sigue siendo el
    técnico, y por eso se devuelve la similitud de cada caso.
    """
    incidencias, problemas = cargar_base_conocimiento_sat()

    hist = []
    for inc in incidencias:
        score = calcular_similitud(texto_consulta, inc.get("texto_norm", ""), dispositivo, inc.get("dispositivo", ""))
        if score > UMBRAL_CASO_SIMILAR:
            hist.append({
                "problema": inc.get("problema", ""),
                "dispositivo": inc.get("dispositivo", ""),
                "distribuidor": inc.get("distribuidor", ""),
                "accion_correctiva": inc.get("accion_correctiva", ""),
                "comentario": inc.get("comentario", ""),
                "estado": inc.get("estado", ""),
                "similitud": round(score, 3),
            })
    hist.sort(key=lambda x: x["similitud"], reverse=True)

    soluciones = []
    for prob in problemas:
        score = calcular_similitud(texto_consulta, prob.get("texto_norm", ""), dispositivo, prob.get("dispositivo", ""))
        if score > UMBRAL_CASO_SIMILAR:
            soluciones.append({
                "dispositivo": prob.get("dispositivo", ""),
                "problema": prob.get("problema", ""),
                "solucion": prob.get("solucion", ""),
                "similitud": round(score, 3),
            })
    soluciones.sort(key=lambda x: x["similitud"], reverse=True)

    return {"incidencias_historicas": hist[:limite], "problemas_solucion": soluciones[:limite]}


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
    # Quién llama. El correo es la puerta de entrada al caso: es lo que permite
    # cruzar este cuestionario con los tickets que ese cliente ya tiene abiertos
    # y con lo que contó la vez anterior. Antes el cuestionario no preguntaba
    # nada de la persona, así que un triaje no se podía atar a nadie.
    persona = datos.get("persona", {}) or {}

    partner = datos.get("partner", "IoT Fenster / MySmartWindow")
    dispositivo = datos.get("dispositivo", "Connect-1")
    num_afectados = datos.get("num_dispositivos_afectados", "1")
    area = datos.get("area_incidencia", "No identificado")

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

    # 2. Selección del diagnóstico por puntuación de reglas
    tags = set()
    sintomas_str = " ".join(sintomas).lower() + " " + descripcion.lower()
    mas_de_un_movil = app_info.get("mas_de_un_movil", "No probado")
    wifi_gen = wifi.get("generacion", "")
    wifi_seg = wifi.get("seguridad", "")
    hw_c1 = especifica.get("hw_c1", {}) or {}
    hw_c2 = especifica.get("hw_c2", {}) or {}

    contexto = {
        "dispositivo": dispositivo,
        "partner": partner,
        "area": area,
        "sintomas": normalizar_texto(sintomas_str),
        "wifi": wifi,
        "wifi_gen": wifi_gen,
        "wifi_seg": wifi_seg,
        "app_info": app_info,
        "alcance": alcance,
        "hw_c1": hw_c1,
        "hw_c2": hw_c2,
        "control_fisico": control_fisico,
        "control_app": control_app,
        "estado_app": estado_app,
        "num_afectados": num_afectados,
        "mas_de_un_movil": mas_de_un_movil,
    }

    ranking = puntuar_reglas(contexto)
    mejor = ranking[0]
    segunda = ranking[1] if len(ranking) > 1 else {"puntuacion": 0.0}
    margen = mejor["puntuacion"] - segunda["puntuacion"]
    concluyente = mejor["puntuacion"] >= UMBRAL_DECISION

    if concluyente:
        diagnostico_titulo = mejor["titulo"]
        causa_raiz = mejor["causa"]
        tags.update(mejor["tags"])
        pasos_recomendados = list(mejor["pasos"])
        nivel_gravedad = mejor["gravedad"]
        motivos_diagnostico = mejor["motivos"]
        # La confianza sale de la evidencia, no de un número escrito a mano. El
        # techo de la regla sigue siendo el máximo, pero hay que ganárselo: sin
        # margen sobre la segunda hipótesis, no se llega arriba. Antes un
        # diagnóstico falso salía con un 95 %, que es peor que no diagnosticar.
        confianza = round(min(mejor["techo"], 50.0 + mejor["puntuacion"] * 7.0 + min(margen, 3.0) * 5.0), 1)
    else:
        # Sin evidencia suficiente no se afirma nada. Decir "no concluyente" y
        # pedir los datos que faltan es más útil —y bastante más honesto— que
        # soltar el primer diagnóstico de la lista con un 95 % de confianza.
        diagnostico_titulo = "Sin diagnóstico concluyente: faltan datos del cuestionario"
        causa_raiz = (
            "Las respuestas recibidas no contienen evidencia suficiente para señalar una causa. "
            "Lo que hay son valores por defecto o datos de entorno que no confirman ningún fallo concreto."
        )
        tags.update(["#FaltanDatos", "#AmpliarCuestionario"])
        nivel_gravedad = "media"
        motivos_diagnostico = []
        pasos_recomendados = [
            "Preguntar si el equipo responde al pulsador físico y si responde desde la App: es lo que más separa unas causas de otras.",
            "Confirmar si el fallo afecta a un solo equipo o a todos los de la vivienda.",
            "Pedir una descripción literal de lo que hace el equipo, con las palabras del cliente.",
            "Comprobar el cifrado del router (WPA2 frente a WPA3) y si las bandas están separadas.",
        ]
        confianza = round(min(55.0, 30.0 + mejor["puntuacion"] * 10.0), 1)

    # Hipótesis consideradas, con su puntuación y el porqué. Se devuelven también
    # cuando no hay diagnóstico: son la pista de por dónde seguir preguntando.
    alternativas = [
        {
            "id": r["id"],
            "titulo": r["titulo"],
            "puntuacion": r["puntuacion"],
            "motivos": r["motivos"],
            "descartada_por": "sin señales en las respuestas" if r["puntuacion"] == 0 else "",
        }
        for r in ranking[:4]
        if r["puntuacion"] > 0 or not concluyente
    ]

    # 3. Filtrar los pasos recomendados excluyendo acciones ya realizadas (Checklist de descarte)
    pasos_filtrados = []
    acciones_hechas_norm = [normalizar_texto(a) for a in acciones_hechas]
    
    for paso in pasos_recomendados:
        paso_norm = normalizar_texto(paso)
        ya_probado = False
        
        # Comprobación semántica exhaustiva de acciones ya realizadas
        if any(h in paso_norm for h in ["reinicio", "reiniciar", "cortar corriente", "automatico general"]) and any("reinicio" in ah or "corte" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["reset", "fabrica", "10 segundos"]) and any("reset" in ah or "fabrica" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["router"]) and any("router" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["separar", "ssid", "2.4 ghz", "2.4g"]) and any("separar" in ah or "2.4" in ah or "ssid" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["datos moviles", "4g", "5g"]) and any("datos moviles" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["multimetro", "tension", "bornes", "230v", "multimetro"]) and any("multimetro" in ah or "tension" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["finales de carrera", "varilla"]) and any("finales" in ah or "carrera" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["invertir", "sentido de giro"]) and any("invertir" in ah or "giro" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["bluetooth", "ubicacion", "permiso", "red local", "bateria"]) and any("permiso" in ah or "bluetooth" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["cache", "reinstalar"]) and any("cache" in ah or "reinstal" in ah for ah in acciones_hechas_norm):
            ya_probado = True
        elif any(h in paso_norm for h in ["repetidor", "mesh", "jaula de faraday", "antena", "tapa de pvc"]) and any("repetidor" in ah or "cerca" in ah for ah in acciones_hechas_norm):
            ya_probado = True
            
        pasos_filtrados.append({
            "paso": paso,
            "ya_probado": ya_probado
        })

    # 4. Obtener Recursos Oficiales & Páginas de Manuales
    manual_encontrado = None
    # `palabras` se usa más abajo para buscar el vídeo. Se inicializa aquí
    # porque antes solo se asignaba dentro del try de la consulta de manuales:
    # si esa consulta fallaba —una query mal formada basta—, la búsqueda del
    # vídeo reventaba con NameError en vez de quedarse sin vídeo.
    palabras: List[str] = []
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

    # Si la búsqueda no encuentra manual, no se inventa uno.
    #
    # Aquí se devolvía un `manual_id: 1` fijo, con el nombre construido a mano
    # y un número de página inventado (3), apuntando siempre al PDF del
    # Connect-1 o al del C-Pulsar según el dispositivo. El técnico recibía una
    # referencia documental con toda la pinta de ser un resultado de búsqueda,
    # y era un valor por defecto: podía citarle al cliente una página que no
    # habla de su avería, o un manual que no es el de su equipo.
    #
    # Es el mismo tipo de fallo que el de los avisos de correo de la Fase 0:
    # dar por bueno algo que no ha pasado. Todos los consumidores de este campo
    # —la interfaz, la plantilla de WhatsApp y el parte en PDF— ya contemplan
    # que venga vacío, así que no mostrar nada es correcto y además es verdad.
    if not manual_encontrado:
        logger.info(
            f"Sin manual indexado para «{dispositivo} / {diagnostico_titulo}»: "
            f"no se sugiere ninguno."
        )

    # 4b. Vídeo de soporte, saltando directamente al segundo exacto del fragmento
    # de la transcripción que mejor coincide (antes solo se devolvía la URL genérica
    # del vídeo, sin usar el minutaje de video_fragmentos).
    video_encontrado = None
    if db and palabras:
        try:
            terminos_sql = " | ".join(palabras)
            query_video = text("""
                SELECT v.id AS video_db_id, v.video_id, v.titulo, v.url,
                       COALESCE(vf.segundo_inicio, 0) as segundo_inicio,
                       ts_rank(
                           setweight(v.metadatos_tsv, 'A') || setweight(COALESCE(vf.texto_tsv, v.transcripcion_tsv), 'C'),
                           to_tsquery('spanish', :q),
                           32
                       ) as relevancia
                FROM videos v
                LEFT JOIN video_fragmentos vf ON vf.video_id = v.id
                WHERE (
                    setweight(v.metadatos_tsv, 'A') || setweight(COALESCE(vf.texto_tsv, v.transcripcion_tsv), 'C')
                ) @@ to_tsquery('spanish', :q)
                ORDER BY relevancia DESC
                LIMIT 1;
            """)
            res_vid = db.execute(query_video, {"q": terminos_sql}).fetchone()
            if res_vid:
                segundos = int(res_vid.segundo_inicio or 0)
                video_encontrado = {
                    "video_db_id": res_vid.video_db_id,
                    "video_id": res_vid.video_id,
                    "titulo": res_vid.titulo,
                    "segundo": segundos,
                    "tiempo_formateado": f"{segundos // 60:02d}:{segundos % 60:02d}",
                    "url": f"{res_vid.url}&t={segundos}s" if segundos else res_vid.url
                }
        except Exception as e:
            logger.warning(f"Error consultando BD de vídeos en cuestionario: {e}")

    # 5. Generar Plantilla WhatsApp
    lista_pasos_txt = "\n".join([f"{idx+1}. {p['paso']}" for idx, p in enumerate(pasos_filtrados) if not p['ya_probado']])
    if not lista_pasos_txt:
        lista_pasos_txt = "\n".join([f"{idx+1}. {p['paso']}" for idx, p in enumerate(pasos_filtrados)])

    video_linea_whatsapp = (
        f"🎥 *Video Tutorial*: {video_encontrado['url']} (min. {video_encontrado['tiempo_formateado']})\n\n"
        if video_encontrado else ""
    )
    # El manual solo se cita si se ha encontrado de verdad. Antes esta línea
    # daba por hecho que siempre había uno, porque siempre lo había: se
    # inventaba unas líneas más arriba.
    manual_linea_whatsapp = (
        f"📄 *Manual de referencia*: {manual_encontrado['nombre']} (Pág. {manual_encontrado['pagina']})\n\n"
        if manual_encontrado else ""
    )
    whatsapp_msg = (
        f"🛠️ *SOPORTE TÉCNICO IOT - ASISTENCIA EN OBRA*\n\n"
        f"📋 *Equipo*: {dispositivo_efectivo} ({partner})\n"
        f"🔍 *Diagnóstico*: {diagnostico_titulo}\n"
        f"💡 *Causa identificada*: {causa_raiz}\n\n"
        f"👉 *Pasos de resolución recomendados*:\n{lista_pasos_txt}\n\n"
        f"{manual_linea_whatsapp}"
        f"{video_linea_whatsapp}"
        f"Por favor, realiza estas verificaciones y confírmanos el resultado. ¡Gracias!"
    )

    # 5b. Casos reales parecidos, de los dos Excel de la base SAT.
    casos_similares = {"incidencias_historicas": [], "problemas_solucion": []}
    try:
        # El dispositivo va aparte, no dentro del texto: `calcular_similitud`
        # ya lo pondera por su cuenta, y meterlo también en la consulta hacía
        # que el modelo pesara el doble y tapara lo que de verdad contó el
        # cliente.
        casos_similares = buscar_casos_similares(
            f"{sintomas_str} {area}".strip(), dispositivo, limite=3
        )
    except Exception as e:
        # Un Excel ausente o mal formado no puede dejar al técnico sin triaje.
        logger.warning(f"No se pudieron buscar casos similares en la base SAT: {e}")

    # 6. Prefill para Ticket SAT
    ticket_prefill = {
        # La persona es la puerta de entrada al caso, así que viaja al ticket
        # antes que nada: sin correo, el ticket nace huérfano y no hay forma de
        # cruzarlo con lo que ese cliente ya había contado.
        "instalador": (persona.get("nombre") or "").strip(),
        "email": (persona.get("correo") or "").strip(),
        "telefono": (persona.get("telefono") or "").strip(),
        "obra": (persona.get("obra") or "").strip(),
        "dispositivo": dispositivo,
        "distribuidor": partner,
        "sintoma": f"[{area}] " + (", ".join(sintomas) if sintomas else descripcion[:120]),
        "diagnostico": f"{diagnostico_titulo}. Causa: {causa_raiz}" if concluyente else "",
        "solucion": "\n".join([p['paso'] for p in pasos_filtrados if not p['ya_probado']]) if concluyente else "",
        "estado": "en_espera",
        "prioridad": "urgente" if momento == "Durante instalación" or "Todos los de la vivienda" in str(num_afectados) else "normal"
    }

    # 7. Construir Top Diagnósticos sugeridos (Feedback Loop)
    top_diagnosticos_cuestionario = [{
        "titulo": diagnostico_titulo,
        "diagnostico": diagnostico_titulo,
        "solucion": pasos_filtrados[0]["paso"] if pasos_filtrados else causa_raiz,
        "confianza": confianza,
        "fuente": "asistencia_guiada"
    }]

    # Las hipótesis que no ganaron, con su puntuación, para que el técnico vea
    # qué más se consideró en vez de recibir una única respuesta sin contexto.
    for alt in alternativas[1:]:
        if alt["puntuacion"] > 0:
            top_diagnosticos_cuestionario.append({
                "titulo": alt["titulo"],
                "diagnostico": alt["titulo"],
                "solucion": "; ".join(alt["motivos"]) or "Sin señales concluyentes en las respuestas.",
                "confianza": round(min(80.0, 40.0 + alt["puntuacion"] * 8.0), 1),
                "fuente": "hipotesis_alternativa"
            })

    # Los precedentes del Excel también son candidatos a mirar.
    for caso in casos_similares.get("problemas_solucion", [])[:2]:
        top_diagnosticos_cuestionario.append({
            "titulo": f"Caso documentado · {caso['dispositivo']}",
            "diagnostico": caso["problema"],
            "solucion": caso["solucion"],
            "confianza": round(min(88.0, 55.0 + caso["similitud"] * 35.0), 1),
            "fuente": "base_sat_excel"
        })

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
        # Si esto viene en False, el diagnóstico es un marcador de "faltan
        # datos", no una conclusión: la interfaz tiene que decirlo así.
        "concluyente": concluyente,
        "diagnostico_titulo": diagnostico_titulo,
        "causa_raiz": causa_raiz,
        # Por qué ha salido este diagnóstico y no otro. Sin esto, el técnico no
        # tiene forma de saber si el triaje ha entendido lo que le contaron.
        "motivos_diagnostico": motivos_diagnostico,
        "hipotesis_consideradas": alternativas,
        "casos_similares": casos_similares,
        "persona": persona,
        "nivel_gravedad": nivel_gravedad,
        "equivalencia_partner": equivalencia_partner,
        "tags_solucion": list(tags),
        "pasos_accion": pasos_filtrados,
        "manual_recomendado": manual_encontrado,
        "video_recomendado": video_encontrado,
        "whatsapp_template": whatsapp_msg,
        "ticket_prefill": ticket_prefill,
        "top_diagnosticos": top_diagnosticos_cuestionario
    }

