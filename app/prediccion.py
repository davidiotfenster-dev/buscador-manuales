"""Predicción a partir de los casos ya vistos: grupo probable y tickets parecidos.

Qué resuelve
------------
El triaje tiene dos fuentes. Las reglas (`sat_autoresolver`) razonan sobre las
respuestas estructuradas del cuestionario. Esto razona sobre **lo que cuenta el
cliente**, comparándolo con todos los tickets que ya se han clasificado: qué
grupo de incidencia es probablemente, y qué casos parecidos se resolvieron y
cómo.

Lo que había antes para esto era `buscar_tickets_resueltos_similares`, una
búsqueda de texto de PostgreSQL que además recibía el síntoma sin tildes contra
un índice que guarda las raíces con tilde, e ignoraba el dispositivo que se le
pasaba.

Cómo se eligió el método
------------------------
Con evaluación «deja uno fuera» sobre los 103 tickets clasificados con texto
útil (cada ticket se predice usando solo los demás, y sin sus duplicados
exactos), 9 grupos:

    decir siempre la clase más frecuente (VINCULACION)     27,2 %
    búsqueda de texto de PostgreSQL (lo que había)         37,9 %   top-3 63,1 %
    palabras y pares de palabras, TF-IDF                   ~50 %    top-3 78,6 %
    n-gramas de caracteres, TF-IDF                          56,3 %   top-3 81,6 %
    n-gramas de caracteres + dispositivo, voto afinado      62,1 %   top-3 81,6 %

Ganan los n-gramas de caracteres porque los tickets están escritos deprisa:
«princiapl», «qu ellos», «Kommerling» sin diéresis. Un trozo de tres letras
sobrevive a una errata; una palabra entera, no. Se paró de afinar ahí a
propósito: con 103 casos, seguir moviendo parámetros sería ajustarse al ruido de
estos datos y no mejorar el sistema.

Para volver a medirlo con los datos que haya en cada momento:

    python tools/evaluar_prediccion.py

Se mantiene solo
----------------
El índice vive en memoria y se reconstruye cuando cambia la «firma» de los
tickets —recuento, id máximo, última modificación y recuento de clasificados—,
comprobada como mucho cada `VIGENCIA_S` segundos. Un ticket nuevo, reclasificado
o cerrado entra en la predicción sin que nadie haga nada: cuantos más tickets se
clasifican, mejor acierta.
"""

from __future__ import annotations

import logging
import math
import re
import threading
import time
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import text

logger = logging.getLogger("buscador_manuales.prediccion")

VIGENCIA_S = 30.0

# Vecinos que votan. Con sim² como peso, los más parecidos mandan y los del
# final solo desempatan.
K_VECINOS = 7
POTENCIA_VOTO = 2.0

# Por debajo de esto, un ticket no se enseña como «parecido»: comparte letras,
# no problema.
SIMILITUD_MINIMA_VECINO = 0.12

# Texto mínimo para intentar predecir. Con menos, la predicción es ruido.
LONGITUD_MINIMA_TEXTO = 12

# El dispositivo cuenta como si apareciera tres veces: pesa, pero no tapa al texto.
PESO_DISPOSITIVO = 3

# Los n-gramas que aparecen en más de esta fracción de tickets no distinguen
# nada (« de», «la ») y solo alargan el cálculo.
FRACCION_MAXIMA_DF = 0.5

SQL_FIRMA = text("""
    SELECT count(*), coalesce(max(id), 0), coalesce(max(fecha_actualizacion)::text, ''), count(grupo_id)
    FROM tickets_sat
""")

SQL_TICKETS = text("""
    SELECT t.id, t.numero_ticket, coalesce(t.sintoma, ''), coalesce(t.diagnostico, ''),
           coalesce(t.solucion, ''), coalesce(t.dispositivo, ''), coalesce(t.estado, ''),
           g.code, g.name
    FROM tickets_sat t
    LEFT JOIN incident_groups g ON g.id = t.grupo_id
""")


# ---------------------------------------------------------------------------
# Texto → rasgos
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    s = unicodedata.normalize("NFD", (texto or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9ñ]+", " ", s).split())


def rasgos(texto: str, dispositivo: str = "") -> Counter:
    """N-gramas de caracteres (3 a 5) y el dispositivo como rasgo propio."""
    s = f" {normalizar(texto)} "
    c: Counter = Counter()
    for n in (3, 4, 5):
        for i in range(len(s) - n + 1):
            g = s[i:i + n]
            if g.strip():
                c[g] += 1
    # «Konect Elite, Connect-2» son dos dispositivos: cada uno es un rasgo.
    for d in re.split(r"[,/;]+", dispositivo or ""):
        d = normalizar(d)
        if d:
            c["§disp:" + d] += PESO_DISPOSITIVO
    return c


def texto_utilizable(sintoma: str) -> bool:
    s = (sintoma or "").strip()
    return len(s) >= LONGITUD_MINIMA_TEXTO and "sin descripci" not in s.lower()


# ---------------------------------------------------------------------------
# Índice
# ---------------------------------------------------------------------------

class IndicePrediccion:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._firma: Optional[Tuple] = None
        self._comprobado = 0.0
        self.docs: List[Dict[str, Any]] = []
        self._idf: Dict[str, float] = {}
        self._idf_ausente = 1.0
        self._postings: Dict[str, List[Tuple[int, float]]] = {}

    # -- mantenimiento -----------------------------------------------------

    def _asegurar_vigente(self, db) -> None:
        ahora = time.monotonic()
        if self._firma is not None and ahora - self._comprobado < VIGENCIA_S:
            return
        with self._lock:
            if self._firma is not None and ahora - self._comprobado < VIGENCIA_S:
                return
            firma = tuple(db.execute(SQL_FIRMA).fetchone())
            self._comprobado = ahora
            if firma == self._firma:
                return
            self._construir(db.execute(SQL_TICKETS).fetchall())
            self._firma = firma

    def invalidar(self) -> None:
        with self._lock:
            self._firma = None

    def _construir(self, filas: Iterable) -> None:
        docs = []
        for f in filas:
            tid, numero, sintoma, diagnostico, solucion, dispositivo, estado, grupo, nombre_grupo = f
            if not texto_utilizable(sintoma):
                continue
            docs.append({
                "id": tid, "numero_ticket": numero, "sintoma": sintoma, "diagnostico": diagnostico,
                "solucion": solucion, "dispositivo": dispositivo, "estado": estado,
                "grupo": grupo, "nombre_grupo": nombre_grupo,
                "clave_duplicado": normalizar(sintoma),
                "_rasgos": rasgos(f"{sintoma} {diagnostico} {solucion}", dispositivo),
            })

        n = len(docs)
        df: Counter = Counter()
        for d in docs:
            df.update(d["_rasgos"].keys())
        idf = {t: math.log((n + 1) / (v + 1)) + 1.0 for t, v in df.items()}
        maximo_df = max(2, int(n * FRACCION_MAXIMA_DF))

        postings: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        for i, d in enumerate(docs):
            vec = {t: (1.0 + math.log(c)) * idf[t] for t, c in d["_rasgos"].items()}
            norma = math.sqrt(sum(x * x for x in vec.values())) or 1.0
            for t, x in vec.items():
                if df[t] <= maximo_df:
                    postings[t].append((i, x / norma))
            del d["_rasgos"]

        self.docs = docs
        self._idf = idf
        self._idf_ausente = math.log(n + 1) + 1.0
        self._postings = dict(postings)
        logger.info(
            f"Índice de predicción reconstruido: {n} tickets con texto, "
            f"{sum(1 for d in docs if d['grupo'])} clasificados."
        )

    # -- consulta ----------------------------------------------------------

    def _similitudes(self, texto: str, dispositivo: str) -> Dict[int, float]:
        r = rasgos(texto, dispositivo)
        vec = {t: (1.0 + math.log(c)) * self._idf.get(t, self._idf_ausente) for t, c in r.items()}
        norma = math.sqrt(sum(x * x for x in vec.values())) or 1.0
        acumulado: Dict[int, float] = defaultdict(float)
        for t, x in vec.items():
            peso = x / norma
            for i, w in self._postings.get(t, ()):
                acumulado[i] += peso * w
        return acumulado

    def predecir(self, db, texto: str, dispositivo: str = "", excluir_ids: Iterable[int] = (),
                 excluir_texto: str = "", vecinos: int = 3) -> Dict[str, Any]:
        """Grupo probable y tickets parecidos para lo que cuenta el cliente.

        `excluir_ids` y `excluir_texto` sirven para evaluar sin trampas: se
        predice un ticket sin dejar que se vea a sí mismo ni a sus copias.
        """
        vacio = {"grupo": None, "nombre_grupo": None, "confianza": 0.0, "ranking": [],
                 "vecinos": [], "base": 0}
        if not texto_utilizable(texto):
            return vacio
        self._asegurar_vigente(db)
        if not self.docs:
            return vacio

        excluir = set(excluir_ids)
        clave_excluida = normalizar(excluir_texto) if excluir_texto else None
        sims = self._similitudes(texto, dispositivo)
        orden = sorted(
            ((s, i) for i, s in sims.items()
             if self.docs[i]["id"] not in excluir
             and (clave_excluida is None or self.docs[i]["clave_duplicado"] != clave_excluida)),
            reverse=True,
        )

        votos: Dict[str, float] = defaultdict(float)
        nombres: Dict[str, str] = {}
        contados = 0
        for s, i in orden:
            d = self.docs[i]
            if not d["grupo"]:
                continue
            votos[d["grupo"]] += s ** POTENCIA_VOTO
            nombres[d["grupo"]] = d["nombre_grupo"] or d["grupo"]
            contados += 1
            if contados >= K_VECINOS:
                break

        total = sum(votos.values())
        ranking = [
            {"grupo": g, "nombre": nombres[g], "probabilidad": round(v / total, 3)}
            for g, v in sorted(votos.items(), key=lambda x: -x[1])
        ] if total > 0 else []

        parecidos = []
        for s, i in orden:
            if s < SIMILITUD_MINIMA_VECINO or len(parecidos) >= vecinos:
                break
            d = self.docs[i]
            parecidos.append({
                "ticket_id": d["id"], "numero_ticket": d["numero_ticket"], "sintoma": d["sintoma"],
                "diagnostico": d["diagnostico"], "solucion": d["solucion"], "dispositivo": d["dispositivo"],
                "estado": d["estado"], "grupo": d["grupo"], "similitud": round(s, 3),
            })

        return {
            "grupo": ranking[0]["grupo"] if ranking else None,
            "nombre_grupo": ranking[0]["nombre"] if ranking else None,
            # La fracción del voto que se lleva el grupo ganador. No es una
            # probabilidad calibrada: es cuánto se ponen de acuerdo los vecinos.
            "confianza": ranking[0]["probabilidad"] if ranking else 0.0,
            "ranking": ranking[:3],
            "vecinos": parecidos,
            # Con cuántos tickets clasificados se ha comparado. Diez no dicen lo
            # mismo que mil, y la interfaz debería poder saberlo.
            "base": sum(1 for d in self.docs if d["grupo"]),
        }

    # -- evaluación --------------------------------------------------------

    def evaluar(self, db) -> Dict[str, Any]:
        """Acierto «deja uno fuera» con los tickets clasificados que haya.

        Cada ticket se predice con todos los demás, sin él y sin sus
        duplicados exactos. Es la medida honesta de cómo acertaría con un caso
        nuevo, y cambia a medida que se clasifican más tickets.
        """
        self._asegurar_vigente(db)
        casos = [d for d in self.docs if d["grupo"]]
        if len(casos) < 5:
            return {"casos": len(casos), "acierto_1": None, "acierto_3": None,
                    "linea_base": None, "por_grupo": {}, "por_confianza": []}

        aciertos_1 = aciertos_3 = 0
        por_grupo: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
        tramos = [(0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
        por_tramo = {t: [0, 0] for t in tramos}
        for d in casos:
            p = self.predecir(db, d["sintoma"], d["dispositivo"],
                              excluir_ids=[d["id"]], excluir_texto=d["sintoma"])
            top = [r["grupo"] for r in p["ranking"]]
            ok1 = bool(top) and top[0] == d["grupo"]
            aciertos_1 += ok1
            aciertos_3 += d["grupo"] in top
            por_grupo[d["grupo"]][0] += ok1
            por_grupo[d["grupo"]][1] += 1
            for t in tramos:
                if t[0] <= p["confianza"] < t[1]:
                    por_tramo[t][0] += ok1
                    por_tramo[t][1] += 1

        n = len(casos)
        mayoritaria = Counter(d["grupo"] for d in casos).most_common(1)[0]
        return {
            "casos": n,
            "acierto_1": round(aciertos_1 / n, 3),
            "acierto_3": round(aciertos_3 / n, 3),
            "linea_base": {"grupo": mayoritaria[0], "acierto": round(mayoritaria[1] / n, 3)},
            "por_grupo": {g: {"aciertos": a, "casos": c, "acierto": round(a / c, 3)}
                          for g, (a, c) in sorted(por_grupo.items(), key=lambda x: -x[1][1])},
            # Si la confianza sirve para algo, los tramos altos deben acertar más.
            "por_confianza": [
                {"desde": t[0], "hasta": min(t[1], 1.0), "casos": c,
                 "acierto": round(a / c, 3) if c else None}
                for t, (a, c) in por_tramo.items()
            ],
        }


indice = IndicePrediccion()
