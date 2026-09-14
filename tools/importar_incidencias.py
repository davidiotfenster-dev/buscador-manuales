"""Importa las 119 incidencias reales de data/sat/Incidencias.xlsx como tickets.

De ese Excel salieron los 9 grupos de incidencia (ver docs/G2_TAXONOMIA_GRUPOS.md),
pero las incidencias en sí nunca llegaron a la base de datos: los tickets que
había eran pruebas de desarrollo. Sin historial real no hay métricas por grupo
que signifiquen nada, ni casos resueltos que ofrecer cuando entra uno parecido.

La columna «Problema» ya trae las etiquetas que puso SAT, así que la
clasificación no se inventa: se traduce.

    python tools/importar_incidencias.py --dry-run    # solo enseña qué haría
    python tools/importar_incidencias.py              # escribe
    python tools/importar_incidencias.py --borrar-existentes

Es idempotente por `numero_ticket`: una incidencia ya importada se salta, así
que volver a lanzarlo no duplica nada.
"""

import argparse
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import database  # noqa: E402
from app.sat_autoresolver import _parsear_xlsx  # noqa: E402

EXCEL = RAIZ / "data" / "sat" / "Incidencias.xlsx"

# Traducción de las 11 etiquetas que usa SAT a los 9 grupos. «Wifi» y «Conexión»
# caen las dos en CONECTIVIDAD: hoy se usan por separado pero ambas son
# problemas de enlace, y separarlas daría 10 grupos. Es una de las decisiones
# que el workshop tiene que confirmar (G2.1).
#
# «Sensor de Apertura» tiene 1 incidencia de 119 y no llegó a ser grupo: encaja
# mejor como pregunta condicionada al dispositivo (G4).
MAPA_ETIQUETAS = {
    "vinculacion": "VINCULACION",
    "wifi": "CONECTIVIDAD",
    "conexion": "CONECTIVIDAD",
    "gestual": "GESTUAL",
    "aplicacion": "APP",
    "pulsador": "PULSADOR",
    "integraciones": "INTEGRACIONES",
    "instalacion": "INSTALACION",
    "rotura": "HARDWARE",
    "otro": "OTRO",
    "sensor de apertura": "OTRO",
}


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").lower().strip()


def grupos_de_etiquetas(crudo: str) -> List[str]:
    """Traduce la celda «Problema» a grupos, el primero es el principal.

    Dos reglas que no son obvias:

    - **OTRO nunca manda si hay algo más concreto.** «Otro, Instalación» es una
      incidencia de instalación que alguien además marcó como rara; dejar OTRO
      de principal escondería la información que sí hay. OTRO es la entrada de
      G12 —candidata a grupo nuevo—, no un cajón de sastre.
    - **Una celda vacía es OTRO**, no un error. 17 de las 119 no se etiquetaron,
      y omitirlas falsearía los totales.
    """
    codigos: List[str] = []
    for etiqueta in (crudo or "").split(","):
        codigo = MAPA_ETIQUETAS.get(_sin_acentos(etiqueta))
        if codigo and codigo not in codigos:
            codigos.append(codigo)

    if not codigos:
        return ["OTRO"]
    if codigos[0] == "OTRO" and len(codigos) > 1:
        return [c for c in codigos if c != "OTRO"] + ["OTRO"]
    return codigos


def leer_incidencias() -> List[Dict[str, Any]]:
    filas = _parsear_xlsx(str(EXCEL))
    if not filas:
        raise SystemExit(f"No se pudo leer {EXCEL}")

    cabecera = filas[0]
    indice = {c: i for i, c in enumerate(cabecera)}

    def columna(fragmento: str) -> str:
        for c in cabecera:
            if fragmento in c:
                return c
        raise SystemExit(f"Falta la columna que contiene '{fragmento}' en el Excel")

    C_PROB, C_COM = columna("roblema"), columna("omentario")
    C_ACC, C_EST = columna("cci"), columna("stado")
    C_NOM, C_DISP = columna("Nombre"), columna("Tipo de dispositivos")
    C_DIST, C_REF = columna("Distribuidor"), columna("ID Incidencia")
    C_VIV = columna("ID vivienda")

    def valor(fila: List[str], nombre: str) -> str:
        i = indice.get(nombre)
        return (fila[i].strip() if i is not None and len(fila) > i else "")

    incidencias = []
    for numero, fila in enumerate(filas[1:], start=1):
        etiquetas = valor(fila, C_PROB)
        codigos = grupos_de_etiquetas(etiquetas)
        comentario = valor(fila, C_COM)
        referencia = valor(fila, C_REF) or f"sin-ref-{numero}"

        incidencias.append({
            "numero_ticket": f"SAT-HIST-{numero:04d}",
            "referencia": referencia,
            "instalador": valor(fila, C_NOM) or "Sin nombre",
            "obra": valor(fila, C_VIV),
            "distribuidor": valor(fila, C_DIST),
            "dispositivo": valor(fila, C_DISP),
            # El síntoma es el comentario de SAT; si no lo hay, al menos las
            # etiquetas dicen de qué iba. Un síntoma vacío no se acepta.
            "sintoma": comentario or etiquetas or "Incidencia sin descripción",
            "solucion": valor(fila, C_ACC),
            "estado_origen": valor(fila, C_EST),
            "etiquetas_originales": etiquetas,
            "principal": codigos[0],
            "secundarios": codigos[1:],
        })
    return incidencias


def _estado(estado_origen: str) -> str:
    """«Resuelta» en el Excel es «resuelto» aquí; lo demás queda en espera."""
    return "resuelto" if _sin_acentos(estado_origen).startswith("resuelt") else "en_espera"


def importar(borrar_existentes: bool = False, dry_run: bool = False) -> Dict[str, int]:
    incidencias = leer_incidencias()
    stats = Counter()

    db = database.SessionLocal()
    try:
        if borrar_existentes and not dry_run:
            borrados = db.query(database.TicketSAT).delete()
            db.commit()
            stats["borrados"] = borrados
            print(f"Borrados {borrados} tickets previos.")
        elif borrar_existentes:
            stats["borrados"] = db.query(database.TicketSAT).count()

        grupos = {g.code: g.id for g in database.obtener_grupos_incidencia(db, solo_activos=False)}
        faltan = {c for i in incidencias for c in [i["principal"]] + i["secundarios"]} - set(grupos)
        if faltan:
            raise SystemExit(f"Estos grupos no existen en la base de datos: {sorted(faltan)}")

        for inc in incidencias:
            ya = db.query(database.TicketSAT).filter(
                database.TicketSAT.numero_ticket == inc["numero_ticket"]
            ).first()
            if ya:
                stats["omitidos"] += 1
                continue

            stats["importados"] += 1
            stats[f"grupo:{inc['principal']}"] += 1
            if inc["secundarios"]:
                stats["con_secundarios"] += 1
            if dry_run:
                continue

            ticket = database.TicketSAT(
                numero_ticket=inc["numero_ticket"],
                instalador=inc["instalador"],
                obra=inc["obra"],
                distribuidor=inc["distribuidor"],
                dispositivo=inc["dispositivo"],
                sintoma=inc["sintoma"],
                solucion=inc["solucion"],
                estado=_estado(inc["estado_origen"]),
                grupo_id=grupos[inc["principal"]],
                creado_por="importacion",
                notas=f"Importada de Incidencias.xlsx · ref {inc['referencia']} · "
                      f"etiquetas originales: {inc['etiquetas_originales'] or '(ninguna)'}",
            )
            db.add(ticket)
            db.flush()

            for codigo in inc["secundarios"]:
                db.add(database.TicketGrupoSecundario(ticket_id=ticket.id, grupo_id=grupos[codigo]))

        if not dry_run:
            db.commit()
    finally:
        db.close()

    return dict(stats)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="No escribe nada, solo informa.")
    parser.add_argument("--borrar-existentes", action="store_true",
                        help="Borra los tickets que haya antes de importar. IRREVERSIBLE.")
    args = parser.parse_args()

    stats = importar(borrar_existentes=args.borrar_existentes, dry_run=args.dry_run)

    print()
    print("EN SECO — no se ha escrito nada." if args.dry_run else "IMPORTACIÓN COMPLETADA")
    print(f"  importados        : {stats.get('importados', 0)}")
    print(f"  omitidos (ya iban): {stats.get('omitidos', 0)}")
    print(f"  con más de un grupo: {stats.get('con_secundarios', 0)}")
    print("  por grupo principal:")
    for clave, n in sorted(
        ((k, v) for k, v in stats.items() if k.startswith("grupo:")),
        key=lambda kv: -kv[1],
    ):
        print(f"      {n:>3}  {clave.split(':', 1)[1]}")


if __name__ == "__main__":
    main()
