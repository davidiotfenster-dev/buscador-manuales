"""La pantalla de login no puede traer credenciales puestas.

Tenía dos botones que anunciaban el usuario y la contraseña del
administrador, y los campos venían rellenos con ellos. Las credenciales
funcionaban: cualquiera que alcanzase la aplicación era admin en un clic.

Mientras solo vive en localhost parece inofensivo, y por eso duró. Pero el
agujero viaja con la aplicación: el día que se comparta por un túnel o se
despliegue, va dentro. Se descubrió justo al ir a pasarle un enlace a un
compañero.

Esto solo comprueba la plantilla y el JS. **Que la contraseña del admin ya no
sea `admin123` es otra cosa y no se puede probar aquí**: vive en la base de
datos de cada instalación.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent.parent
MODALS = RAIZ / "app" / "templates" / "partials" / "modals.html"
APP_JS = RAIZ / "app" / "static" / "app.js"

# Contraseñas que llegaron a estar escritas en el repositorio. Si alguna vuelve
# a aparecer en el código que se sirve al navegador, es que ha vuelto el fallo.
FILTRADAS = ["admin123", "tecnico123"]


@pytest.mark.parametrize("clave", FILTRADAS)
@pytest.mark.parametrize("fichero", [MODALS, APP_JS], ids=["modals.html", "app.js"])
def test_ninguna_contrasena_en_el_codigo_del_navegador(fichero, clave):
    assert clave not in fichero.read_text(encoding="utf-8")


@pytest.mark.parametrize("campo", ["login-email", "login-password"])
def test_los_campos_de_login_llegan_vacios(campo):
    """Un `value=` con algo dentro es exactamente como estaba el fallo."""
    html = MODALS.read_text(encoding="utf-8")

    etiqueta = re.search(rf'<input[^>]*id="{campo}"[^>]*>', html)
    assert etiqueta, f"no se encuentra el campo {campo}"

    valor = re.search(r'value="([^"]*)"', etiqueta.group(0))
    assert valor is None or valor.group(1) == "", (
        f"{campo} viene relleno con {valor.group(1)!r}"
    )


def test_no_quedan_botones_de_acceso_rapido():
    html = MODALS.read_text(encoding="utf-8")

    assert "btn-quick-login-admin" not in html
    assert "btn-quick-login-tecnico" not in html


def test_el_modo_invitado_se_conserva():
    """No es el agujero: es de fachada y los datos siguen pidiendo token.
    Quitarlo de paso habría sido cambiar una decisión de producto sin
    que nadie lo pidiera."""
    assert "btn-login-invitado" in MODALS.read_text(encoding="utf-8")
