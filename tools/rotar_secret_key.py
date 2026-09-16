"""Sustituye la SECRET_KEY del .env por una nueva, guardando la anterior.

La clave con la que se firman hoy los tokens es la que estuvo escrita en
`app/auth.py` y publicada en el repositorio. El fallback se quitó en la Fase 0,
pero el **valor** sigue siendo el filtrado: cualquiera que leyera aquel commit
puede firmarse un token de administrador. Rotarla es lo que cierra el agujero
de verdad.

    python tools/rotar_secret_key.py            # rota
    python tools/rotar_secret_key.py --dry-run  # solo dice qué haría

Esto **cierra todas las sesiones abiertas**: los tokens emitidos con la clave
vieja dejan de validar y hay que volver a entrar. Es lo esperado.

Existe como script y no como una línea suelta porque la línea suelta no
sobrevive a PowerShell: las comillas se pierden al pasar el código a `python`
y la orden falla a medias, que en un fichero de configuración es justo lo que
no se quiere.
"""

import argparse
import re
import secrets
import shutil
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENV = RAIZ / ".env"
COPIAS = RAIZ / "copias"

# Longitud en bytes de entropía. 64 bytes ≈ 86 caracteres en base64url, muy por
# encima de lo que necesita HS256 y sin coste ninguno.
BYTES = 64


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true",
                   help="no escribe nada, solo dice qué haría")
    args = p.parse_args()

    if not ENV.exists():
        print(f"ERROR: no existe {ENV}", file=sys.stderr)
        print("Copia .env.example a .env y rellénalo antes de rotar.", file=sys.stderr)
        return 1

    texto = ENV.read_text(encoding="utf-8")

    # Se exige que la línea ya esté: crear una SECRET_KEY donde no había
    # ninguna significaría que este .env no es el que usa el stack, y dejarlo
    # a medias es peor que no tocarlo.
    if not re.search(r"(?m)^SECRET_KEY=", texto):
        print("ERROR: el .env no tiene ninguna línea SECRET_KEY=", file=sys.stderr)
        print("No se toca nada: revisa que sea el .env correcto.", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Se rotaría SECRET_KEY en {ENV}")
        print(f"Se guardaría la anterior en copias/.env.antes-de-rotar-{date.today()}")
        print("(--dry-run: no se ha escrito nada)")
        return 0

    COPIAS.mkdir(exist_ok=True)
    respaldo = COPIAS / f".env.antes-de-rotar-{date.today()}"
    shutil.copy2(ENV, respaldo)

    nuevo, n = re.subn(r"(?m)^SECRET_KEY=.*$",
                       "SECRET_KEY=" + secrets.token_urlsafe(BYTES), texto)
    if n != 1:
        print(f"ERROR: se esperaba una línea SECRET_KEY y hay {n}. No se toca nada.",
              file=sys.stderr)
        return 1

    ENV.write_text(nuevo, encoding="utf-8")

    print(f"SECRET_KEY rotada en {ENV.name}")
    print(f"Copia de la anterior: copias/{respaldo.name}")
    print()
    print("Falta reiniciar para que el contenedor la recoja:")
    print("    docker compose up -d --force-recreate web")
    print()
    print("Al reiniciar se cierran todas las sesiones abiertas: hay que volver a entrar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
