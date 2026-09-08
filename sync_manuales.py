"""
Script de sincronización e indexación automática de manuales para Buscador de Manuales.
Escanea la carpeta 'manuales/', extrae el texto de cada página e inserta o actualiza
los registros en PostgreSQL con metadatos técnicos enriquecidos y niveles de acceso (RBAC).

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

# Catálogo canónico de metadatos para manuales del sistema
CATALOGO_MANUALES: Dict[str, Dict[str, Any]] = {
    # --- 1. Documentación Técnica SAT (Procedente de nuevo/DOCUMENTACIÓN SAT) ---
    "Problemas_y_Soluciones_SAT.pdf": {
        "nombre_original": "Guía de Problemas y Soluciones SAT.pdf",
        "dispositivo": "TODOS",
        "categoria": "Problemas y Soluciones",
        "nivel_acceso": "tecnico",
        "etiquetas": "sat, averias, soluciones, no enciende, pulsador insensible, cable cortado, parpadea constante, modo candado, rele, final de carrera, ruido electrico, se mueven solas, invertir controles"
    },
    "SOPORTE_APPs_TECNICO_DOCUMENTO.pdf": {
        "nombre_original": "Soporte Técnico Apps IoT Fenster.pdf",
        "dispositivo": "TODOS",
        "categoria": "Soporte SAT",
        "nivel_acceso": "tecnico",
        "etiquetas": "apps, arquitectura, core comun, mysmartwindow, greenteq wave, icon smart home, konect, unificado, soporte tecnico"
    },
    "IoT_FENSTER_Apps_Technical_Documentation.pdf": {
        "nombre_original": "IoT Fenster Apps Technical Documentation (English).pdf",
        "dispositivo": "TODOS",
        "categoria": "Soporte SAT",
        "nivel_acceso": "tecnico",
        "etiquetas": "apps, shared core, mysmartwindow, greenteq wave, icon smart home, konect, architecture, unified support, english"
    },
    "CONECTIVIDAD_REQUISITOS.pdf": {
        "nombre_original": "Requisitos de Conectividad, WiFi y CGNAT.pdf",
        "dispositivo": "TODOS",
        "categoria": "Conectividad y Red",
        "nivel_acceso": "tecnico",
        "etiquetas": "wifi, cgnat, router, 2.4ghz, wpa2, wpa3, dhcp, puertos, mqtt 8883, aislamiento de clientes, ap isolation, wmf, digi plus, masmovil, ip publica"
    },
    "Conectivity_Requirements.pdf": {
        "nombre_original": "Connectivity Requirements and CGNAT (English).pdf",
        "dispositivo": "TODOS",
        "categoria": "Conectividad y Red",
        "nivel_acceso": "tecnico",
        "etiquetas": "wifi, connectivity, cgnat, router, 2.4ghz, wpa2, client isolation, ap isolation, wmf, ports, english"
    },
    "DENOMINACION_DE_MARCAS_Y_DISPOSITIVOS.pdf": {
        "nombre_original": "Denominación de Marcas y Dispositivos.pdf",
        "dispositivo": "TODOS",
        "categoria": "Denominación y Marcas",
        "nivel_acceso": "publico",
        "etiquetas": "marcas, equivalencias, connect-1, connect-2, c-wall, c-pulsar, wave-1, wave-2, wave 3, wave4, icon1, icon2, icon3, icon mini, essential+, sentry, blickdomi, solven, vbh, procomsa, kommerling, evo, sense"
    },
    "BRAND_AND_DEVICE_NAMING.pdf": {
        "nombre_original": "Brand and Device Naming Guide (English).pdf",
        "dispositivo": "TODOS",
        "categoria": "Denominación y Marcas",
        "nivel_acceso": "publico",
        "etiquetas": "brands, naming, connect-1, connect-2, c-wall, c-pulsar, wave-1, wave-2, wave3, wave4, icon1, icon2, essential+, sentry, solven, vbh, procomsa, english"
    },
    "MODOS_DISPOSITIVOS.pdf": {
        "nombre_original": "Modos de Dispositivos y Procedimientos de Reset.pdf",
        "dispositivo": "TODOS",
        "categoria": "Modos y Reset",
        "nivel_acceso": "tecnico",
        "etiquetas": "modo fabrica, factory mode, reset simple, hard reset, parpadeo led 2s, connect-1, connect-2, c-wall, c-pulsar, evo, sense, ventana 60 minutos, led verde, pulsar 8s"
    },
    "Technical_Specifications_Device_Operation_and_Pairing.pdf": {
        "nombre_original": "Device Operation and Pairing Specifications (English).pdf",
        "dispositivo": "TODOS",
        "categoria": "Modos y Reset",
        "nivel_acceso": "tecnico",
        "etiquetas": "factory mode, reset, hard reset, led status, connect-1, connect-2, c-wall, c-pulsar, pairing, english"
    },
    "Manual_de_vinculacion_MySmartWindow.pdf": {
        "nombre_original": "Manual de Vinculación MySmartWindow.pdf",
        "dispositivo": "TODOS",
        "categoria": "Vinculación y Emparejamiento",
        "nivel_acceso": "publico",
        "etiquetas": "vinculacion, emparejamiento, multivinculacion, multicast, punto a punto, modo ap, red bdsmart, metodo app, asistente app, wifi"
    },
    "Linking_Manual_MySmartWindow.pdf": {
        "nombre_original": "Linking Manual MySmartWindow (English).pdf",
        "dispositivo": "TODOS",
        "categoria": "Vinculación y Emparejamiento",
        "nivel_acceso": "publico",
        "etiquetas": "linking, pairing, multi-linking, multicast, point to point, ap mode, bdsmart, app method, english"
    },
    "ENLACES_DE_LOS_VIDEOS_DE_YOUTUBE.pdf": {
        "nombre_original": "Enlaces y Soluciones en Vídeo YouTube.pdf",
        "dispositivo": "TODOS",
        "categoria": "Vídeos y Tutoriales",
        "nivel_acceso": "publico",
        "etiquetas": "videos, tutoriales, youtube, enlaces, instalacion, reset, configuracion, router, orange, jazztel, vinculacion, multiwifi, tareas offline, alexa, google home, ifttt, italiano"
    },

    # --- 2. Manuales Originales de Dispositivos y FAQs ---
    "Connect-1_Documentacion_MySmartWindow.pdf": {
        "nombre_original": "Documentación Funcional Connect-1.pdf",
        "dispositivo": "CONNECT-1",
        "categoria": "Manuales de Dispositivos",
        "nivel_acceso": "publico",
        "etiquetas": "connect-1, wave-1, icon1, essential+, marco ventana, pulsador capacitivo, persiana, toldo, veneciana, calibracion, reset"
    },
    "Connect-2_Documentacion_MySmartWindow.pdf": {
        "nombre_original": "Documentación Funcional Connect-2.pdf",
        "dispositivo": "CONNECT-2",
        "categoria": "Manuales de Dispositivos",
        "nivel_acceso": "publico",
        "etiquetas": "connect-2, wave-2, icon2, sentry, tres botones, calidad del aire, co2, voc, alerta efraccion, alerta apertura, veneciana con lamas, instalacion"
    },
    "C-PULSAR_Documentacion_MySmartWindow.pdf": {
        "nombre_original": "Documentación Funcional C-PULSAR.pdf",
        "dispositivo": "C-PULSAR",
        "categoria": "Manuales de Dispositivos",
        "nivel_acceso": "publico",
        "etiquetas": "c-pulsar, wave4, icon mini, pulsador inalambrico, modulo cajon, boton retroiluminado, pila cr2032, radiofrecuencia, reset 8s"
    },
    "C-Wall_Documentacion_MySmartWindow.pdf": {
        "nombre_original": "Documentación Funcional C-Wall.pdf",
        "dispositivo": "C-WALL",
        "categoria": "Manuales de Dispositivos",
        "nivel_acceso": "publico",
        "etiquetas": "c-wall, wave 3, icon3, pulse, interruptor pared, boton central, escena general apagado, caja 60mm, wifi 6, bluetooth"
    },
    "Preguntas-frecuentes-MySmartWindow-1.pdf": {
        "nombre_original": "Preguntas Frecuentes Motores y Compatibilidad.pdf",
        "dispositivo": "TODOS",
        "categoria": "Manuales de Usuario",
        "nivel_acceso": "publico",
        "etiquetas": "faq, preguntas frecuentes, motores, mecanicos, electronicos, via radio, 4 cables, 4 hilos, somfy, cherubini, becker, compatibilidad"
    },
    "6b1a3a47-ec60-4b7c-b438-7426a8f8cb32_Contraseas_Wifi.pdf": {
        "nombre_original": "Documentación de Redes WiFi y Laboratorio.pdf",
        "dispositivo": "TODOS",
        "categoria": "Conectividad y Red",
        "nivel_acceso": "tecnico",
        "etiquetas": "wifi, redes, contrasenas, credenciales, laboratorio, ssid, taller"
    }
}


def extraer_paginas_pdf(ruta_pdf: Path) -> List[Tuple[str, bool]]:
    """Extrae el texto de cada página de un PDF eliminando caracteres nulos."""
    reader = PdfReader(str(ruta_pdf))
    paginas = []
    for i, pagina in enumerate(reader.pages, start=1):
        txt = (pagina.extract_text() or "").replace("\x00", "")
        paginas.append((txt, False))
    return paginas


def sincronizar_manuales(dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
    """
    Sincroniza todos los PDFs presentes en 'manuales/' con la base de datos PostgreSQL.
    """
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

        # Ignorar archivos duplicados temporales tipo '*_1.pdf', '*_2.pdf' si el base existe
        # a menos que sean los únicos
        meta = CATALOGO_MANUALES.get(nombre_archivo)
        if not meta:
            # Buscar si existe versión canónica sin sufijo _1, _2
            nombre_base = nombre_archivo
            for sufijo in ["_1.pdf", "_2.pdf", "_3.pdf"]:
                if nombre_archivo.endswith(sufijo):
                    nombre_base = nombre_archivo[:-len(sufijo)] + ".pdf"
                    break
            meta = CATALOGO_MANUALES.get(nombre_base)

        if not meta:
            # Generar metadatos por defecto basados en el nombre
            meta = {
                "nombre_original": nombre_archivo.replace("_", " "),
                "dispositivo": "TODOS",
                "categoria": "Manuales Técnicos",
                "nivel_acceso": "publico",
                "etiquetas": "general, manual"
            }

        try:
            paginas = extraer_paginas_pdf(ruta_pdf)
            total_chars = sum(len(p[0]) for p in paginas)
            
            detalle = {
                "archivo": nombre_archivo,
                "nombre_legible": meta["nombre_original"],
                "dispositivo": meta["dispositivo"],
                "categoria": meta["categoria"],
                "nivel_acceso": meta["nivel_acceso"],
                "paginas": len(paginas),
                "caracteres": total_chars
            }

            if dry_run or not db_disponible:
                logger.info(
                    f"[DRY-RUN] {nombre_archivo} -> {meta['nombre_original']} "
                    f"({len(paginas)} págs, {total_chars:,} caracteres, Rol: {meta['nivel_acceso']})"
                )
                stats["detalles"].append(detalle)
                stats["insertados"] += 1
                continue

            # Modo real con base de datos conectada
            existente = database.obtener_manual_por_archivo(nombre_archivo)
            if existente:
                if force:
                    database.actualizar_manual(
                        manual_id=existente["id"],
                        dispositivo=meta["dispositivo"],
                        categoria=meta["categoria"],
                        nivel_acceso=meta["nivel_acceso"],
                        etiquetas=meta["etiquetas"]
                    )
                    database.actualizar_paginas_manual(existente["id"], paginas)
                    logger.info(f"Actualizado manual ID {existente['id']}: {nombre_archivo}")
                    stats["actualizados"] += 1
                else:
                    logger.info(f"Manual ya existente ID {existente['id']} (sin cambios): {nombre_archivo}")
                    stats["omitidos"] += 1
            else:
                nuevo_id = database.insertar_manual(
                    nombre_original=meta["nombre_original"],
                    nombre_archivo=nombre_archivo,
                    dispositivo=meta["dispositivo"],
                    categoria=meta["categoria"],
                    paginas=paginas,
                    nivel_acceso=meta["nivel_acceso"],
                    etiquetas=meta["etiquetas"]
                )
                logger.info(f"Registrado nuevo manual ID {nuevo_id}: {nombre_archivo} ({len(paginas)} págs)")
                stats["insertados"] += 1

            stats["detalles"].append(detalle)

        except Exception as e:
            logger.error(f"Error procesando {nombre_archivo}: {e}")
            stats["errores"] += 1

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
