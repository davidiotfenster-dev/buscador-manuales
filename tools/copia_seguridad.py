"""Copia de seguridad de la base de datos, con rotación y verificación.

La base de datos vive en el volumen `pgdata` de Docker. Un `docker compose
down -v` —que es la forma habitual de "empezar de cero"— lo borra sin
preguntar, y con él se van las 119 incidencias reales, los fragmentos de los
43 vídeos (una semana de pipeline y de cuota de Gemini) y los cuestionarios
de asistencia. Hasta ahora la única copia era un `pg_dump` suelto lanzado a
mano antes de la importación del histórico.

    python tools/copia_seguridad.py                  # copia + rotación
    python tools/copia_seguridad.py --verificar      # además, restaura y compara
    python tools/copia_seguridad.py --conservar 30   # guarda 30 en vez de 14
    python tools/copia_seguridad.py --sin-rotar      # no borra ninguna antigua

La rotación **solo** toca ficheros con el nombre que genera este script
(`buscador_manuales_FECHA.sql.gz`). Las copias sueltas puestas a mano con otro
nombre no se tocan nunca, para que una copia guardada a propósito antes de
algo delicado no desaparezca sola a las dos semanas.

Qué NO cubre esto, dicho claro:

  - Los PDF de `manuales/` (55 MB) no están en la base de datos ni en git.
    Viven solo en el disco. Copiarlos es:
        tar -czf copias/manuales_$(date +%F).tar.gz manuales/
  - `copias/` está en el mismo disco que los datos. Esto protege de un
    `down -v`, de un borrado por SQL y de una migración que salga mal.
    No protege de que se rompa el disco: para eso la carpeta tiene que
    acabar en otra máquina (la decisión de S3 que hay pendiente).
"""

import argparse
import gzip
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "copias"

SERVICIO_DB = "db"
USUARIO = "postgres"
BASE = "buscador_manuales"

# Solo se rotan los ficheros que genera este script.
PATRON = re.compile(r"^buscador_manuales_\d{4}-\d{2}-\d{2}_\d{4}\.sql\.gz$")

# pg_dump cierra siempre con esta línea. Si no está, el volcado se cortó a
# medias —contenedor parado, disco lleno— y el fichero es papel mojado. Vale
# la pena comprobarlo ahora y no el día que haga falta restaurar.
MARCA_FINAL = "-- PostgreSQL database dump complete"

# Tablas cuyo recuento se guarda junto a la copia. Son las que duelen.
TABLAS = ["tickets_sat", "videos", "video_fragmentos", "manuales",
          "paginas", "cuestionarios_asistencia", "usuarios"]


def _compose(*args: str, entrada: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=RAIZ, capture_output=True, input=entrada,
    )


def _psql(sql: str, base: str = BASE) -> str:
    proc = _compose("exec", "-T", SERVICIO_DB, "psql", "-U", USUARIO,
                    "-d", base, "-tAc", sql)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip())
    return proc.stdout.decode("utf-8", "replace").strip()


def recuentos(base: str = BASE) -> dict[str, int]:
    """Filas por tabla, para comparar antes y después de restaurar."""
    union = " UNION ALL ".join(
        f"SELECT '{t}', COUNT(*) FROM {t}" for t in TABLAS
    )
    salida = _psql(union, base)
    resultado = {}
    for linea in salida.splitlines():
        if "|" in linea:
            tabla, n = linea.split("|")
            resultado[tabla.strip()] = int(n)
    return resultado


def volcar(destino: Path) -> Path:
    """pg_dump comprimido. Devuelve la ruta del fichero escrito."""
    proc = _compose("exec", "-T", SERVICIO_DB, "pg_dump", "-U", USUARIO, "-d", BASE)
    if proc.returncode != 0:
        raise RuntimeError(
            "pg_dump falló: " + proc.stderr.decode("utf-8", "replace").strip()
        )

    sql = proc.stdout
    if MARCA_FINAL.encode() not in sql:
        raise RuntimeError(
            "el volcado no termina en la marca de pg_dump: está incompleto, "
            "no se guarda"
        )

    destino.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(destino, "wb") as f:
        f.write(sql)
    return destino


def rotar(conservar: int) -> list[Path]:
    """Borra las copias propias más viejas. Devuelve las borradas."""
    propias = sorted(
        (p for p in DESTINO.glob("*.sql.gz") if PATRON.match(p.name)),
        key=lambda p: p.name,
    )
    sobran = propias[:-conservar] if conservar > 0 else []
    for p in sobran:
        p.unlink()
    return sobran


def verificar_restauracion(copia: Path, originales: dict[str, int]) -> dict[str, int]:
    """Restaura la copia en una base desechable y cuenta sus filas.

    Una copia que nunca se ha restaurado no es una copia, es un fichero. Esto
    la restaura de verdad, en una base aparte que se destruye al terminar, así
    que la de producción no se toca en ningún momento.
    """
    temporal = f"verificacion_copia_{datetime.now():%H%M%S}"
    _psql(f'CREATE DATABASE "{temporal}"', base="postgres")
    try:
        with gzip.open(copia, "rb") as f:
            sql = f.read()
        proc = _compose("exec", "-T", SERVICIO_DB, "psql", "-U", USUARIO,
                        "-d", temporal, "-q", "-v", "ON_ERROR_STOP=1",
                        entrada=sql)
        if proc.returncode != 0:
            raise RuntimeError(
                "la copia no se pudo restaurar: "
                + proc.stderr.decode("utf-8", "replace").strip()[:500]
            )
        return recuentos(temporal)
    finally:
        _psql(f'DROP DATABASE IF EXISTS "{temporal}"', base="postgres")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--conservar", type=int, default=14,
                   help="cuántas copias propias se guardan (por defecto 14)")
    p.add_argument("--sin-rotar", action="store_true",
                   help="no borrar ninguna copia antigua")
    p.add_argument("--verificar", action="store_true",
                   help="restaurar la copia en una base desechable y comparar filas")
    args = p.parse_args()

    marca = datetime.now().strftime("%Y-%m-%d_%H%M")
    destino = DESTINO / f"buscador_manuales_{marca}.sql.gz"

    try:
        antes = recuentos()
    except RuntimeError as e:
        print(f"ERROR: no se puede consultar la base de datos.\n{e}", file=sys.stderr)
        print("¿Está el stack levantado? `docker compose ps`", file=sys.stderr)
        return 1

    try:
        volcar(destino)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    tam = destino.stat().st_size
    print(f"Copia escrita: {destino.relative_to(RAIZ)}  ({tam / 1024 / 1024:.1f} MB)")
    for tabla, n in antes.items():
        print(f"  {tabla:<26} {n:>7}")

    if args.verificar:
        print("\nVerificando: restaurando en una base desechable...")
        try:
            despues = verificar_restauracion(destino, antes)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print("La copia se ha guardado, pero NO se ha podido restaurar.",
                  file=sys.stderr)
            return 1

        fallos = [t for t in antes if antes[t] != despues.get(t)]
        if fallos:
            print("ERROR: la copia restaurada no coincide:", file=sys.stderr)
            for t in fallos:
                print(f"  {t}: {antes[t]} -> {despues.get(t)}", file=sys.stderr)
            return 1
        print("  Restaurada y comparada: todas las tablas coinciden.")

    if not args.sin_rotar:
        borradas = rotar(args.conservar)
        if borradas:
            print(f"\nRotación: {len(borradas)} copia(s) antigua(s) eliminada(s).")
            for b in borradas:
                print(f"  - {b.name}")

    quedan = sorted(p for p in DESTINO.glob("*.sql.gz") if PATRON.match(p.name))
    print(f"\nCopias disponibles: {len(quedan)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
