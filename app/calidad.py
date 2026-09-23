"""Cuánto acierta y cuánto tarda el sistema, medido con los datos que haya hoy.

Sirve para no tener que opinar. Cada vez que se meten manuales, vídeos o
tickets nuevos, esto dice si la búsqueda y la predicción han mejorado o
empeorado, con los mismos criterios con los que se ajustaron.

Dos formas de usarlo:

    # dentro del contenedor, con informe legible
    docker exec buscador_web python -m app.calidad

    # desde la aplicación, como administrador
    GET /api/sat/calidad

Qué mide
--------
Búsqueda. Usa como consultas los síntomas de los tickets, que es exactamente lo
que teclea un técnico:

- latencia (mediana y p95) y porcentaje de consultas sin ningún resultado;
- acierto aproximado: para los tickets de VINCULACION, CONECTIVIDAD,
  INSTALACION y APP —los grupos que tienen categoría de vídeo equivalente—, si
  entre los tres primeros vídeos hay uno de esa categoría. Es una medida
  aproximada: un vídeo puede ser útil sin estar en esa categoría. Sirve para
  comparar un cambio con otro, no como nota absoluta.

Predicción. Evaluación «deja uno fuera» sobre los tickets clasificados: cada uno
se predice con todos los demás, sin él y sin sus duplicados. Incluye el acierto
por tramo de confianza, que es lo que dice si la confianza que se enseña
significa algo.
"""

from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import text

# Grupos de ticket con una categoría de vídeo equivalente.
EQUIVALENCIA_GRUPO_VIDEO = {
    "VINCULACION": "VINCULACION",
    "CONECTIVIDAD": "CONECTIVIDAD",
    "INSTALACION": "INSTALACION",
    "APP": "CONFIGURACION_APP",
}


def _tamanos(db) -> Dict[str, int]:
    fila = db.execute(text("""
        SELECT (SELECT count(*) FROM manuales), (SELECT count(*) FROM paginas),
               (SELECT count(*) FROM videos), (SELECT count(*) FROM video_fragmentos),
               (SELECT count(*) FROM tickets_sat), (SELECT count(grupo_id) FROM tickets_sat)
    """)).fetchone()
    return {"manuales": fila[0], "paginas": fila[1], "videos": fila[2], "fragmentos": fila[3],
            "tickets": fila[4], "tickets_clasificados": fila[5]}


def medir_busqueda(db) -> Dict[str, Any]:
    from . import busqueda

    filas = db.execute(text("""
        SELECT t.sintoma, coalesce(t.dispositivo, ''), g.code
        FROM tickets_sat t LEFT JOIN incident_groups g ON g.id = t.grupo_id
        WHERE length(t.sintoma) >= 12 AND t.sintoma NOT ILIKE '%sin descripci%'
    """)).fetchall()
    if not filas:
        return {"consultas": 0}
    categoria_video = {vid: cat for vid, cat in db.execute(text("SELECT id, categoria FROM videos"))}

    tiempos, vacias, con_categoria, aciertos = [], 0, 0, 0
    for sintoma, _dispositivo, grupo in filas:
        t0 = time.perf_counter()
        prep = busqueda.preparar_consulta(db, sintoma, prefijo=False)
        manuales = busqueda.buscar_manuales(db, prep, limite=5)
        videos = busqueda.buscar_videos(db, prep, limite=5)
        tiempos.append((time.perf_counter() - t0) * 1000)
        if not manuales and not videos:
            vacias += 1
        esperada = EQUIVALENCIA_GRUPO_VIDEO.get(grupo or "")
        if esperada:
            con_categoria += 1
            aciertos += any(categoria_video.get(v["id"]) == esperada for v in videos[:3])

    tiempos.sort()
    return {
        "consultas": len(filas),
        "latencia_ms_mediana": round(statistics.median(tiempos), 1),
        "latencia_ms_p95": round(tiempos[max(0, int(len(tiempos) * 0.95) - 1)], 1),
        "sin_resultados": round(vacias / len(filas), 3),
        "video_de_la_categoria_en_top3": round(aciertos / con_categoria, 3) if con_categoria else None,
        "consultas_con_categoria": con_categoria,
    }


def informe(db) -> Dict[str, Any]:
    from .prediccion import indice

    return {
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "datos": _tamanos(db),
        "busqueda": medir_busqueda(db),
        "prediccion": indice.evaluar(db),
    }


def _pct(x) -> str:
    return "—" if x is None else f"{100 * x:.1f} %"


def imprimir(inf: Dict[str, Any]) -> None:
    d, b, p = inf["datos"], inf["busqueda"], inf["prediccion"]
    print(f"Informe de calidad · {inf['fecha']}")
    print(f"  Datos: {d['manuales']} manuales ({d['paginas']} páginas), {d['videos']} vídeos "
          f"({d['fragmentos']} fragmentos), {d['tickets']} tickets ({d['tickets_clasificados']} clasificados)")
    print("\nBúsqueda")
    if b.get("consultas"):
        print(f"  {b['consultas']} consultas reales (síntomas de tickets)")
        print(f"  latencia        mediana {b['latencia_ms_mediana']} ms · p95 {b['latencia_ms_p95']} ms")
        print(f"  sin resultados  {_pct(b['sin_resultados'])}")
        print(f"  vídeo de la categoría correcta en el top-3  {_pct(b['video_de_la_categoria_en_top3'])}"
              f"  ({b['consultas_con_categoria']} consultas)")
    else:
        print("  No hay tickets con síntoma para usar como consultas.")
    print("\nPredicción del grupo (deja uno fuera)")
    if p.get("acierto_1") is None:
        print(f"  Solo hay {p['casos']} tickets clasificados: hacen falta al menos 5 para medir.")
        return
    lb = p["linea_base"]
    print(f"  {p['casos']} tickets clasificados")
    print(f"  acierta el grupo       {_pct(p['acierto_1'])}")
    print(f"  grupo entre los 3 1os  {_pct(p['acierto_3'])}")
    print(f"  línea base             {_pct(lb['acierto'])}  (decir siempre {lb['grupo']})")
    print("  por confianza (si la confianza sirve, los tramos altos aciertan más):")
    for t in p["por_confianza"]:
        print(f"    {t['desde']:.1f}–{t['hasta']:.1f}   {t['casos']:4d} casos   acierta {_pct(t['acierto'])}")
    print("  por grupo:")
    for g, v in p["por_grupo"].items():
        print(f"    {g:14s} {v['aciertos']:3d}/{v['casos']:<3d}  {_pct(v['acierto'])}")


if __name__ == "__main__":
    import logging

    logging.disable(logging.WARNING)
    from . import database

    sesion = database.SessionLocal()
    try:
        imprimir(informe(sesion))
    finally:
        sesion.close()
