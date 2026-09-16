"""Deja las cuentas listas para abrir la aplicación a otra persona.

Antes de que la aplicación salga de `localhost` hay que cerrar lo que estaba
abierto de puertas adentro: la contraseña del administrador era `admin123` y
la propia pantalla de login la anunciaba. Quitarla de la pantalla no la
cambia — sigue siendo válida hasta que se sustituya.

    python tools/preparar_acceso_companero.py --email juan@empresa.com
    python tools/preparar_acceso_companero.py --email juan@empresa.com --dry-run

Hace dos cosas:

1. **Rota la contraseña de `admin@empresa.com`** por una aleatoria larga.
2. **Crea la cuenta del compañero** con rol `tecnico` y su propia contraseña.

Las dos contraseñas se escriben en `.credenciales_companero`, que está
ignorado por git. Ese fichero es el único sitio donde aparecen: no se
imprimen por pantalla, para que no queden en el historial de la terminal ni
en logs. Léelo, pásale al compañero **solo su línea**, y bórralo.

Por qué rol `tecnico` y no admin
--------------------------------
Con `tecnico` puede hacer todo lo que se le pide probar —buscar, usar el
asistente, crear y cerrar tickets— y no puede tocar usuarios ni borrar
manuales. Además cada ticket queda con su correo, así que al mirar los
resultados se sabe qué probó él y qué había antes.

Sus tickets seran `SAT-2026-NNNN`. El historico real es `SAT-HIST-NNNN`, asi
que no hay mezcla posible y limpiar sus pruebas al terminar es una linea.
"""

import argparse
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import database  # noqa: E402

ADMIN = "admin@empresa.com"
DESTINO = RAIZ / ".credenciales_companero"

# Suficiente para que no se adivine y todavia se pueda copiar y pegar.
LARGO = 20


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--email", required=True,
                   help="correo del compañero que va a probar")
    p.add_argument("--rol", default="tecnico", choices=["tecnico", "comercial"],
                   help="rol de su cuenta (por defecto tecnico)")
    p.add_argument("--dry-run", action="store_true",
                   help="dice qué haría sin tocar nada")
    args = p.parse_args()

    if "@" not in args.email:
        print(f"ERROR: {args.email!r} no parece un correo.", file=sys.stderr)
        return 1

    db = database.SessionLocal()
    try:
        admin = db.query(database.User).filter(database.User.email == ADMIN).first()
        if not admin:
            print(f"ERROR: no existe {ADMIN} en esta base de datos.", file=sys.stderr)
            return 1

        ya_existe = db.query(database.User).filter(
            database.User.email == args.email).first()

        if args.dry_run:
            print(f"Se rotaría la contraseña de {ADMIN}")
            if ya_existe:
                print(f"{args.email} ya existe (rol {ya_existe.role}): "
                      "se le pondría una contraseña nueva")
            else:
                print(f"Se crearía {args.email} con rol {args.rol}")
            print(f"Las dos irían a {DESTINO.name}")
            print("\n(--dry-run: no se ha tocado nada)")
            return 0

        clave_admin = secrets.token_urlsafe(LARGO)
        clave_companero = secrets.token_urlsafe(LARGO)

        if not database.cambiar_password_usuario(admin.id, clave_admin):
            print("ERROR: no se pudo cambiar la contraseña del admin.", file=sys.stderr)
            return 1

        if ya_existe:
            if not database.cambiar_password_usuario(ya_existe.id, clave_companero):
                print("ERROR: no se pudo cambiar su contraseña.", file=sys.stderr)
                return 1
            que_paso = f"ya existía (rol {ya_existe.role}), contraseña nueva"
        else:
            if not database.crear_usuario(args.email, clave_companero, args.rol):
                print("ERROR: no se pudo crear la cuenta.", file=sys.stderr)
                return 1
            que_paso = f"creada con rol {args.rol}"

        DESTINO.write_text(
            "Credenciales generadas por tools/preparar_acceso_companero.py\n"
            "BORRA ESTE FICHERO cuando las hayas repartido.\n\n"
            f"Tuya (administrador):\n  {ADMIN}\n  {clave_admin}\n\n"
            f"Del compañero — pásale SOLO estas dos líneas:\n"
            f"  {args.email}\n  {clave_companero}\n",
            encoding="utf-8",
        )

        print(f"Contraseña de {ADMIN}: rotada")
        print(f"Cuenta {args.email}: {que_paso}")
        print(f"\nLas dos están en {DESTINO.name} — y en ningún otro sitio.")
        print("Ábrelo, reparte, y bórralo.")
        print("\nAviso: al rotar la del admin, tu sesión abierta deja de valer.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
