"""Prepara un paquete para que otra persona monte su propia copia de la aplicación.

El objetivo es que pruebe **sin compartir datos en ninguna dirección**: lo que
escriba él no llega aquí, y lo que se escriba aquí no le llega a él. Eso no se
consigue con permisos ni con un modo invitado —la aplicación no es
multi-inquilino— sino de la única forma que hoy es cierta: **su propia base de
datos, en su propia máquina**.

    python tools/paquete_companero.py
    python tools/paquete_companero.py --sin-manuales   # solo la base de datos

Lo que se comparte es el punto de partida (manuales, vídeos, el histórico
clasificado) para que la aplicación no le aparezca vacía y no tenga sentido
probarla. A partir de ahí, las dos copias se separan para siempre.

Dos cosas que este script deja fuera a propósito
------------------------------------------------
**Los datos de `usuarios`.** Llevan los hashes de contraseña de las cuentas de
aquí. No hay ninguna razón para que viajen, y la aplicación se crea su propio
`admin@empresa.com` con contraseña nueva cuando arranca sin usuarios: la
escribe en `.admin_initial_password`.

La **tabla** sí viaja, vacía. Excluirla entera parecía más limpio y era un
fallo: el volcado trae `alembic_version` al día, así que Alembic daría el
esquema por hecho y no crearía la tabla que falta. La aplicación reventaría al
buscar el admin — y solo en la máquina del otro, que es donde peor se arregla.

**El `.env`.** Contiene la `SECRET_KEY` con la que se firman los tokens de aquí
y la contraseña de esta base de datos. Cada copia genera las suyas.

Lo que sí viaja, y conviene decirlo en voz alta
-----------------------------------------------
Los 119 tickets del histórico llevan **nombres reales de instaladores** (89
personas). No hay teléfonos ni correos, pero son datos de personas reales: el
paquete es para un compañero de la empresa, no para enseñarlo fuera.
"""

import argparse
import gzip
import subprocess
import sys
import tarfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MANUALES = RAIZ / "manuales"

SERVICIO_DB = "db"
USUARIO = "postgres"
BASE = "buscador_manuales"

# Tablas cuyos DATOS no viajan. Se excluyen los datos y **no la tabla**: el
# volcado trae `alembic_version` al dia, asi que al arrancar Alembic da el
# esquema por hecho y no crearia una tabla que faltase. La aplicacion
# reventaria al buscar el admin, y solo en la maquina del otro.
EXCLUIDAS = ["usuarios"]

MARCA_FINAL = "-- PostgreSQL database dump complete"

LEEME = """# Copia de pruebas del Buscador de Manuales

Este paquete monta una copia **entera y separada** de la aplicación. Lo que
escribas aquí no llega a nadie más, y lo que escriban otros no te llega a ti:
es tu propia base de datos en tu propia máquina.

Lo que trae es el punto de partida —los manuales indexados, los vídeos del
canal y el histórico de incidencias ya clasificado— para que la aplicación no
te aparezca vacía.

## Qué hace falta

Docker Desktop y Git. Nada más.

## Montarlo

**1. El código**

    git clone https://github.com/davidiotfenster-dev/buscador-manuales.git
    cd buscador-manuales

**2. Tu configuración.** Copia `.env.example` a `.env` y rellena las dos
primeras. Invéntate la contraseña de Postgres; la `SECRET_KEY` sácala de:

    python -c "import secrets; print(secrets.token_urlsafe(64))"

**3. Los manuales.** Descomprime `manuales.tar.gz` dentro de la carpeta del
proyecto. Tiene que quedar un directorio `manuales/` con los PDF.

**4. La base de datos.** Levanta solo Postgres y carga los datos:

    docker compose up -d db
    gunzip -c datos.sql.gz | docker compose exec -T db psql -U postgres -d buscador_manuales

**5. Arranca.**

    docker compose up -d

Entra en http://localhost:8000. La aplicación se crea un usuario
`admin@empresa.com` la primera vez y **escribe la contraseña en el fichero
`.admin_initial_password`**. Ábrelo, entra, y bórralo.

## Antes de tocar nada

Los tickets del histórico llevan **nombres reales de instaladores**. Son datos
de la empresa: quedan entre nosotros.

## Si quieres empezar de cero

    docker compose down -v

Eso borra la base de datos entera y vuelves al paso 4. Ojo, que no pregunta.
"""


def _compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], cwd=RAIZ, capture_output=True)


def volcar_sin_usuarios(destino: Path) -> int:
    """pg_dump completo menos las tablas excluidas. Devuelve el tamaño."""
    exclusiones = []
    for tabla in EXCLUIDAS:
        exclusiones += ["--exclude-table-data", tabla]

    proc = _compose("exec", "-T", SERVICIO_DB, "pg_dump", "-U", USUARIO, "-d", BASE,
                    *exclusiones)
    if proc.returncode != 0:
        raise RuntimeError("pg_dump falló: "
                           + proc.stderr.decode("utf-8", "replace").strip())

    sql = proc.stdout
    if MARCA_FINAL.encode() not in sql:
        raise RuntimeError("el volcado está incompleto, no se empaqueta")

    # Que no se cuele ni un hash. `--exclude-table-data` deberia bastar, pero
    # esto es lo unico que de verdad lo garantiza, y una bandera mal escrita
    # no avisa de nada por su cuenta.
    #
    # Se busca el prefijo de bcrypt, que es lo que identifica a un hash de
    # verdad. El nombre de la columna `password_hash` NO sirve de senal: el
    # volcado trae el `CREATE TABLE usuarios` a proposito -la tabla tiene que
    # existir, vacia- y ahi aparece de forma legitima.
    if b"$2b$" in sql or b"$2a$" in sql:
        raise RuntimeError("el volcado contiene hashes de contrasena: NO se empaqueta")

    with gzip.open(destino, "wb") as f:
        f.write(sql)
    return destino.stat().st_size


def empaquetar_manuales(destino: Path) -> int:
    with tarfile.open(destino, "w:gz") as tar:
        tar.add(MANUALES, arcname="manuales")
    return destino.stat().st_size


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sin-manuales", action="store_true",
                   help="no incluir los PDF (55 MB)")
    args = p.parse_args()

    carpeta = RAIZ / "copias" / f"paquete-companero-{date.today()}"
    carpeta.mkdir(parents=True, exist_ok=True)

    print(f"Preparando {carpeta.relative_to(RAIZ)}\n")

    try:
        tam = volcar_sin_usuarios(carpeta / "datos.sql.gz")
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"  datos.sql.gz      {tam / 1024 / 1024:6.1f} MB   "
          f"(la tabla {', '.join(EXCLUIDAS)} viaja vacia)")

    if not args.sin_manuales:
        if not MANUALES.is_dir():
            print(f"ERROR: no existe {MANUALES}", file=sys.stderr)
            return 1
        tam = empaquetar_manuales(carpeta / "manuales.tar.gz")
        print(f"  manuales.tar.gz   {tam / 1024 / 1024:6.1f} MB")

    (carpeta / "LEEME.md").write_text(LEEME, encoding="utf-8")
    print("  LEEME.md                      instrucciones de montaje\n")

    print("Listo. Lo que NO va dentro, y es a propósito:")
    print("  - los datos de `usuarios` (hashes de contraseña); la tabla va vacia")
    print("  - el .env (SECRET_KEY y contraseña de esta base de datos)")
    print("\nAvisa de que los tickets llevan nombres reales de instaladores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
