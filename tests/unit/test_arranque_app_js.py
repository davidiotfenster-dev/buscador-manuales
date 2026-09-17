"""La aplicación no puede arrancar antes de terminar de definirse.

`app.js` son ~6.000 líneas en un solo ámbito. Llamar a `verificarSesion()` a un
tercio del fichero hacía que el modo invitado entrase por
`inicializarModuloEsquemas()`, que lee un `let` declarado 1.500 líneas más
abajo. Un `let` no existe hasta que se ejecuta su declaración, así que reventaba
con «Cannot access 'esquemasModuloInicializado' before initialization».

El fallo no era esa variable: era arrancar a mitad de fichero. Mover la
declaración arriba habría tapado este caso y dejado el siguiente `let` que
alguien añada en la misma trampa.

No hay runner de JavaScript en el proyecto, así que esto es lo que se puede
comprobar sin uno: que el arranque sigue aplazado. Es poco, pero cubre
exactamente la regresión que costó encontrar.
"""

import re
from pathlib import Path

import pytest

APP_JS = Path(__file__).resolve().parent.parent.parent / "app" / "static" / "app.js"


@pytest.fixture(scope="module")
def codigo():
    return APP_JS.read_text(encoding="utf-8")


def test_la_app_no_arranca_a_mitad_de_fichero(codigo):
    """Una llamada suelta en el margen izquierdo se ejecuta durante la
    evaluación del módulo, con la mitad del fichero aún sin definir."""
    sueltas = re.findall(r"(?m)^verificarSesion\(\);", codigo)

    assert not sueltas, (
        "verificarSesion() se llama a nivel de módulo: la aplicación arranca "
        "antes de que existan los `let` y `const` declarados más abajo"
    )


def test_el_arranque_esta_aplazado(codigo):
    """El microtask corre en cuanto termina de evaluarse el módulo: antes de
    pintar y antes de que nadie pueda tocar nada, pero con todo ya definido."""
    assert "queueMicrotask(verificarSesion);" in codigo


def test_el_let_sigue_donde_estaba(codigo):
    """Si alguien «arregla» esto subiendo la variable, el arranque volvería a
    quedar a mitad de fichero y el siguiente `let` caería igual. Este test
    está para que ese cambio obligue a leer el de arriba."""
    lineas = codigo.splitlines()
    declaracion = next(i for i, l in enumerate(lineas)
                       if l.startswith("let esquemasModuloInicializado"))
    arranque = next(i for i, l in enumerate(lineas)
                    if l.startswith("queueMicrotask(verificarSesion)"))

    assert arranque < declaracion, (
        "el arranque ya no está antes de la declaración; si se ha reordenado "
        "el fichero a propósito, actualiza este test"
    )
