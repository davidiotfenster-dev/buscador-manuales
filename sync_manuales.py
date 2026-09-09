"""
Script de sincronización e indexación automática de manuales para Buscador de Manuales.
Escanea la carpeta 'manuales/', extrae el texto de cada página e inserta o actualiza
los registros en PostgreSQL con metadatos técnicos enriquecidos, etiquetas (tags) y niveles de acceso (RBAC).

Uso:
    python sync_manuales.py [--dry-run] [--force]
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pypdf import PdfReader

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sync_manuales")

MANUALES_DIR = BASE_DIR / "manuales"

# ==============================================================================
# CATÁLOGO CANÓNICO DE METADATOS Y ETIQUETAS (TAGS) TÉCNICAS SAT
# ==============================================================================
CATALOGO_MANUALES: Dict[str, Dict[str, Any]] = {
    # --- 1. Documentación Técnica SAT (Procedente de nuevo/DOCUMENTACIÓN SAT) ---
    "Problemas_y_Soluciones_SAT.pdf": {
        "nombre_original": "Guía de Problemas y Soluciones SAT — Averías Frecuentes",
        "dispositivo": "TODOS",
        "categoria": "Problemas y Soluciones",
        "nivel_acceso": "tecnico",
        "etiquetas": "sat, averias, problemas y soluciones, no enciende, sin alimentacion, no sube persiana, no baja persiana, pulsador insensible, pulsador sin sensibilidad, cable cortado, parpadea constante, modo candado, rele suena, motor roto, ruido electrico, se mueven solas, invertir controles, giro invertido, swap giro, finales de carrera, descalibrado, calibracion, recalibrar, reset simple, hard reset, somfy, cherubini, becker, fallo pulsador"
    },
    "SOPORTE_APPs_TECNICO_DOCUMENTO.pdf": {
        "nombre_original": "Soporte Técnico de Aplicaciones y Arquitectura de Software",
        "dispositivo": "TODOS",
        "categoria": "Soporte SAT",
        "nivel_acceso": "tecnico",
        "etiquetas": "apps, arquitectura, core comun, mysmartwindow, greenteq wave, icon smart home, konect, unificado, soporte tecnico, alexa, google home, siri, escenas, grupos, virtual rooms, automatizaciones, firmware ota, cuentas, permisos instalador, usuario"
    },
    "IoT_FENSTER_Apps_Technical_Documentation.pdf": {
        "nombre_original": "IoT Fenster Apps Technical Documentation and Architecture (English)",
        "dispositivo": "TODOS",
        "categoria": "Soporte SAT",
        "nivel_acceso": "tecnico",
        "etiquetas": "apps, shared core, mysmartwindow, greenteq wave, icon smart home, konect, architecture, unified support, ota firmware, alexa, google home, english, sat, cloud sync"
    },
    "CONECTIVIDAD_REQUISITOS.pdf": {
        "nombre_original": "Requisitos de Conectividad, Red WiFi y CG-NAT",
        "dispositivo": "TODOS",
        "categoria": "Conectividad y Red",
        "nivel_acceso": "tecnico",
        "etiquetas": "conectividad, red wifi, wifi 2.4ghz, cgnat, carrier-grade nat, ip publica, digi plus, masmovil, pepephone, wpa2, wpa3, router, aisla clientes, ap isolation, client isolation, wmf, wireless multicast forwarding, wps, multicast, puertos, mqtt 8883, puerto 443, movistar, o2, orange, vodafone, livebox, hgu, band steering, firewall, red local, dhcp, dns 53, ntp 123"
    },
    "Conectivity_Requirements.pdf": {
        "nombre_original": "Connectivity Requirements and CG-NAT Guide (English)",
        "dispositivo": "TODOS",
        "categoria": "Conectividad y Red",
        "nivel_acceso": "tecnico",
        "etiquetas": "connectivity, wifi, 2.4ghz, cgnat, public ip, digi plus, wpa2, router, client isolation, ap isolation, wmf, multicast, ports, mqtt 8883, port 443, english, network, isp"
    },
    "DENOMINACION_DE_MARCAS_Y_DISPOSITIVOS.pdf": {
        "nombre_original": "Denominación de Marcas Partner y Catálogo de Dispositivos",
        "dispositivo": "TODOS",
        "categoria": "Denominación y Marcas",
        "nivel_acceso": "publico",
        "etiquetas": "marcas, denominacion, equivalencias, partner, mysmartwindow, konect, kommerling, greenteq wave, vbh, icon smart home, procomsa, blickdomi, solven, connect-1, wave-1, icon1, essential+, connect-2, wave-2, icon2, sentry, c-wall, wave 3, wave wall, icon3, pulse, c-pulsar, wave4, icon mini, connect evo, konect elite sense, blu-connect, witooth"
    },
    "BRAND_AND_DEVICE_NAMING.pdf": {
        "nombre_original": "Brand and Device Naming Guide (English)",
        "dispositivo": "TODOS",
        "categoria": "Denominación y Marcas",
        "nivel_acceso": "publico",
        "etiquetas": "brands, naming, correlations, partner apps, mysmartwindow, konect, greenteq wave, icon smart home, connect-1, wave-1, icon1, essential+, connect-2, wave-2, icon2, sentry, c-wall, wave 3, wave wall, icon3, pulse, c-pulsar, wave4, icon mini, connect evo, sense, english"
    },
    "MODOS_DISPOSITIVOS.pdf": {
        "nombre_original": "Modos de Dispositivos, Procedimientos de Reset y Estados LED",
        "dispositivo": "TODOS",
        "categoria": "Modos y Reset",
        "nivel_acceso": "tecnico",
        "etiquetas": "modos, modo fabrica, factory mode, reset simple, hard reset, restablecimiento completo, ventana 60 minutos, led parpadea 2s, led verde, led fijo, boton reset, pincho reset, clip, subida bajada 5s, sensor gestual 5s, pulsar 8s, connect-1, connect-2, c-wall, c-pulsar, connect evo, konect elite, estados led, pulsador local"
    },
    "Technical_Specifications_Device_Operation_and_Pairing.pdf": {
        "nombre_original": "Device Operation, Reset and Pairing Specifications (English)",
        "dispositivo": "TODOS",
        "categoria": "Modos y Reset",
        "nivel_acceso": "tecnico",
        "etiquetas": "factory mode, reset, hard reset, pairing window, led blinking 2s, led green, reset button, pin reset, 60 minutes, connect-1, connect-2, c-wall, c-pulsar, connect evo, led status, english"
    },
    "Manual_de_vinculacion_MySmartWindow.pdf": {
        "nombre_original": "Manual de Vinculación y Emparejamiento de Dispositivos",
        "dispositivo": "TODOS",
        "categoria": "Vinculación y Emparejamiento",
        "nivel_acceso": "publico",
        "etiquetas": "vinculacion, emparejamiento, multivinculacion, multicast, punto a punto, modo ap, red bdsmart, red connect, asistente app, pairing, wifi 2.4ghz, bluetooth ble, broadcast, permisos ubicacion, datos moviles, problemas vinculacion"
    },
    "Linking_Manual_MySmartWindow.pdf": {
        "nombre_original": "Device Linking Manual (English)",
        "dispositivo": "TODOS",
        "categoria": "Vinculación y Emparejamiento",
        "nivel_acceso": "publico",
        "etiquetas": "linking, pairing, multi-linking, multicast, point to point, ap mode, bdsmart, app method, wifi 2.4ghz, bluetooth, pairing guide, english"
    },
    "ENLACES_DE_LOS_VIDEOS_DE_YOUTUBE.pdf": {
        "nombre_original": "Catálogo de Vídeos de Soporte y Enlaces YouTube",
        "dispositivo": "TODOS",
        "categoria": "Vídeos y Tutoriales",
        "nivel_acceso": "publico",
        "etiquetas": "videos youtube, tutoriales, enlaces soporte, instalacion en ventana, fabricacion ventana, como instalar, vinculacion video, configuracion router, livebox, movistar hgu, digi, motores somfy, cherubini, becker, tareas offline, alexa, google home, ifttt, italiano, ingles"
    },

    # --- 2. Manuales Originales de Dispositivos y FAQs ---
    "Connect-1_Documentacion_MySmartWindow.pdf": {
        "nombre_original": "Documentación Funcional y Técnica Connect-1",
        "dispositivo": "CONNECT-1",
        "categoria": "Manuales de Dispositivos",
        "nivel_acceso": "publico",
        "etiquetas": "connect-1, wave-1, icon1, essential+, marco ventana, pulsador capacitivo, persiana, toldo, veneciana, calibracion, bornes 230v, borne l, borne n, bornes subida bajada, instalacion aluminio, antena wifi, reset simple"
    },
    "Connect-2_Documentacion_MySmartWindow.pdf": {
        "nombre_original": "Documentación Funcional y Técnica Connect-2",
        "dispositivo": "CONNECT-2",
        "categoria": "Manuales de Dispositivos",
        "nivel_acceso": "publico",
        "etiquetas": "connect-2, wave-2, icon2, sentry, tres botones, sensor co2, sensor voc, calidad aire, detector efraccion, alarma apertura, veneciana orientacion lamas, ventilacion automatica, instalacion marco"
    },
    "C-PULSAR_Documentacion_MySmartWindow.pdf": {
        "nombre_original": "Documentación Funcional y Técnica C-Pulsar",
        "dispositivo": "C-PULSAR",
        "categoria": "Manuales de Dispositivos",
        "nivel_acceso": "publico",
        "etiquetas": "c-pulsar, wave4, icon mini, pulsador inalambrico, modulo persiana cajon, boton retroiluminado, pila cr2032, radiofrecuencia, receptor cajon, instalacion sin rozas, sin cables, reset 8s"
    },
    "C-Wall_Documentacion_MySmartWindow.pdf": {
        "nombre_original": "Documentación Funcional y Técnica C-Wall",
        "dispositivo": "C-WALL",
        "categoria": "Manuales de Dispositivos",
        "nivel_acceso": "publico",
        "etiquetas": "c-wall, wave 3, wave wall, icon3, pulse, interruptor pared, mecanismo empotrar, caja universal 60mm, boton central, apagado general, escena general, wifi 6, bluetooth, esquema electrico 230v"
    },
    "Preguntas-frecuentes-MySmartWindow-1.pdf": {
        "nombre_original": "Preguntas Frecuentes sobre Motores y Compatibilidad",
        "dispositivo": "TODOS",
        "categoria": "Manuales de Usuario",
        "nivel_acceso": "publico",
        "etiquetas": "faq, preguntas frecuentes, motores compatibles, motor 4 hilos, 4 cables, somfy, cherubini, becker, inversor mecanico, motor electronico, finales carrera mecanicos, dudas obra"
    },
    "6b1a3a47-ec60-4b7c-b438-7426a8f8cb32_Contraseas_Wifi.pdf": {
        "nombre_original": "Guía de Redes WiFi, Credenciales y Laboratorio SAT",
        "dispositivo": "TODOS",
        "categoria": "Conectividad y Red",
        "nivel_acceso": "tecnico",
        "etiquetas": "redes wifi, credenciales, contrasenas taller, ssid laboratorio, contrasenas wifi, banco de pruebas, taller i+d, configuracion router"
    }
}

# Mapeo de etiquetas temáticas específicas para vídeos de YouTube
MAPEO_TAGS_VIDEOS: Dict[str, str] = {
    "Vinculación AP de C-Pulsar": "c-pulsar, vinculacion, modo ap, punto a punto, wifi, emparejamiento, red bdsmart",
    "Instalación de Connect Smart - Pulsar": "c-pulsar, instalacion, montaje, pulsador inalambrico, cajon, conexion 230v",
    "Uso y emparejamiento del mando Blu-Connect": "blu-connect, mando a distancia, emparejamiento, bluetooth, witooth, control local",
    "Vinculación C WALL Shutter": "c-wall, vinculacion, persiana, shutter, emparejamiento, interruptor pared",
    "Servicio Offline de Connect-2": "connect-2, offline, modo local, sin internet, tareas locales, programacion offline",
    "Modos luz led y bloqueo": "luces led, modos led, bloqueo, modo candado, parpadeo, estados led, seguridad ninos",
    "Vinculación Bluetooth": "bluetooth, vinculacion ble, emparejamiento, movil, connect, deteccion rapida",
    "Instalación Pulsar en Cajón de Persiana": "c-pulsar, cajon persiana, instalacion, motor, conexion, receptor",
    "C-WALL Sky, diseñado para ventanas abatibles": "c-wall, sky, ventana abatible, motor abatible, ventilacion, compas",
    "Activa el Modo Manual (Hard Reset) de tu C-Pulsar": "c-pulsar, hard reset, modo manual, reset 8s, fabrica, pulsador inalambrico",
    "Multiwifi - MySmartWindow": "multiwifi, cambiar wifi, redes wifi, cambio router, conexion, contrasenas wifi",
    "Acciones Abatible Virtual Rooms": "virtual rooms, abatible, grupos, app, escenas, automatizacion",
    "Acciones Persiana Virtual Rooms": "virtual rooms, persiana, grupos, app, escenas, automatizacion",
    "Eliminar Virtual Rooms": "virtual rooms, eliminar grupo, app, configuracion, estancias",
    "Editar Virtual Rooms": "virtual rooms, editar grupo, app, configuracion, estancias",
    "Crear Virtual Rooms": "virtual rooms, crear grupo, app, estancias, habitaciones, zonas",
    "Activación de Candado - Seguridad": "candado, modo candado, bloqueo, seguridad ninos, persiana bloqueada, desbloqueo",
    "Tarea programada abrir ventana abatible": "tareas programadas, programacion horaria, abatible, automatizacion, horario",
    "Tarea programada bajar persiana sin conexión": "tareas programadas, persiana, offline, sin conexion, reloj interno, automatizacion",
    "Cómo se instala C-WALL Shutter": "c-wall, instalacion, montaje, interruptor pared, caja 60mm, conexion 230v",
    "Motorización de una ventana": "motorizacion, motor persiana, instalacion, montaje motor, 4 hilos, mecanico",
    "Preguntas frecuentes sobre tus dispositivos": "preguntas frecuentes, faq, dudas, soporte sat, motores, compatibilidad",
    "Perfiles de Usuario": "perfiles usuario, cuentas, permisos, familia, invitados, instalador",
    "Vinculación Multicast C-Pulsar": "c-pulsar, vinculacion, multicast, broadcast, emparejamiento, wmf",
    "Configuración Router Orange y Jazztel": "router, orange, jazztel, livebox, 2.4ghz, wifi, puertos, configuracion router",
    "Indicador del sensor de apertura": "sensor apertura, connect-2, detector apertura, efraccion, seguridad, ventana",
    "Solución de problemas  de vinculación": "solucion problemas, problemas vinculacion, router, fallo wifi, ayuda sat",
    "Configuración del router": "configuracion router, wmf, aislamiento clientes, ap isolation, 2.4ghz, wpa2, cgnat",
    "Qué es IFTTT": "ifttt, integracion domotica, escenas, automatizacion, servicios externos",
    "Vincular Google Home": "google home, asistente google, control por voz, domotica, integracion"
}


def resolver_metadatos_archivo(nombre_archivo: str) -> Dict[str, Any]:
    """Resuelve los metadatos y etiquetas de un archivo aplicando reglas canónicas y alias."""
    # 1. Coincidencia directa exacta
    if nombre_archivo in CATALOGO_MANUALES:
        return CATALOGO_MANUALES[nombre_archivo]

    # 2. Coincidencia por sufijos temporales _1, _2, _3
    nombre_base = nombre_archivo
    for sufijo in ["_1.pdf", "_2.pdf", "_3.pdf"]:
        if nombre_archivo.endswith(sufijo):
            nombre_base = nombre_archivo[:-len(sufijo)] + ".pdf"
            break
    if nombre_base in CATALOGO_MANUALES:
        return CATALOGO_MANUALES[nombre_base]

    # 3. Coincidencia por patrones o nombres alternativos
    norm = nombre_archivo.lower().replace("_", " ").replace("-", " ")
    if "contrase" in norm and "wifi" in norm:
        return CATALOGO_MANUALES["6b1a3a47-ec60-4b7c-b438-7426a8f8cb32_Contraseas_Wifi.pdf"]
    if "connect 1" in norm:
        return CATALOGO_MANUALES["Connect-1_Documentacion_MySmartWindow.pdf"]
    if "connect 2" in norm:
        return CATALOGO_MANUALES["Connect-2_Documentacion_MySmartWindow.pdf"]
    if "c pulsar" in norm:
        return CATALOGO_MANUALES["C-PULSAR_Documentacion_MySmartWindow.pdf"]
    if "c wall" in norm:
        return CATALOGO_MANUALES["C-Wall_Documentacion_MySmartWindow.pdf"]
    if "problemas" in norm or "averias" in norm:
        return CATALOGO_MANUALES["Problemas_y_Soluciones_SAT.pdf"]
    if "conectividad" in norm or "connectivity" in norm:
        return CATALOGO_MANUALES["CONECTIVIDAD_REQUISITOS.pdf"]
    if "denominacion" in norm or "brand" in norm:
        return CATALOGO_MANUALES["DENOMINACION_DE_MARCAS_Y_DISPOSITIVOS.pdf"]
    if "modos" in norm or "operation" in norm or "reset" in norm:
        return CATALOGO_MANUALES["MODOS_DISPOSITIVOS.pdf"]
    if "vinculacion" in norm or "linking" in norm:
        return CATALOGO_MANUALES["Manual_de_vinculacion_MySmartWindow.pdf"]
    if "soporte apps" in norm or "apps technical" in norm:
        return CATALOGO_MANUALES["SOPORTE_APPs_TECNICO_DOCUMENTO.pdf"]
    if "videos" in norm or "youtube" in norm or "enlaces" in norm:
        return CATALOGO_MANUALES["ENLACES_DE_LOS_VIDEOS_DE_YOUTUBE.pdf"]
    if "preguntas" in norm or "faq" in norm:
        return CATALOGO_MANUALES["Preguntas-frecuentes-MySmartWindow-1.pdf"]

    return {
        "nombre_original": nombre_archivo.replace("_", " "),
        "dispositivo": "TODOS",
        "categoria": "Manuales Técnicos",
        "nivel_acceso": "publico",
        "etiquetas": "general, manual"
    }


def extraer_paginas_pdf(ruta_pdf: Path) -> List[Tuple[str, bool]]:
    """Extrae el texto de cada página de un PDF eliminando caracteres nulos."""
    reader = PdfReader(str(ruta_pdf))
    paginas = []
    for i, pagina in enumerate(reader.pages, start=1):
        txt = (pagina.extract_text() or "").replace("\x00", "")
        # Sanitizar caracteres nulos adicionales
        txt = "".join(ch for ch in txt if ord(ch) != 0)
        paginas.append((txt.strip(), False))
    return paginas


def sincronizar_etiquetas_videos(database) -> int:
    """Actualiza las etiquetas de los vídeos en la base de datos con descriptores técnicos específicos."""
    actualizados = 0
    try:
        from app.database import SessionLocal, Video
        db = SessionLocal()
        try:
            videos = db.query(Video).all()
            for v in videos:
                nuevas_tags = None
                for clave, tags in MAPEO_TAGS_VIDEOS.items():
                    if clave.lower() in v.titulo.lower():
                        nuevas_tags = tags
                        break
                if nuevas_tags and v.etiquetas != nuevas_tags:
                    v.etiquetas = nuevas_tags
                    actualizados += 1
                elif not v.etiquetas or v.etiquetas == "video, tutorial, configuracion, ":
                    disp = (v.dispositivo or "").lower()
                    v.etiquetas = f"video, tutorial, configuracion, soporte, {disp}".strip(", ")
                    actualizados += 1
            db.commit()
            if actualizados > 0:
                logger.info(f"Actualizadas etiquetas para {actualizados} vídeos de YouTube en la base de datos.")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"No se pudieron sincronizar etiquetas de vídeos: {e}")
    return actualizados


def sincronizar_manuales(dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
    """
    Escanea la carpeta de manuales y sincroniza cada archivo con PostgreSQL.
    """
    logger.info("=" * 60)
    logger.info(f"Iniciando sincronización de manuales (dry_run={dry_run}, force={force})")
    logger.info("=" * 60)

    if not MANUALES_DIR.exists():
        logger.error(f"El directorio de manuales no existe: {MANUALES_DIR}")
        return {"total": 0, "insertados": 0, "actualizados": 0, "omitidos": 0, "errores": 1}

    # Importar base de datos solo cuando no es dry_run
    db_disponible = False
    database = None
    if not dry_run:
        try:
            from app import database as db_mod
            database = db_mod
            # Verificar conectividad
            with database.engine.connect() as conn:
                pass
            db_disponible = True
            logger.info("Conexión con PostgreSQL establecida correctamente.")
        except Exception as e:
            logger.warning(f"Base de datos no accesible en este momento: {e}")
            logger.warning("Ejecutando en modo de verificación e informe.")

    archivos_pdf = sorted(MANUALES_DIR.glob("*.pdf"))
    logger.info(f"Encontrados {len(archivos_pdf)} archivos PDF en {MANUALES_DIR}")

    stats = {
        "total": len(archivos_pdf),
        "insertados": 0,
        "actualizados": 0,
        "omitidos": 0,
        "errores": 0,
        "detalles": []
    }

    for ruta_pdf in archivos_pdf:
        nombre_archivo = ruta_pdf.name
        meta = resolver_metadatos_archivo(nombre_archivo)

        try:
            if dry_run or not db_disponible:
                paginas = extraer_paginas_pdf(ruta_pdf)
                total_chars = sum(len(p[0]) for p in paginas)
                detalle = {
                    "archivo": nombre_archivo,
                    "nombre_legible": meta["nombre_original"],
                    "dispositivo": meta["dispositivo"],
                    "categoria": meta["categoria"],
                    "nivel_acceso": meta["nivel_acceso"],
                    "etiquetas": meta["etiquetas"],
                    "paginas": len(paginas),
                    "caracteres": total_chars
                }
                logger.info(
                    f"[DRY-RUN] {nombre_archivo} -> {meta['nombre_original']} "
                    f"({len(paginas)} págs, {total_chars:,} caracteres, Rol: {meta['nivel_acceso']}) "
                    f"Tags: [{meta['etiquetas'][:40]}...]"
                )
                stats["detalles"].append(detalle)
                stats["insertados"] += 1
                continue

            # Modo real con base de datos conectada
            existente = database.obtener_manual_por_archivo(nombre_archivo)
            if existente:
                if force:
                    paginas = extraer_paginas_pdf(ruta_pdf)
                    database.actualizar_manual(
                        manual_id=existente["id"],
                        dispositivo=meta["dispositivo"],
                        categoria=meta["categoria"],
                        nivel_acceso=meta["nivel_acceso"],
                        etiquetas=meta["etiquetas"],
                        nombre_original=meta.get("nombre_original")
                    )
                    database.actualizar_paginas_manual(existente["id"], paginas)
                    logger.info(f"Actualizado manual ID {existente['id']}: {nombre_archivo} (Tags enriquecidas)")
                    stats["actualizados"] += 1
                else:
                    # Si no tiene etiquetas o tiene etiquetas por defecto 'general, manual', actualizar etiquetas
                    tags_actuales = existente.get("etiquetas") or ""
                    if not tags_actuales.strip() or tags_actuales.strip() in ["general, manual", "dispositivo"]:
                        database.actualizar_manual(
                            manual_id=existente["id"],
                            dispositivo=meta["dispositivo"],
                            categoria=meta["categoria"],
                            nivel_acceso=meta["nivel_acceso"],
                            etiquetas=meta["etiquetas"],
                            nombre_original=meta.get("nombre_original")
                        )
                        logger.info(f"Etiquetas completadas para manual ID {existente['id']}: {nombre_archivo}")
                        stats["actualizados"] += 1
                    else:
                        logger.debug(f"Manual ya existente ID {existente['id']} (sin cambios): {nombre_archivo}")
                        stats["omitidos"] += 1
            else:
                paginas = extraer_paginas_pdf(ruta_pdf)
                nuevo_id = database.insertar_manual(
                    nombre_original=meta["nombre_original"],
                    nombre_archivo=nombre_archivo,
                    dispositivo=meta["dispositivo"],
                    categoria=meta["categoria"],
                    paginas=paginas,
                    nivel_acceso=meta["nivel_acceso"],
                    etiquetas=meta["etiquetas"]
                )
                logger.info(f"Insertado nuevo manual ID {nuevo_id}: {nombre_archivo} ({len(paginas)} págs)")
                stats["insertados"] += 1

            detalle = {
                "archivo": nombre_archivo,
                "nombre_legible": meta["nombre_original"],
                "dispositivo": meta["dispositivo"],
                "categoria": meta["categoria"],
                "nivel_acceso": meta["nivel_acceso"],
                "etiquetas": meta["etiquetas"]
            }
            stats["detalles"].append(detalle)

        except Exception as e:
            logger.error(f"Error procesando {nombre_archivo}: {e}")
            stats["errores"] += 1

    # Sincronizar también etiquetas en vídeos de YouTube
    if db_disponible and database:
        sincronizar_etiquetas_videos(database)

    logger.info("=" * 60)
    logger.info(
        f"Resumen de sincronización: Total={stats['total']}, "
        f"Insertados={stats['insertados']}, Actualizados={stats['actualizados']}, "
        f"Omitidos={stats['omitidos']}, Errores={stats['errores']}"
    )
    logger.info("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Sincronizador de manuales para Buscador de Manuales")
    parser.add_argument("--dry-run", action="store_true", help="Simula la sincronización sin escribir en la base de datos")
    parser.add_argument("--force", action="store_true", help="Fuerza la re-extracción y actualización de páginas existentes")
    args = parser.parse_args()

    sincronizar_manuales(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
