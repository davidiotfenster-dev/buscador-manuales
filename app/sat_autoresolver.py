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

    # 2. Inferencia de Matriz de Estados (Físico vs App)
    tags = set()
    diagnostico_titulo = ""
    causa_raiz = ""
    pasos_recomendados = []
    nivel_gravedad = "media"
    confianza = 85.0

    sintomas_str = " ".join(sintomas).lower() + " " + descripcion.lower()
    mas_de_un_movil = app_info.get("mas_de_un_movil", "No probado")
    wifi_gen = wifi.get("generacion", "")
    wifi_seg = wifi.get("seguridad", "")
    hw_c1 = especifica.get("hw_c1", {})
    hw_c2 = especifica.get("hw_c2", {})

    # 1. Evaluación: Relés conmutan pero el motor no responde (frecuente en Connect-1)
    if (dispositivo == "Connect-1" and hw_c1.get("oyen_reles") and not hw_c1.get("motor_responde")) or any(k in sintomas_str for k in ["reles pero no se mueve", "clic de rele pero no", "suena el rele pero no"]):
        diagnostico_titulo = "Relés Electrónicos Conmutan pero Motor Tubular no Responde"
        causa_raiz = "El módulo Connect-1 maniobra correctamente pero la tensión no llega al bobinado del motor. Causas probables: neutro común (cable azul) suelto o desconectado, final de carrera superior/inferior completamente cerrado, corte térmico del motor tras esfuerzo o condensador averiado."
        tags.update(["#NeutroComunAzul", "#VerificarFasesSalida", "#FinalesCarreraMotor", "#ProteccionTermica"])
        pasos_recomendados = [
            "Comprobar con un multímetro que entre el Neutro (N) y OUT1/OUT2 se miden 230V AC al conmutar la subida o bajada.",
            "Verificar la conexión del cable Azul (Neutro del motor) en la regleta de bornes o clema WAGO.",
            "Girar los tornillos de final de carrera del motor 5-6 vueltas con la varilla reguladora para liberar posibles topes mecánicos forzados.",
            "Si el motor estuvo funcionando reiteradamente, dejar enfriar 20 minutos (disparo del protector bimetálico térmico)."
        ]
        confianza = 97.0

    # 2. Evaluación: Inversión de Giros (Fases invertidas o sentido de motor)
    elif any(k in sintomas_str for k in ["bajar sube", "sube cuando bajo", "al reves", "invertid", "giro"]):
        diagnostico_titulo = "Inversión de Fases de Maniobra / Sentido de Giro Motor"
        causa_raiz = "Las salidas de motor OUT1 (Subida) y OUT2 (Bajada) están intercambiadas o el motor está montado en el lado opuesto del tambor de persiana."
        tags.update(["#InvertirFasesMotor", "#AppSwapGiro", "#VerificarSentidoGiro"])
        pasos_recomendados = [
            "En la App MySmartWindow/BlickDomi: Entrar en Ajustes de Ventana > 'Invertir Sentido de Giro' y activar la casilla.",
            "Si se prefiere por cableado: Desconectar magnetotérmico 230V e intercambiar los cables Marrón y Negro en las salidas del módulo.",
            "Comprobar que al pulsar ▲ la persiana sube y al pulsar ▼ la persiana baja.",
            "Lanzar una calibración completa desde la App."
        ]
        confianza = 96.0

    # 3. Evaluación: Incompatibilidad de Red WPA3 / Wi-Fi 6 (802.11ax) / Wi-Fi 7
    elif "WPA3" in wifi_seg or any(g in wifi_gen for g in ["Wi-Fi 6", "Wi-Fi 7"]) or "wpa3" in sintomas_str:
        diagnostico_titulo = "Incompatibilidad de Cifrado WPA3 o Trama Wi-Fi 6/7 en Red 2.4 GHz"
        causa_raiz = "Los microcontroladores IoT Wi-Fi 2.4 GHz requieren autenticación WPA2-PSK (AES). Las redes con WPA3-SAE Only o con Protected Management Frames (PMF) obligatorios impiden la conexión o provocan caídas continuas."
        tags.update(["#DesactivarWPA3Only", "#ModoMixtoWPA2", "#DesactivarPMF", "#CompatibilidadIoT"])
        pasos_recomendados = [
            "Acceder a la configuración del router y cambiar la seguridad de la red 2.4 GHz a 'WPA2-PSK (AES)' o 'WPA2/WPA3 Personal Mixto'.",
            "Desactivar 'PMF' (Protected Management Frames) o configurarlo en 'Opcional / Capable', nunca 'Obligatorio'.",
            "Verificar que el nombre de la red (SSID) y la contraseña no contengan caracteres especiales (ñ, comillas, tildes).",
            "Reiniciar el router y reconectar el equipo IoT."
        ]
        confianza = 95.0

    # 4. Evaluación: Incidencia Global de Instalación (Todos los equipos o varios móviles)
    elif num_afectados == "Todos los de la vivienda/instalación" or mas_de_un_movil in ["Sí (Común a la vivienda)", "Varios móviles con el mismo fallo"]:
        diagnostico_titulo = "Incidencia General de Red Local, Router o Línea Eléctrica"
        causa_raiz = "Al estar afectados todos los dispositivos de la instalación o manifestarse en múltiples teléfonos simultáneamente, se descarta una avería de hardware unitario. El fallo radica en el router principal (bloqueo DHCP, tabla ARP saturada, caída DNS), corte de suministro o aislamiento de red."
        tags.update(["#AveriaGlobalRed", "#ReinicioRouter", "#DHCPExhaustion", "#LineaElectricaGeneral"])
        nivel_gravedad = "alta"
        pasos_recomendados = [
            "Reiniciar el router principal y los puntos de acceso/Mesh apagándolos de la toma durante 30 segundos.",
            "Comprobar si el router ha agotado el rango de direcciones IP disponibles en el servidor DHCP (límite /24 saturado).",
            "Verificar si el interruptor magnetotérmico general de la línea de persianas ha saltado en el cuadro eléctrico.",
            "Comprobar la conectividad a internet externa y servidores DNS de la vivienda."
        ]
        confianza = 94.0

    # 5. Evaluación: Disparidad de Smartphone ("Solo en este móvil" o "En unos sí y otros no")
    elif mas_de_un_movil in ["No (Solo en este móvil)", "En unos móviles funciona y en otros no"]:
        diagnostico_titulo = "Conflicto de Permisos Locales o Caché en Smartphone Específico"
        causa_raiz = "La instalación física y la red operan correctamente ya que otros terminales funcionan con normalidad. La incidencia radica en permisos locales del smartphone (permiso 'Red Local' en iOS, ahorro agresivo de batería en Android) o datos corruptos en caché."
        tags.update(["#PermisosRedLocalIOS", "#OptimizacionBateriaAndroid", "#BorrarCacheApp"])
        pasos_recomendados = [
            "En dispositivos iOS (iPhone): Ajustes > Privacidad y Seguridad > Red Local > Comprobar que la App tiene el permiso concedido.",
            "En Android: Ajustes > Aplicaciones > App > Batería > Seleccionar 'Sin restricciones' (evitar suspensión de procesos en segundo plano).",
            "Borrar el almacenamiento en caché de la App o desinstalar y reinstalar desde App Store / Google Play.",
            "Verificar que el smartphone no está conectado a una red Wi-Fi de invitados (Guest Network) aislada."
        ]
        confianza = 93.0

    # 6. Evaluación de Control Físico KO + App KO (Alimentación / Corte térmico)
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

    # 7. Evaluación de Control Físico OK + App KO (Conectividad / Wi-Fi / Cloud)
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

    # 8. Evaluación de Vinculación: 0 dispositivos o Band Steering activo
    elif any(k in sintomas_str for k in ["no descubre", "0 dispositivos", "cero dispositivos", "menos dispositivos", "vincula pero no aparece"]) or (wifi.get("tipo_red") in ["Red mixta 2.4/5 GHz (mismo SSID)", "Dual 2,4/5 GHz"] and wifi.get("ssid_separados") == "No"):
        diagnostico_titulo = "Band Steering Activo en Router / Frecuencia 5 GHz en Emparejamiento"
        causa_raiz = "El router emite 2.4 y 5 GHz bajo el mismo SSID con Band Steering forzado. El smartphone negocia enlace en 5 GHz y el módulo IoT (solo radio 2.4 GHz) no puede completar el descubrimiento BLE/Wi-Fi."
        tags.update(["#PermisosBluetooth", "#Forzar24GHz", "#ModoEmparejamiento", "#Reset10Segundos"])
        pasos_recomendados = [
            "En el teléfono: Activar Bluetooth, Ubicación (GPS) y permisos de 'Dispositivos Cercanos' en la App.",
            "Separar temporalmente los nombres de red en el router (ej: Red_2.4G y Red_5G) y conectar el móvil a la 2.4 GHz.",
            "Desactivar temporalmente los datos móviles (4G/5G) en el teléfono durante la vinculación.",
            "Poner el dispositivo en modo emparejamiento pulsando 5 segundos el botón de configuración (parpadeo rápido)."
        ]
        confianza = 95.0

    # 9. Evaluación de Calibración / Recorrido
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

    # 10. Evaluación de Sensorización Connect-2 / Oscilobatiente
    elif "Connect-2" in dispositivo and (hw_c2.get("oscilo") or hw_c2.get("apertura") or any(k in sintomas_str for k in ["oscilo", "sensor", "temperatura", "co2", "humedad", "voc"])):
        diagnostico_titulo = "Desalineación de Sensores en Hoja Oscilobatiente o Precalentamiento Ambiental"
        causa_raiz = "El sensor de apertura/gestual se desalinea físicamente con la hoja en posición oscilobatiente, o los sensores de CO2/VOC requieren tiempo de estabilización."
        tags.update(["#SensorOscilobatiente", "#AlineacionIman", "#PrecalentamientoCO2"])
        pasos_recomendados = [
            "Verificar que el imán sensor del marco y la hoja mantienen una distancia inferior a 8 mm en posición cerrada.",
            "Recordar que en posición oscilobatiente el sensor gestual se desactiva por seguridad estructural.",
            "Para lecturas de CO2 y VOC (calidad de aire), permitir 24-48h de conexión continua para la calibración del sensor térmico."
        ]
        confianza = 89.0

    # 11. Evaluación de C-Wall
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

    # 12. Evaluación de WAlarm
    elif "WAlarm" in dispositivo:
        diagnostico_titulo = "Verificación de Batería, Sabotaje y Contacto Magnético WAlarm"
        causa_raiz = "Nivel de batería bajo, microswitch de sabotaje (tamper) no presionado contra el marco, o desalineación del imán exterior."
        tags.update(["#TamperSabotaje", "#BateriaWAlarm", "#TestSirenaApp"])
        pasos_recomendados = [
            "Comprobar que la lengüeta de tamper posterior está completamente apretada contra el marco.",
            "Verificar el nivel de batería en la App o sustituir pila si la tensión cae por debajo de 2.8V.",
            "Realizar un test de sirena desde la App para comprobar el buzzer integrado."
        ]
        confianza = 90.0

    # 13. Evaluación por Entorno Wi-Fi / Cobertura
    elif wifi.get("rssi") in ["Bajo", "<-75 dBm", "Bajo (-65 a -75 dBm)", "Muy débil / crítico (< -75 dBm)"] or "Metal" in str(alcance.get("obstaculos", [])):
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

    # 2b. La confianza de cada rama era un valor fijo asignado a mano. Aquí se
    # recalcula con la similitud textual real entre la evidencia aportada por el
    # técnico (síntomas, descripción y campos específicos) y el diagnóstico de la
    # rama seleccionada: el valor fijo pasa a ser solo el techo de esa rama, nunca
    # se supera, pero baja si la evidencia libre aportada no la respalda bien.
    texto_evidencia = " ".join(filter(None, [
        sintomas_str,
        str(wifi.get("seguridad") or ""), str(wifi.get("generacion") or ""),
        str(app_info.get("mas_de_un_movil") or ""),
        " ".join(str(v) for v in hw_c1.values()),
        " ".join(str(v) for v in hw_c2.values()),
    ])).strip()
    if texto_evidencia and diagnostico_titulo:
        similitud = calcular_similitud(texto_evidencia, f"{diagnostico_titulo} {causa_raiz}", dispositivo, dispositivo)
        confianza = round(min(confianza, 65.0 + similitud * 60.0), 1)

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
    whatsapp_msg = (
        f"🛠️ *SOPORTE TÉCNICO IOT - ASISTENCIA EN OBRA*\n\n"
        f"📋 *Equipo*: {dispositivo_efectivo} ({partner})\n"
        f"🔍 *Diagnóstico*: {diagnostico_titulo}\n"
        f"💡 *Causa identificada*: {causa_raiz}\n\n"
        f"👉 *Pasos de resolución recomendados*:\n{lista_pasos_txt}\n\n"
        f"📄 *Manual de referencia*: {manual_encontrado['nombre']} (Pág. {manual_encontrado['pagina']})\n\n"
        f"{video_linea_whatsapp}"
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
        "video_recomendado": video_encontrado,
        "whatsapp_template": whatsapp_msg,
        "ticket_prefill": ticket_prefill,
        "top_diagnosticos": top_diagnosticos_cuestionario
    }

