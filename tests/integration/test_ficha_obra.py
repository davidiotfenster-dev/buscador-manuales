"""La ficha de una obra: qué le pasó antes a ese sitio, contra PostgreSQL real.

De las 10 obras del histórico con más de una incidencia, **nueve tienen
problemas de grupos distintos**. Lo que se repite no es la avería, es la obra:
el sitio que dio guerra hace tres semanas vuelve a llamar por otra cosa. Esa
información ya estaba en la base de datos y no la veía nadie durante la
llamada.

Por eso la ficha enseña el historial entero y marca aparte si además se repite
el mismo grupo, que es la pregunta rápida. Si solo enseñara las coincidencias
de grupo, se callaría en nueve de cada diez casos en los que tiene algo que
decir.

Se omiten automáticamente si PostgreSQL no está accesible.
"""

from app import database


def _ticket(db, **extra):
    datos = {
        "instalador": "Marta Gil",
        "obra": "13282",
        "dispositivo": "Connect-1",
        "sintoma": "No vincula",
        "estado": "en_espera",
    }
    datos.update(extra)
    return database.crear_ticket_sat(db, datos)


def _numeros(ficha):
    return [i["numero_ticket"] for i in ficha["incidencias"]]


def test_una_obra_sin_antecedentes_no_es_un_error(db):
    """Es la respuesta más frecuente, no un fallo: total 0 y a seguir."""
    ficha = database.obtener_ficha_obra(db, "no-existe")

    assert ficha["total"] == 0
    assert ficha["incidencias"] == []
    assert ficha["ya_paso_lo_mismo"] is False


def test_reune_las_incidencias_de_la_misma_obra(db):
    _ticket(db, obra="13282", sintoma="Primera")
    _ticket(db, obra="13282", sintoma="Segunda")
    _ticket(db, obra="99999", sintoma="De otra obra")

    ficha = database.obtener_ficha_obra(db, "13282")

    assert ficha["total"] == 2
    assert {i["sintoma"] for i in ficha["incidencias"]} == {"Primera", "Segunda"}


def test_la_obra_se_compara_normalizada(db):
    """El campo es texto libre y lo rellena una persona al teléfono. Comparar
    en crudo partiría el historial de una obra en dos sin que nadie lo notara."""
    _ticket(db, obra="13282")
    _ticket(db, obra="  13282  ")

    assert database.obtener_ficha_obra(db, "13282")["total"] == 2
    assert database.obtener_ficha_obra(db, " 13282 ")["total"] == 2


def test_la_obra_se_compara_sin_mayusculas(db):
    _ticket(db, obra="OB-77")

    assert database.obtener_ficha_obra(db, "ob-77")["total"] == 1


def test_una_obra_vacia_no_agrupa_a_todos_los_que_no_la_tienen(db):
    """40 de las 119 incidencias no traen obra. Si la cadena vacía casara
    consigo misma, la ficha de cualquiera de ellas mostraría las otras 39
    como antecedentes de un sitio que no tienen en común."""
    _ticket(db, obra="")
    _ticket(db, obra="   ")

    assert database.obtener_ficha_obra(db, "")["total"] == 0
    assert database.obtener_ficha_obra(db, "   ")["total"] == 0


def test_grupos_distintos_no_son_lo_mismo(db):
    """El caso de 9 de las 10 obras reales que repiten: la obra vuelve a
    llamar, pero por otra cosa. Hay antecedentes y no hay repetición."""
    _ticket(db, obra="13929", grupo="CONECTIVIDAD")
    _ticket(db, obra="13929", grupo="GESTUAL")

    ficha = database.obtener_ficha_obra(db, "13929")

    assert ficha["total"] == 2
    assert ficha["ya_paso_lo_mismo"] is False
    assert ficha["grupos_repetidos"] == []
    assert {g["code"] for g in ficha["grupos"]} == {"CONECTIVIDAD", "GESTUAL"}


def test_el_mismo_grupo_dos_veces_si_se_marca(db):
    """El caso de la obra 14257: dos veces CONECTIVIDAD."""
    _ticket(db, obra="14257", grupo="CONECTIVIDAD")
    _ticket(db, obra="14257", grupo="CONECTIVIDAD")

    ficha = database.obtener_ficha_obra(db, "14257")

    assert ficha["ya_paso_lo_mismo"] is True
    assert ficha["grupos_repetidos"] == ["CONECTIVIDAD"]


def test_el_ticket_que_se_mira_no_cuenta_como_antecedente(db):
    """La ficha responde a «¿qué hubo ANTES?». Contarse a sí mismo la haría
    decir siempre que hay antecedentes, que es lo mismo que no decir nada."""
    actual = _ticket(db, obra="13282")

    ficha = database.obtener_ficha_obra(db, "13282", excluir_ticket_id=actual.id)

    assert ficha["total"] == 0


def test_desde_el_ticket_la_repeticion_se_mide_contra_su_grupo(db):
    """Vista desde un ticket, la pregunta no es si la obra repite por su
    cuenta, sino si repite **lo de ahora**."""
    _ticket(db, obra="13282", grupo="CONECTIVIDAD")
    _ticket(db, obra="13282", grupo="GESTUAL")
    actual = _ticket(db, obra="13282", grupo="GESTUAL")

    ficha = database.obtener_ficha_obra_de_ticket(db, actual.id)

    assert ficha["total"] == 2
    assert ficha["ya_paso_lo_mismo"] is True
    assert [i["grupo"] for i in ficha["mismo_grupo"]] == ["GESTUAL"]


def test_un_ticket_sin_grupo_no_inventa_coincidencias(db):
    _ticket(db, obra="13282", grupo="CONECTIVIDAD")
    actual = _ticket(db, obra="13282")

    ficha = database.obtener_ficha_obra_de_ticket(db, actual.id)

    assert ficha["total"] == 1
    assert ficha["mismo_grupo"] == []
    assert ficha["ya_paso_lo_mismo"] is False


def test_lo_mas_reciente_va_primero(db):
    """En una llamada se mira la primera línea; tiene que ser la última vez."""
    primera = _ticket(db, obra="13282", sintoma="La vieja")
    segunda = _ticket(db, obra="13282", sintoma="La nueva")

    ficha = database.obtener_ficha_obra(db, "13282")

    assert _numeros(ficha)[0] == segunda.numero_ticket
    assert _numeros(ficha)[1] == primera.numero_ticket


def test_cada_antecedente_dice_como_acabo(db):
    """Una lista de fechas no sirve de nada: lo que cambia el diagnóstico es
    si aquello se resolvió y con qué."""
    anterior = _ticket(db, obra="13282", grupo="CONECTIVIDAD", estado="resuelto",
                       solucion="Llamada, Videos")
    database.registrar_cierre_tecnico(db, anterior.id, {
        "cierre_resuelto": True,
        "cierre_doc_suficiente": False,
        "cierre_descripcion": "Hubo que cambiar el firmware",
    }, "tecnico@empresa.com")

    incidencia = database.obtener_ficha_obra(db, "13282")["incidencias"][0]

    assert incidencia["estado"] == "resuelto"
    assert incidencia["resuelto"] is True
    assert incidencia["documentacion_suficiente"] is False
    assert "Videos" in incidencia["solucion"]


def test_el_limite_acota_el_historial(db):
    for n in range(5):
        _ticket(db, obra="13282", sintoma=f"Incidencia {n}")

    ficha = database.obtener_ficha_obra(db, "13282", limite=3)

    assert ficha["total"] == 3
