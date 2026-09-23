"""El camino completo: llamada → triaje → ticket, sin saltarse ningún paso.

Cada pieza tenía sus tests, pero el recorrido entero no lo comprobaba nadie, y
ahí es donde estaban los fallos: el cuestionario no recogía el correo, el motor
devolvía siempre el mismo diagnóstico, y el ticket se creaba con `email: ""`
fijo. Tres piezas correctas por separado y un flujo que no servía.

Estos tests recorren el trayecto que hace de verdad un técnico durante una
llamada.
"""

import pytest

from app import database
from app.sat_autoresolver import evaluar_cuestionario_asistencia


def cuestionario_de_llamada(**cambios):
    """Lo que manda el formulario en una llamada real, con la persona delante."""
    datos = {
        "persona": {
            "nombre": "Paco Gómez",
            "correo": "paco@ventanas.example",
            "telefono": "612345678",
            "obra": "Residencial Las Rozas",
        },
        "partner": "IoT Fenster / MySmartWindow",
        "dispositivo": "Connect-1",
        "area_incidencia": "Dispositivo / electrónica",
        "estado_control_fisico": "Sí",
        "estado_control_app": "Sí",
        "sintomas_observados": [],
        "wifi_info": {"tipo_red": "Dual 2,4/5 GHz", "ssid_separados": "No", "seguridad": "WPA2"},
        "app_info": {"mas_de_un_movil": "No probado"},
        "info_especifica": {"hw_c1": {}, "hw_c2": {}},
        "descripcion_detallada": "",
        "acciones_realizadas": [],
    }
    datos.update(cambios)
    return datos


def test_la_llamada_completa_acaba_en_un_ticket_con_dueno(db):
    """De lo que cuenta el cliente al ticket, sin perder quién es por el camino."""
    # 1 · El técnico contesta el cuestionario con el cliente al teléfono.
    resultado = evaluar_cuestionario_asistencia(
        cuestionario_de_llamada(
            estado_control_app="No",
            descripcion_detallada="el pulsador de la pared va bien pero desde el movil no responde",
        ),
        db,
    )

    # 2 · El triaje concluye algo, y dice en qué se basa.
    assert resultado["concluyente"] is True
    assert resultado["motivos_diagnostico"]

    # 3 · Las respuestas quedan guardadas, atadas a lo que se dedujo.
    registro = database.guardar_cuestionario_asistencia(
        db, cuestionario_de_llamada(), resultado, creado_por="tecnico@iotfenster.com"
    )
    assert registro.id

    # 4 · Y el ticket nace con el cliente puesto, no huérfano.
    ticket = database.crear_ticket_sat(
        db,
        {
            "instalador": resultado["ticket_prefill"]["instalador"],
            "email": resultado["ticket_prefill"]["email"],
            "telefono": resultado["ticket_prefill"]["telefono"],
            "obra": resultado["ticket_prefill"]["obra"],
            "dispositivo": resultado["ticket_prefill"]["dispositivo"],
            "sintoma": resultado["ticket_prefill"]["sintoma"],
            "diagnostico": resultado["ticket_prefill"]["diagnostico"],
        },
        creado_por="tecnico@iotfenster.com",
    )
    assert ticket.email == "paco@ventanas.example"
    assert ticket.instalador == "Paco Gómez"

    # 5 · Si ese cliente vuelve a llamar, ya sabemos que tiene esto abierto.
    historial = database.historial_por_correo(db, "paco@ventanas.example")
    assert historial["abiertos"] == 1
    assert historial["tickets"][0]["numero_ticket"] == ticket.numero_ticket


def test_dos_averias_distintas_del_mismo_cliente_no_dan_el_mismo_diagnostico(db):
    """La comprobación que resume el fallo original, sobre el flujo real."""
    sin_app = evaluar_cuestionario_asistencia(
        cuestionario_de_llamada(estado_control_app="No"), db
    )
    sin_nada = evaluar_cuestionario_asistencia(
        cuestionario_de_llamada(estado_control_fisico="No", estado_control_app="No"), db
    )
    assert sin_app["diagnostico_titulo"] != sin_nada["diagnostico_titulo"]


def test_el_triaje_no_inventa_un_manual_cuando_no_lo_encuentra(db):
    """Devolvía un `manual_id: 1` fijo con la página 3 inventada.

    El técnico recibía una referencia documental con pinta de resultado de
    búsqueda y podía citarle al cliente una página que no habla de su avería.
    """
    resultado = evaluar_cuestionario_asistencia(
        cuestionario_de_llamada(
            dispositivo="Otro",
            descripcion_detallada="zzzz texto que no casa con ningun manual indexado zzzz",
        ),
        db,
    )
    manual = resultado["manual_recomendado"]
    assert manual is None or manual.get("manual_id") != 1
    if manual is None:
        assert "Manual de referencia" not in resultado["whatsapp_template"]


def test_el_mensaje_de_whatsapp_no_cita_documentacion_que_no_existe(db):
    resultado = evaluar_cuestionario_asistencia(
        cuestionario_de_llamada(dispositivo="Otro", descripcion_detallada="zzzz qqqq"), db
    )
    texto = resultado["whatsapp_template"]
    if resultado["manual_recomendado"] is None:
        assert "Pág." not in texto


@pytest.mark.parametrize("dispositivo", ["Connect-1", "Connect-2", "C-Wall", "C-Pulsar", "WAlarm"])
def test_todos_los_dispositivos_del_desplegable_se_pueden_triar(db, dispositivo):
    """Incluido C-Pulsar, que faltaba en la lista pese a tener manual y vídeos."""
    resultado = evaluar_cuestionario_asistencia(
        cuestionario_de_llamada(dispositivo=dispositivo), db
    )
    assert resultado["exito"] is True
    assert resultado["diagnostico_titulo"]
