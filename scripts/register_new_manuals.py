import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pypdf import PdfReader
from app import database
MANUALES_DIR = BASE_DIR / "manuales"
MANUALES_DIR.mkdir(parents=True, exist_ok=True)
CONVERTED_DIR = BASE_DIR / "scratch" / "converted_pdfs"

MANUALS_TO_REGISTER = [
    {
        "filename": "SOPORTE_APPs_TECNICO_DOCUMENTO.pdf",
        "nombre_original": "Soporte Técnico Apps IoT Fenster.pdf",
        "dispositivo": "TODOS",
        "categoria": "Soporte SAT",
        "nivel_acceso": "tecnico",
        "etiquetas": "apps, mysmartwindow, greenteq wave, icon smart home, konect, arquitectura, soporte sat"
    },
    {
        "filename": "IoT_FENSTER_Apps_Technical_Documentation.pdf",
        "nombre_original": "IoT Fenster Apps Technical Documentation.pdf",
        "dispositivo": "TODOS",
        "categoria": "Soporte SAT",
        "nivel_acceso": "tecnico",
        "etiquetas": "apps, english, mysmartwindow, greenteq wave, icon smart home, konect, architecture, sat"
    },
    {
        "filename": "CONECTIVIDAD_REQUISITOS.pdf",
        "nombre_original": "Requisitos de Conectividad y CGNAT.pdf",
        "dispositivo": "TODOS",
        "categoria": "Conectividad y Red",
        "nivel_acceso": "tecnico",
        "etiquetas": "wifi, cgnat, router, 2.4ghz, wpa2, puertos, aislamiento clientes, sat, red"
    },
    {
        "filename": "Conectivity_Requirements.pdf",
        "nombre_original": "Connectivity Requirements and CGNAT.pdf",
        "dispositivo": "TODOS",
        "categoria": "Conectividad y Red",
        "nivel_acceso": "tecnico",
        "etiquetas": "wifi, cgnat, router, 2.4ghz, wpa2, ports, english, connectivity"
    },
    {
        "filename": "DENOMINACION_DE_MARCAS_Y_DISPOSITIVOS.pdf",
        "nombre_original": "Denominación de Marcas y Dispositivos.pdf",
        "dispositivo": "TODOS",
        "categoria": "Denominación y Marcas",
        "nivel_acceso": "publico",
        "etiquetas": "marcas, denominacion, connect-1, connect-2, c-wall, c-pulsar, wave-1, wave-2, wave wall, wave4, icon1, icon2, essential+, sentry, solven, vbh, procomsa"
    },
    {
        "filename": "BRAND_AND_DEVICE_NAMING.pdf",
        "nombre_original": "Brand and Device Naming Guide.pdf",
        "dispositivo": "TODOS",
        "categoria": "Denominación y Marcas",
        "nivel_acceso": "publico",
        "etiquetas": "brands, naming, connect-1, connect-2, c-wall, c-pulsar, wave-1, wave-2, wave wall, wave4, icon1, icon2, english"
    },
    {
        "filename": "MODOS_DISPOSITIVOS.pdf",
        "nombre_original": "Modos de Dispositivos y Reset.pdf",
        "dispositivo": "TODOS",
        "categoria": "Modos y Reset",
        "nivel_acceso": "tecnico",
        "etiquetas": "modo fabrica, factory mode, reset, hard reset, parpadeo led, connect-1, connect-2, c-pulsar, c-wall, vinculacion"
    },
    {
        "filename": "Technical_Specifications_Device_Operation_and_Pairing.pdf",
        "nombre_original": "Technical Specifications Device Operation and Pairing.pdf",
        "dispositivo": "TODOS",
        "categoria": "Modos y Reset",
        "nivel_acceso": "tecnico",
        "etiquetas": "factory mode, reset, hard reset, led status, connect-1, connect-2, c-pulsar, c-wall, pairing, english"
    },
    {
        "filename": "Problemas_y_Soluciones_SAT.pdf",
        "nombre_original": "Guía de Problemas y Soluciones SAT.pdf",
        "dispositivo": "TODOS",
        "categoria": "Problemas y Soluciones",
        "nivel_acceso": "tecnico",
        "etiquetas": "problemas, soluciones, sat, no enciende, no sube persiana, pulsador sin sensibilidad, parpadea, modo candado, rele, final de carrera, ruido electrico"
    },
    {
        "filename": "Manual_de_vinculacion_MySmartWindow.pdf",
        "nombre_original": "Manual de Vinculación MySmartWindow.pdf",
        "dispositivo": "TODOS",
        "categoria": "Vinculación y Emparejamiento",
        "nivel_acceso": "publico",
        "etiquetas": "vinculacion, multicast, multivinculacion, punto a punto, modo ap, asistente app, emparejamiento, wifi"
    },
    {
        "filename": "Linking_Manual_MySmartWindow.pdf",
        "nombre_original": "Linking Manual MySmartWindow.pdf",
        "dispositivo": "TODOS",
        "categoria": "Vinculación y Emparejamiento",
        "nivel_acceso": "publico",
        "etiquetas": "linking, pairing, multicast, multi-linking, point to point, ap mode, app method, english"
    },
    {
        "filename": "ENLACES_DE_LOS_VIDEOS_DE_YOUTUBE.pdf",
        "nombre_original": "Enlaces y Soluciones en Vídeo YouTube.pdf",
        "dispositivo": "TODOS",
        "categoria": "Vídeos y Tutoriales",
        "nivel_acceso": "publico",
        "etiquetas": "videos, tutoriales, youtube, enlaces, instalacion, reset, configuracion, router, vinculacion, italiano, soporte"
    }
]

registered_count = 0
for item in MANUALS_TO_REGISTER:
    src = CONVERTED_DIR / item["filename"]
    dest = MANUALES_DIR / item["filename"]
    
    if not src.exists():
        print(f"ERROR: Source file {src} does not exist!")
        continue
        
    # Copy to manuales directory
    shutil.copy2(src, dest)
    
    # Extract pages
    reader = PdfReader(str(dest))
    paginas = []
    for p in reader.pages:
        txt = (p.extract_text() or "").replace("\x00", "")
        paginas.append((txt, False))
        
    # Check if existing in DB
    existing = database.obtener_manual_por_archivo(item["filename"])
    if existing:
        print(f"Updating existing manual ID {existing['id']}: {item['filename']}")
        database.actualizar_manual(
            manual_id=existing["id"],
            dispositivo=item["dispositivo"],
            categoria=item["categoria"],
            nivel_acceso=item["nivel_acceso"],
            etiquetas=item["etiquetas"]
        )
        database.actualizar_paginas_manual(existing["id"], paginas)
        registered_count += 1
    else:
        new_id = database.insertar_manual(
            nombre_original=item["nombre_original"],
            nombre_archivo=item["filename"],
            dispositivo=item["dispositivo"],
            categoria=item["categoria"],
            paginas=paginas,
            nivel_acceso=item["nivel_acceso"],
            etiquetas=item["etiquetas"]
        )
        print(f"Registered NEW manual ID {new_id}: {item['nombre_original']} ({len(paginas)} pages)")
        registered_count += 1

print(f"\nTotal manuals registered/updated: {registered_count}")
