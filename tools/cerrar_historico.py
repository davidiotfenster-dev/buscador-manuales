"""Deriva el cierre de los tickets históricos a partir de lo que hizo SAT.

El formulario de cierre existe, tiene diez campos y **ninguno de los 119
tickets lo tiene relleno**. Sin un solo cierre, G10 —«¿la documentación fue
suficiente?»— es una pregunta construida y sin ninguna respuesta, y el
buscador de casos parecidos no puede decir qué acabó funcionando.

La columna «Acción» del Excel no es texto libre: SAT usaba un vocabulario
cerrado de doce acciones. Eso permite derivar el cierre sin inventarlo, del
mismo modo que la columna «Problema» permitió clasificar por grupo.

    python tools/cerrar_historico.py --dry-run   # solo enseña el reparto
    python tools/cerrar_historico.py             # escribe
    python tools/cerrar_historico.py --rehacer   # recalcula los ya cerrados

Es idempotente: un ticket que ya tiene cierre se salta, salvo `--rehacer`.

Lo que se deriva y lo que no
----------------------------
Se rellenan `cierre_resuelto`, `cierre_doc_suficiente`, `cierre_escalado`,
`cierre_descripcion` y `cierre_fecha`. Se dejan vacíos a propósito:

  - `cierre_manual_id` y `cierre_video_id`: la acción «Videos» dice que se
    mandaron vídeos, no *cuál*. Apuntar uno al azar contaminaría la métrica
    de qué documentación resuelve.
  - `cierre_doc_texto` y `cierre_alternativa`: son «qué documentación
    faltaba». El Excel no lo recoge y no hay de dónde sacarlo.

`cierre_por` queda como `historico-excel` en todos, para que se distingan de
un cierre hecho por una persona. Cualquier métrica que quiera contar solo
cierres reales filtra por esa columna.

`cierre_fecha` se pone igual que `fecha_creacion`, que en estos tickets es la
fecha de importación: el Excel no trae fechas. No es una fecha real de cierre
y no debe leerse como tal.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sqlalchemy import text  # noqa: E402

from app import database  # noqa: E402

# Las doce acciones del Excel, repartidas por lo que significan para el cierre.
#
# La frontera que importa es una sola: ¿bastó con explicar, o tuvo que actuar
# alguien? Explicar —mandar un vídeo, una guía, guiar por teléfono, pedir un
# reset— es documentación haciendo su trabajo. Tocar el firmware, el servidor,
# reponer una pieza o ir a la obra significa que la documentación no llegó,
# por buena que fuera.
DOCUMENTAL = {"Videos", "Mensaje Informativo"}
GUIADO = {"Llamada", "Reset", "Tiempo"}
INTERVENCION = {"Firmware", "servidor", "Reposición", "Asistencia Presencial",
                "Ofertar Nuevos Dispositivos"}
SIN_DESENLACE = {"incompareciencia"}
AJENA = {"Incidencia Ajena a nosotros"}

CONOCIDAS = DOCUMENTAL | GUIADO | INTERVENCION | SIN_DESENLACE | AJENA

MARCA = "historico-excel"


def acciones_de(solucion: str | None) -> set[str]:
    if not solucion:
        return set()
    return {a.strip() for a in solucion.split(",") if a.strip()}


def derivar(estado: str, solucion: str | None) -> dict | None:
    """El cierre que se desprende de las acciones, o None si no se puede.

    Devolver None es una respuesta legítima: un ticket en espera no está
    cerrado, y uno resuelto sin ninguna acción anotada no dice qué pasó.
    Rellenarlos «por completar» metería ruido en la única métrica que
    tenemos de si la documentación sirve.
    """
    if estado != "resuelto":
        return None

    acciones = acciones_de(solucion)
    if not acciones:
        return None

    # El cliente dejó de responder. Está cerrado, pero no resuelto, y no se
    # puede saber si la documentación habría bastado.
    if acciones & SIN_DESENLACE:
        return {
            "resuelto": False,
            "doc_suficiente": None,
            "escalado": False,
            "motivo": "incomparecencia",
        }

    # Tuvo que intervenir alguien: firmware, servidor, pieza o visita.
    if acciones & INTERVENCION:
        return {
            "resuelto": True,
            "doc_suficiente": False,
            "escalado": True,
            "motivo": "intervencion",
        }

    # No era nuestra: se derivó sin que la documentación entrara en juego.
    if acciones & AJENA:
        return {
            "resuelto": True,
            "doc_suficiente": None,
            "escalado": True,
            "motivo": "ajena",
        }

    # Solo se explicó, y con eso se resolvió.
    return {
        "resuelto": True,
        "doc_suficiente": True,
        "escalado": False,
        "motivo": "explicado",
    }


def descripcion(solucion: str, motivo: str) -> str:
    textos = {
        "incomparecencia": "El cliente dejó de responder; no consta que se resolviera.",
        "intervencion": "Hizo falta intervención técnica: la documentación no bastó.",
        "ajena": "Incidencia ajena: se derivó fuera.",
        "explicado": "Se resolvió explicando, sin intervención técnica.",
    }
    return f"{textos[motivo]} Acciones registradas por SAT: {solucion}."


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true",
                   help="enseña el reparto sin escribir nada")
    p.add_argument("--rehacer", action="store_true",
                   help="recalcula también los tickets que ya tienen cierre")
    args = p.parse_args()

    db = database.SessionLocal()
    try:
        filas = db.execute(text("""
            SELECT id, numero_ticket, estado, solucion, cierre_resuelto
            FROM tickets_sat
            WHERE numero_ticket LIKE 'SAT-HIST-%'
            ORDER BY numero_ticket
        """)).mappings().all()

        if not filas:
            print("No hay tickets del histórico. ¿Se importó el Excel?")
            return 1

        desconocidas = Counter()
        for f in filas:
            desconocidas.update(acciones_de(f["solucion"]) - CONOCIDAS)
        if desconocidas:
            print("AVISO: acciones que este script no sabe interpretar.")
            print("Se tratan como «explicado», que puede no ser lo correcto:")
            for a, n in desconocidas.most_common():
                print(f"  {a!r}: {n}")
            print()

        reparto = Counter()
        escritos = 0
        for f in filas:
            if f["cierre_resuelto"] is not None and not args.rehacer:
                reparto["ya tenía cierre"] += 1
                continue

            cierre = derivar(f["estado"], f["solucion"])
            if cierre is None:
                razon = ("en espera" if f["estado"] != "resuelto"
                         else "resuelto sin acciones anotadas")
                reparto[f"sin cierre ({razon})"] += 1
                continue

            reparto[cierre["motivo"]] += 1
            if args.dry_run:
                continue

            db.execute(text("""
                UPDATE tickets_sat SET
                    cierre_resuelto = :resuelto,
                    cierre_doc_suficiente = :doc,
                    cierre_escalado = :escalado,
                    cierre_descripcion = :descripcion,
                    cierre_por = :por,
                    cierre_fecha = fecha_creacion
                WHERE id = :id
            """), {
                "resuelto": cierre["resuelto"],
                "doc": cierre["doc_suficiente"],
                "escalado": cierre["escalado"],
                "descripcion": descripcion(f["solucion"], cierre["motivo"]),
                "por": MARCA,
                "id": f["id"],
            })
            escritos += 1

        if not args.dry_run:
            db.commit()

        print(f"Tickets del histórico: {len(filas)}")
        for clave, n in reparto.most_common():
            print(f"  {clave:<40} {n:>4}")

        cerrados = sum(reparto[m] for m in
                       ("explicado", "intervencion", "ajena", "incomparecencia"))
        con_respuesta = reparto["explicado"] + reparto["intervencion"]
        if con_respuesta:
            pct = 100 * reparto["explicado"] / con_respuesta
            print(f"\nG10 — de {con_respuesta} cierres con respuesta clara, "
                  f"la documentación bastó en el {pct:.0f}%.")

        if args.dry_run:
            print(f"\n(--dry-run: no se ha escrito nada; se cerrarían {cerrados})")
        else:
            print(f"\nCierres escritos: {escritos}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
