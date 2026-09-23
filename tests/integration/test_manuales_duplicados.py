"""Deduplicación de manuales por contenido, contra PostgreSQL real.

De los 28 manuales que llegó a haber, 10 eran copias byte a byte de otros 5 —
siete de ellas del mismo PDF de wifi. El nombre del fichero no impedía nada:
subir dos veces el mismo documento con nombres distintos creaba dos manuales, y
la búsqueda devolvía el mismo resultado repetido.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

import pytest

from app import database


PDF_A = b"%PDF-1.4 contenido A"
PDF_B = b"%PDF-1.4 contenido B"


def _insertar(db, nombre_original: str, nombre_archivo: str, datos=None) -> int:
    """Inserta por ORM sobre la sesión de pruebas.

    database.insertar_manual() abre su propia sesión contra el engine del
    módulo, que apunta a la base de desarrollo, no a la de pruebas.
    """
    manual = database.Manual(
        nombre_original=nombre_original,
        nombre_archivo=nombre_archivo,
        dispositivo="TODOS",
        categoria="general",
        num_paginas=1,
        contenido_hash=database.calcular_hash_contenido(datos) if datos else None,
    )
    db.add(manual)
    db.commit()
    return manual.id


def test_el_hash_no_depende_del_nombre_del_fichero(db):
    """Es lo único que identifica de verdad un documento."""
    assert database.calcular_hash_contenido(PDF_A) == database.calcular_hash_contenido(PDF_A)
    assert database.calcular_hash_contenido(PDF_A) != database.calcular_hash_contenido(PDF_B)


def test_encuentra_el_manual_aunque_el_fichero_se_llame_distinto(db):
    """El caso real: 'contraseñaa WIFI.pdf' y 'Contraseas_Wifi_2.pdf' eran el mismo."""
    manual_id = _insertar(db, "Guia de WiFi", "contrasenas_wifi.pdf", PDF_A)

    encontrado = database.obtener_manual_por_hash(database.calcular_hash_contenido(PDF_A), db=db)

    assert encontrado is not None
    assert encontrado["id"] == manual_id
    assert encontrado["nombre_archivo"] == "contrasenas_wifi.pdf"


def test_un_contenido_distinto_no_se_confunde_con_uno_existente(db):
    _insertar(db, "Guia de WiFi", "wifi.pdf", PDF_A)

    assert database.obtener_manual_por_hash(database.calcular_hash_contenido(PDF_B), db=db) is None


def test_hash_vacio_no_devuelve_cualquier_cosa(db):
    """Los manuales anteriores a la columna tienen el hash a NULL.

    Si una cadena vacía casara con ellos, la subida los daría por duplicados de
    cualquier PDF nuevo y no se podría subir nada.
    """
    _insertar(db, "Antiguo sin hash", "antiguo.pdf")

    assert database.obtener_manual_por_hash("", db=db) is None
    assert database.obtener_manual_por_hash(None, db=db) is None


def test_fijar_hash_rellena_los_manuales_antiguos(db):
    """El sincronizador completa el hash de lo que ya estaba dado de alta."""
    manual_id = _insertar(db, "Antiguo sin hash", "antiguo.pdf")
    hash_real = database.calcular_hash_contenido(PDF_A)

    database.fijar_hash_manual(manual_id, hash_real, db=db)

    assert database.obtener_manual_por_hash(hash_real, db=db)["id"] == manual_id


def test_fijar_hash_no_pisa_uno_ya_calculado(db):
    """Solo rellena huecos: reescribirlo enmascararía un fichero cambiado."""
    manual_id = _insertar(db, "Con hash", "con_hash.pdf", PDF_A)

    database.fijar_hash_manual(manual_id, database.calcular_hash_contenido(PDF_B), db=db)

    assert database.obtener_manual_por_hash(database.calcular_hash_contenido(PDF_A), db=db)["id"] == manual_id
    assert database.obtener_manual_por_hash(database.calcular_hash_contenido(PDF_B), db=db) is None


# ---------------------------------------------------------------------
# Metadatos: qué devuelve la consulta que usa el sincronizador
# ---------------------------------------------------------------------

def test_la_consulta_por_archivo_devuelve_categoria_y_etiquetas(db):
    """El sincronizador decide con ellas si al manual le faltan metadatos.

    Al no venir en el diccionario, daba por vacías las etiquetas de **todos** los
    manuales, así que en cada arranque reescribía dispositivo, categoría y nivel
    de acceso de la biblioteca entera: lo que el administrador hubiera elegido al
    subir el PDF se perdía en el siguiente reinicio, sin aviso.
    """
    manual = database.Manual(
        nombre_original="Guía C-Wall",
        nombre_archivo="guia_cwall.pdf",
        dispositivo="C-Wall",
        categoria="instalacion",
        etiquetas="cwall, montaje",
        num_paginas=1,
    )
    db.add(manual)
    db.commit()

    ficha = database.obtener_manual_por_archivo("guia_cwall.pdf", db=db)

    assert ficha["dispositivo"] == "C-Wall"
    assert ficha["categoria"] == "instalacion"
    assert ficha["etiquetas"] == "cwall, montaje"


def test_la_consulta_por_archivo_devuelve_none_si_no_existe(db):
    assert database.obtener_manual_por_archivo("no_existe.pdf", db=db) is None
