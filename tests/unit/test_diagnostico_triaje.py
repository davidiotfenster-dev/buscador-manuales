"""El triaje daba SIEMPRE el mismo diagnóstico, y nadie lo detectó.

La cadena de trece `if/elif` de `evaluar_cuestionario_asistencia` tenía en la
rama 8 esta condición:

    wifi["tipo_red"] in [..., "Dual 2,4/5 GHz"] and wifi["ssid_separados"] == "No"

que son **exactamente** las dos primeras `<option>` de los desplegables de Wi-Fi
del formulario: las que quedan puestas si el técnico no toca ese bloque. Como el
`elif` se evaluaba en orden, cualquier avería —una alarma sin batería incluida—
salía como «Band Steering Activo en Router» con un 92-95 % de confianza, y las
ramas 9 a 13 (calibración, sensores Connect-2, C-Wall, WAlarm y cobertura) eran
inalcanzables salvo cambiando ese desplegable.

Sobrevivió porque los diez tests que había del cuestionario comprobaban que las
respuestas **se guardaban**, nunca qué diagnóstico salía. La lógica de
diagnóstico tenía cobertura cero.

Estos tests fijan lo que importa: que un valor por defecto no decide un
diagnóstico, que sin evidencia se dice que no la hay, y que cada regla sigue
siendo alcanzable.
"""

import copy

import pytest

from app.sat_autoresolver import (
    UMBRAL_DECISION,
    buscar_casos_similares,
    evaluar_cuestionario_asistencia,
    puntuar_reglas,
)


# El envío que produce el formulario cuando el técnico no toca nada: todos los
# desplegables en su primera opción. Es el punto de partida del fallo.
CUESTIONARIO_POR_DEFECTO = {
    "persona": {},
    "partner": "IoT Fenster / MySmartWindow",
    "dispositivo": "Connect-1",
    "num_dispositivos_afectados": "1",
    "area_incidencia": "Dispositivo / electrónica",
    "estado_vinculado": "Sí",
    "estado_app": "Sí",
    "estado_control_fisico": "Sí",
    "estado_control_app": "Sí",
    "sintomas_observados": [],
    "wifi_info": {
        "tipo_red": "Dual 2,4/5 GHz",
        "ssid_separados": "No",
        "generacion": "Wi-Fi 5",
        "seguridad": "WPA2",
        "rssi": "Bueno",
    },
    "app_info": {"mas_de_un_movil": "No probado"},
    "alcance_fisico": {"obstaculos": "Tabiques"},
    "info_especifica": {
        "hw_c1": {
            "controla_persiana": True,
            "motor_responde": True,
            "oyen_reles": True,
            "calib_termina": True,
        },
        "hw_c2": {},
    },
    "momento_fallo": "Durante uso normal",
    "descripcion_detallada": "",
    "acciones_realizadas": [],
}


def cuestionario(**cambios):
    """Copia del envío por defecto con los cambios indicados."""
    datos = copy.deepcopy(CUESTIONARIO_POR_DEFECTO)
    for clave, valor in cambios.items():
        if isinstance(valor, dict) and isinstance(datos.get(clave), dict):
            datos[clave].update(valor)
        else:
            datos[clave] = valor
    return datos


# ── El fallo original ───────────────────────────────────────────────────────

def test_el_formulario_en_blanco_no_diagnostica_band_steering():
    """La regresión exacta: sin tocar nada salía Band Steering al 95 %."""
    r = evaluar_cuestionario_asistencia(cuestionario(), None)
    assert "Band Steering" not in r["diagnostico_titulo"]
    assert r["concluyente"] is False


def test_sin_evidencia_se_dice_que_faltan_datos_y_no_se_afirma_nada():
    r = evaluar_cuestionario_asistencia(cuestionario(), None)
    assert r["concluyente"] is False
    assert "faltan datos" in r["diagnostico_titulo"].lower()
    # Y sobre todo: no se vende como certeza.
    assert r["confianza"] <= 55.0


@pytest.mark.parametrize(
    "descripcion",
    [
        "La persiana no sube ni baja",
        "el sensor de temperatura marca mal",
        "la alarma no suena, la batería está agotada",
        "hace un ruido muy raro al moverse",
    ],
)
def test_averias_distintas_no_pueden_dar_todas_el_mismo_diagnostico(descripcion):
    """Cada una de estas daba «Band Steering» con más de un 92 %."""
    r = evaluar_cuestionario_asistencia(cuestionario(descripcion_detallada=descripcion), None)
    assert "Band Steering" not in r["diagnostico_titulo"]


def test_la_red_por_defecto_no_llega_sola_al_umbral():
    """El corazón del arreglo: una señal que puede venir por defecto no decide.

    La condición de Band Steering sigue existiendo y sigue puntuando, pero pesa
    DÉBIL. Si decidiera por sí sola volveríamos al fallo original.
    """
    ranking = puntuar_reglas({
        "dispositivo": "Connect-1", "partner": "", "area": "", "sintomas": "",
        "wifi": {"tipo_red": "Dual 2,4/5 GHz", "ssid_separados": "No"},
        "wifi_gen": "Wi-Fi 5", "wifi_seg": "WPA2", "app_info": {}, "alcance": {},
        "hw_c1": {}, "hw_c2": {}, "control_fisico": "Sí", "control_app": "Sí",
        "estado_app": "Sí", "num_afectados": "1", "mas_de_un_movil": "No probado",
    })
    band = next(r for r in ranking if r["id"] == "band_steering")
    assert 0 < band["puntuacion"] < UMBRAL_DECISION


# ── Que cada regla siga siendo alcanzable ───────────────────────────────────

@pytest.mark.parametrize(
    "cambios, esperado",
    [
        # Las que antes funcionaban (ramas 1-7), para que no se rompan.
        (
            {"info_especifica": {"hw_c1": {"oyen_reles": True, "motor_responde": False}}},
            "reles_sin_motor",
        ),
        ({"descripcion_detallada": "al dar a bajar sube"}, "inversion_giro"),
        ({"wifi_info": {"seguridad": "WPA3"}}, "wpa3_wifi67"),
        (
            {"num_dispositivos_afectados": "Todos los de la vivienda/instalación"},
            "incidencia_global",
        ),
        (
            {"app_info": {"mas_de_un_movil": "No (Solo en este móvil)"}},
            "disparidad_movil",
        ),
        (
            {"estado_control_fisico": "No", "estado_control_app": "No"},
            "alimentacion_termico",
        ),
        ({"estado_control_app": "No"}, "conectividad_wifi"),
        # Las que eran inalcanzables (ramas 8-13). Este es el segundo fallo.
        (
            {"descripcion_detallada": "la app no descubre el equipo, salen 0 dispositivos"},
            "band_steering",
        ),
        ({"descripcion_detallada": "no calibra, se queda a medias"}, "calibracion"),
        (
            {"dispositivo": "Connect-2", "descripcion_detallada": "el sensor de temperatura falla"},
            "sensores_c2",
        ),
        (
            {"dispositivo": "C-Wall", "descripcion_detallada": "el pulsador no responde al tacto"},
            "cwall",
        ),
        (
            {"dispositivo": "WAlarm", "descripcion_detallada": "la sirena no suena, batería agotada"},
            "walarm",
        ),
        ({"wifi_info": {"rssi": "Muy débil / crítico (< -75 dBm)"}}, "cobertura_rf"),
    ],
)
def test_cada_regla_es_alcanzable(cambios, esperado):
    """Ninguna regla puede quedar tapada por otra que gane siempre."""
    r = evaluar_cuestionario_asistencia(cuestionario(**cambios), None)
    ganadora = r["hipotesis_consideradas"][0]
    assert ganadora["id"] == esperado, (
        f"Se esperaba '{esperado}' y ganó '{ganadora['id']}' "
        f"con {ganadora['puntuacion']} puntos"
    )
    assert r["concluyente"] is True


# ── La confianza tiene que significar algo ──────────────────────────────────

def test_mas_evidencia_da_mas_confianza_que_menos():
    floja = evaluar_cuestionario_asistencia(
        cuestionario(wifi_info={"seguridad": "WPA3"}), None
    )
    fuerte = evaluar_cuestionario_asistencia(
        cuestionario(
            wifi_info={"seguridad": "WPA3", "generacion": "Wi-Fi 6"},
            descripcion_detallada="el router tiene WPA3 y no asocia",
        ),
        None,
    )
    assert fuerte["confianza"] > floja["confianza"]


def test_el_diagnostico_explica_en_que_se_basa():
    """Sin los motivos, el técnico no puede saber si el triaje le ha entendido."""
    r = evaluar_cuestionario_asistencia(
        cuestionario(estado_control_fisico="Sí", estado_control_app="No"), None
    )
    assert r["motivos_diagnostico"]
    assert any("pulsador físico" in m for m in r["motivos_diagnostico"])


def test_se_devuelven_las_hipotesis_descartadas():
    r = evaluar_cuestionario_asistencia(cuestionario(), None)
    assert len(r["hipotesis_consideradas"]) > 1


# ── La base de conocimiento del Excel, que no la leía nadie ─────────────────

def test_los_excel_de_la_base_sat_ya_se_consultan():
    """`cargar_base_conocimiento_sat()` no se llamaba desde ningún sitio.

    Las 119 incidencias reales y las 10 parejas problema-solución eran código
    muerto: se parseaban perfectamente y no las usaba nadie.
    """
    casos = buscar_casos_similares("no sube la persiana cuando se le da la orden", "Connect-1")
    assert casos["problemas_solucion"], "La matriz de problemas-soluciones sigue sin consultarse"
    assert all(c["solucion"] for c in casos["problemas_solucion"])


def test_no_se_devuelve_cualquier_caso_del_mismo_dispositivo_como_parecido():
    """El bono por dispositivo (0,35) no puede bastar para llamarlo «parecido».

    Con el corte anterior salían los mismos tres casos para consultas
    completamente distintas.
    """
    casos = buscar_casos_similares("xyzzy plugh texto que no aparece en ningun caso", "Connect-1")
    assert casos["problemas_solucion"] == []
    assert casos["incidencias_historicas"] == []


def test_el_triaje_devuelve_casos_parecidos_de_verdad():
    r = evaluar_cuestionario_asistencia(
        cuestionario(descripcion_detallada="no sube la persiana cuando se le da la orden"), None
    )
    textos = " ".join(c["problema"].lower() for c in r["casos_similares"]["problemas_solucion"])
    assert "persiana" in textos


# ── La persona, que el cuestionario no preguntaba ──────────────────────────

def test_los_datos_de_la_persona_viajan_al_ticket():
    """El correo es la puerta de entrada: si no llega al ticket, no sirve."""
    r = evaluar_cuestionario_asistencia(
        cuestionario(persona={
            "nombre": "Paco Gómez",
            "correo": "paco@ventanas.example",
            "telefono": "612345678",
            "obra": "Residencial Las Rozas",
        }),
        None,
    )
    prefill = r["ticket_prefill"]
    assert prefill["instalador"] == "Paco Gómez"
    assert prefill["email"] == "paco@ventanas.example"
    assert prefill["telefono"] == "612345678"
    assert prefill["obra"] == "Residencial Las Rozas"


def test_un_cuestionario_sin_persona_no_revienta():
    """Se sigue pudiendo triar sin datos de contacto; simplemente van vacíos."""
    r = evaluar_cuestionario_asistencia(cuestionario(), None)
    assert r["ticket_prefill"]["email"] == ""


def test_sin_diagnostico_concluyente_el_ticket_no_se_prerellena_con_una_causa():
    """Un diagnóstico que no lo es no puede colarse como diagnóstico del ticket."""
    r = evaluar_cuestionario_asistencia(cuestionario(), None)
    assert r["ticket_prefill"]["diagnostico"] == ""


def test_el_excel_de_problemas_soluciones_se_recarga_al_cambiar(tmp_path, monkeypatch):
    """Antes se cargaba una vez: añadir filas no servía hasta reiniciar el servidor."""
    import os
    import shutil
    import time as _time
    from app import sat_autoresolver as sa

    copia = tmp_path / "problemas.xlsx"
    shutil.copy(sa.PATH_PROBLEMAS_SOL, copia)
    # Todo el estado de la caché se restaura al acabar: otros tests usan el Excel real.
    for nombre in ("_CACHE_INCIDENCIAS", "_CACHE_PROBLEMAS_SOL", "_MTIME_EXCEL", "_COMPROBADO_EXCEL"):
        monkeypatch.setattr(sa, nombre, getattr(sa, nombre))
    monkeypatch.setattr(sa, "PATH_PROBLEMAS_SOL", str(copia))
    monkeypatch.setattr(sa, "VIGENCIA_EXCEL_S", 0.0)

    _, antes = sa.cargar_base_conocimiento_sat(force_reload=True)

    # Otro Excel con más filas en el mismo sitio: el de incidencias sirve.
    shutil.copy(sa.PATH_INCIDENCIAS, copia)
    futuro = _time.time() + 10
    os.utime(copia, (futuro, futuro))

    _, despues = sa.cargar_base_conocimiento_sat()
    assert len(despues) != len(antes), "el Excel ha cambiado en disco y no se ha recargado"
