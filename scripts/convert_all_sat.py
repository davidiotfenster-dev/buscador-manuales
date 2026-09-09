import os
import subprocess
from pathlib import Path

sat_dir = Path("nuevo/DOCUMENTACIÓN SAT").resolve()
converted_dir = Path("scratch/converted_pdfs").resolve()
converted_dir.mkdir(parents=True, exist_ok=True)

# List of files and metadata:
# (rel_path, target_pdf_name, dispositivo, categoria, nivel_acceso, etiquetas)
DOCS_METADATA = [
    (
        "APPs/SOPORTE APPs TECNICO DOCUMENTO.docx",
        "SOPORTE_APPs_TECNICO_DOCUMENTO.pdf",
        "TODOS",
        "Soporte SAT",
        "tecnico",
        "apps, mysmartwindow, greenteq wave, icon smart home, konect, arquitectura, core comun, soporte tecnico"
    ),
    (
        "APPs/IoT_FENSTER_Apps_Technical_Documentation.docx",
        "IoT_FENSTER_Apps_Technical_Documentation.pdf",
        "TODOS",
        "Soporte SAT",
        "tecnico",
        "apps, english, mysmartwindow, greenteq wave, icon smart home, konect, architecture, shared core"
    ),
    (
        "CONNECTIVIDAD/CONECTIVIDAD REQUISITOS.docx",
        "CONECTIVIDAD_REQUISITOS.pdf",
        "TODOS",
        "Conectividad y Red",
        "tecnico",
        "wifi, cgnat, router, red 2.4ghz, wpa2, dhcp, puertos, conectividad, soporte"
    ),
    (
        "CONNECTIVIDAD/Conectivity.docx",
        "Conectivity_Requirements.pdf",
        "TODOS",
        "Conectividad y Red",
        "tecnico",
        "wifi, cgnat, router, 2.4ghz, wpa2, dhcp, ports, connectivity, english"
    ),
    (
        "DENOMINACIÓN DISPOSITIVOS/DENOMINACIÓN DE MARCAS Y DISPOSITIVOS.docx",
        "DENOMINACION_DE_MARCAS_Y_DISPOSITIVOS.pdf",
        "TODOS",
        "Denominación y Marcas",
        "publico",
        "marcas, denominacion, connect-1, connect-2, c-wall, c-pulsar, wave-1, wave-2, wave wall, wave4, icon1, icon2, essential+, sentry, solven, vbh, procomsa"
    ),
    (
        "DENOMINACIÓN DISPOSITIVOS/NAMED english.docx",
        "BRAND_AND_DEVICE_NAMING.pdf",
        "TODOS",
        "Denominación y Marcas",
        "publico",
        "brands, naming, connect-1, connect-2, c-wall, c-pulsar, wave-1, wave-2, wave wall, wave4, icon1, icon2, english"
    ),
    (
        "MODOS DISPOSITIVOS/MODOS DISPOSITIVOS.docx",
        "MODOS_DISPOSITIVOS.pdf",
        "TODOS",
        "Modos y Reset",
        "tecnico",
        "modo fabrica, factory mode, reset, hard reset, parpadeo led, connect-1, connect-2, c-pulsar, c-wall, vinculacion"
    ),
    (
        "MODOS DISPOSITIVOS/Technical Specifications for Device Operation and Pairing.docx",
        "Technical_Specifications_Device_Operation_and_Pairing.pdf",
        "TODOS",
        "Modos y Reset",
        "tecnico",
        "factory mode, reset, hard reset, led status, connect-1, connect-2, c-pulsar, c-wall, pairing, english"
    ),
    (
        "Problemas- soluciones.xlsx",
        "Problemas_y_Soluciones_SAT.pdf",
        "TODOS",
        "Problemas y Soluciones",
        "tecnico",
        "problemas, soluciones, sat, no enciende, no sube persiana, pulsador sin sensibilidad, parpadea, modo candado, rele, final de carrera, ruido electrico"
    ),
    (
        "VINCULACIÓN DE DISPOSITIVOS/Manual de vinculación.docx",
        "Manual_de_vinculacion_MySmartWindow.pdf",
        "TODOS",
        "Vinculación y Emparejamiento",
        "publico",
        "vinculacion, multicast, multivinculacion, punto a punto, modo ap, asistente app, emparejamiento, wifi"
    ),
    (
        "VINCULACIÓN DE DISPOSITIVOS/vinculacion.docx",
        "Linking_Manual_MySmartWindow.pdf",
        "TODOS",
        "Vinculación y Emparejamiento",
        "publico",
        "linking, pairing, multicast, multi-linking, point to point, ap mode, app method, english"
    ),
    (
        "ENLACES VIDEOS/ENLACES DE LOS VIDEOS DE YOUTUBE.docx",
        "ENLACES_DE_LOS_VIDEOS_DE_YOUTUBE.pdf",
        "TODOS",
        "Vídeos y Tutoriales",
        "publico",
        "videos, tutoriales, youtube, enlaces, instalacion, reset, configuracion, router, vinculacion, italiano"
    )
]

print("Converting documents...")

# Convert docx files via Word COM
word_docs = [m for m in DOCS_METADATA if m[0].endswith(".docx")]
for rel_path, pdf_name, _, _, _, _ in word_docs:
    src_file = sat_dir / rel_path
    dst_pdf = converted_dir / pdf_name
    print(f"Converting DOCX: {rel_path} -> {pdf_name}")
    cmd = f'''
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {{
    $doc = $word.Documents.Open("{str(src_file)}")
    $doc.SaveAs([ref]"{str(dst_pdf)}", [ref]17)
    $doc.Close()
    Write-Output "OK"
}} catch {{
    Write-Output "ERROR: $($_.Exception.Message)"
}} finally {{
    $word.Quit()
}}
'''
    res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    out = res.stdout.strip()
    if "OK" in out and dst_pdf.exists():
        print(f"  -> Generated: {pdf_name} ({dst_pdf.stat().st_size:,} bytes)")
    else:
        print(f"  -> Failed: {out} {res.stderr}")

# Convert xlsx files via Excel COM
xlsx_docs = [m for m in DOCS_METADATA if m[0].endswith(".xlsx")]
for rel_path, pdf_name, _, _, _, _ in xlsx_docs:
    src_file = sat_dir / rel_path
    dst_pdf = converted_dir / pdf_name
    print(f"Converting XLSX: {rel_path} -> {pdf_name}")
    cmd = f'''
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {{
    $wb = $excel.Workbooks.Open("{str(src_file)}")
    $wb.ExportAsFixedFormat(0, "{str(dst_pdf)}")
    $wb.Close($false)
    Write-Output "OK"
}} catch {{
    Write-Output "ERROR: $($_.Exception.Message)"
}} finally {{
    $excel.Quit()
}}
'''
    res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    out = res.stdout.strip()
    if "OK" in out and dst_pdf.exists():
        print(f"  -> Generated: {pdf_name} ({dst_pdf.stat().st_size:,} bytes)")
    else:
        print(f"  -> Failed: {out} {res.stderr}")

print("All conversions finished!")
