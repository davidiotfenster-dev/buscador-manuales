"""El orden del cuestionario de asistencia.

El formulario empezaba por el dispositivo y no preguntaba por la persona en
ningún momento: el nombre, la obra y el teléfono estaban al final del primer
bloque, en gris, bajo el rótulo «Datos Opcionales de Referencia», y el correo no
existía. Pero el correo es la puerta de entrada al caso —es lo que identifica al
cliente, lo que viaja al ticket y lo que permite cruzar esta llamada con la
anterior—, así que va primero.

El orden acordado es: quién llama, luego la comercializadora y el equipo, luego
lo que le pasa, y el resto detrás.

No hay runner de JavaScript en el proyecto, así que esto comprueba lo que se
puede comprobar sin uno: que los pasos están en ese orden y que los campos de la
persona siguen existiendo con los ids que lee `app.js`. Es poco, pero cubre
exactamente lo que se rompería al reordenar bloques otra vez.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent.parent
VISTA = RAIZ / "app" / "templates" / "partials" / "vista_asistencia.html"
APP_JS = RAIZ / "app" / "static" / "app.js"


@pytest.fixture(scope="module")
def html():
    return VISTA.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js():
    return APP_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js_codigo(js):
    """`app.js` sin comentarios.

    Los comentarios de este proyecto citan el código que se corrigió, así que
    una búsqueda literal sobre el fichero entero encuentra el fallo descrito en
    el comentario y da por roto lo que está bien."""
    sin_bloque = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", "", linea) for linea in sin_bloque.splitlines())


def pasos(html):
    """[(numero, titulo)] en el orden en que aparecen en el documento."""
    return [
        (int(n), t)
        for n, t in re.findall(r'data-paso="(\d+)"\s+data-titulo="([^"]+)"', html)
    ]


def test_el_cuestionario_empieza_preguntando_quien_llama(html):
    primero = pasos(html)[0]
    assert primero[0] == 1
    assert "Quién llama" in primero[1]


def test_el_orden_es_persona_comercializadora_y_problema(html):
    titulos = [t for _, t in pasos(html)]
    assert titulos[0] == "Quién llama"
    assert titulos[1] == "Comercializadora y equipo"
    assert titulos[2] == "Qué le pasa"


def test_los_pasos_estan_numerados_sin_saltos(html):
    """`irAPasoAsistencia` navega por `data-paso`: un hueco deja un paso muerto."""
    numeros = [n for n, _ in pasos(html)]
    assert numeros == list(range(1, len(numeros) + 1))


def test_el_correo_del_cliente_existe_y_esta_en_el_primer_paso(html):
    assert 'id="asist-persona-correo"' in html
    primer_paso = html.split('data-paso="2"')[0]
    assert 'id="asist-persona-correo"' in primer_paso, (
        "El correo tiene que estar en el paso 1: es la puerta de entrada al caso"
    )


@pytest.mark.parametrize(
    "campo", ["asist-input-instalador", "asist-input-telefono", "asist-input-obra"]
)
def test_los_datos_de_contacto_estan_en_el_primer_paso(html, campo):
    """Estaban al final del bloque del dispositivo; ahora abren el cuestionario."""
    primer_paso = html.split('data-paso="2"')[0]
    assert f'id="{campo}"' in primer_paso


@pytest.mark.parametrize(
    "campo",
    [
        "asist-input-instalador",
        "asist-input-telefono",
        "asist-input-obra",
        "asist-ficha-obra",
        "asist-persona-correo",
        "asist-persona-historial",
    ],
)
def test_ningun_id_esta_duplicado(html, campo):
    """Mover un bloque y olvidarse de borrar el original deja dos ids iguales.

    `getElementById` devuelve el primero, así que el formulario parecería
    funcionar mientras se lee un campo que el técnico no ve."""
    assert html.count(f'id="{campo}"') == 1


def test_el_javascript_envia_los_datos_de_la_persona(js):
    """Sin esto el formulario pregunta por el cliente y luego no lo manda."""
    assert "persona: persona" in js
    for lectura in ["asist-persona-correo", "asist-input-instalador", "asist-input-telefono"]:
        assert lectura in js


def test_el_correo_consulta_el_historial_del_cliente(js):
    assert "consultarHistorialCliente" in js
    assert "/api/sat/clientes/historial" in js


def test_el_ticket_no_se_crea_con_el_correo_vacio_a_la_fuerza(js):
    """Los dos sitios que abren ticket desde el triaje llevaban `email: ""` fijo.

    El ticket nacía sin destinatario, así que `auto-registrar-enviar` generaba
    el parte y no tenía a quién mandárselo. Mientras el formulario no pedía el
    correo casi no se notaba; ahora que lo pide, dejarlo fijo sería perderlo
    justo en el último paso.
    """
    assert 'email: ""' not in js
    assert js.count('asist-persona-correo")?.value.trim() || prefill.email') == 2


def test_el_repetidor_mesh_lee_los_botones_que_existen(js_codigo, html):
    """Los cinco botones de repetidor/mesh no hacían nada.

    El HTML tiene un grupo de botones `#asist-group-mesh`, pero el JavaScript
    hacía `getElementById("asist-wifi-mesh").value` sobre un `<select>` que no
    existe en ninguna plantilla. El valor era **siempre** "Ninguno" pulsara el
    técnico lo que pulsara, así que el dato se perdía entero sin ningún error
    que lo delatara.
    """
    assert 'id="asist-group-mesh"' in html
    assert 'getElementById("asist-wifi-mesh")' not in js_codigo
    assert 'getChoiceValue("asist-group-mesh"' in js_codigo


def test_ningun_id_leido_por_el_js_falta_en_las_plantillas(js_codigo):
    """La clase de fallo del mesh, buscada en todo el módulo de asistencia.

    `getElementById` de un id inexistente devuelve `null` y, con el encadenado
    opcional que usa este fichero, se queda en el valor por defecto sin avisar.
    Un campo entero deja de recogerse y nada falla.
    """
    plantillas = "".join(
        f.read_text(encoding="utf-8") for f in (RAIZ / "app" / "templates").rglob("*.html")
    )
    ids_html = set(re.findall(r'id="([^"]+)"', plantillas))
    leidos = set(re.findall(r'getElementById\("(asist[^"]+)"\)', js_codigo))
    leidos |= set(re.findall(r'querySelector\("#(asist[a-zA-Z0-9_-]+)', js_codigo))
    faltan = sorted(leidos - ids_html)
    assert not faltan, f"El JS lee ids que no existen en ninguna plantilla: {faltan}"


def test_el_desplegable_tiene_las_familias_con_documentacion(html):
    """C-Pulsar faltaba pese a tener manual propio y cinco vídeos indexados.

    Sin la opción, una incidencia de C-Pulsar se registraba con otro dispositivo
    y la búsqueda de manual y vídeo perdía su señal de más peso.
    """
    for familia in ["Connect-1", "Connect-2", "C-Wall", "C-Pulsar", "WAlarm"]:
        assert f'value="{familia}"' in html, f"Falta {familia} en el desplegable"
