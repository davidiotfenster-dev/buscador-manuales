"""Motor de búsqueda de manuales y vídeos.

Sustituye a las dos consultas que vivían dentro de `database.buscar()` y
`database.buscar_videos()`. Medido sobre la base real antes del cambio, con los
síntomas de los tickets como consultas —que es lo que teclea un técnico—:

    latencia            p50 147 ms   con solo 104 páginas indexadas
    sin ningún resultado 73 % de las consultas

Las causas, de mayor a menor peso:

1. **Todas las palabras eran obligatorias.** `websearch_to_tsquery` exige que
   TODOS los términos aparezcan en la misma página. «La persiana no sube cuando
   se le da la orden» casi nunca cumple eso, y la respuesta era cero resultados
   en vez de las páginas que más se parecían. Ahora basta con que aparezca
   alguno, y la página que los contiene todos sube arriba (se multiplica su
   relevancia): lo exacto primero, lo parecido después, nunca «nada».

2. **Las tildes.** «vinculacion» encontraba 1 página y «vinculación» 22;
   «instalacion», ninguna. Se resuelve en la consulta y no en el índice —ver
   `variantes_palabra()`, que explica por qué cambiar el índice a
   'spanish_unaccent' se probó y resultó peor—.

3. **Los sinónimos costaban 66 ms y se aplicaban dos veces.** Ver `sinonimos.py`.

4. **`ts_headline`, lo más caro, se calculaba para cada fragmento coincidente**
   (pueden ser cientos) antes de descartar los que no se muestran. Ahora solo
   se calcula para los resultados finales.

5. **El filtro no podía usar los índices.** Se comparaba contra
   `setweight(a) || setweight(b)`, una expresión calculada fila a fila que
   ningún índice cubre. Ahora se filtra con `a @@ q OR b @@ q`, que el
   planificador resuelve con los índices GIN en cuanto la tabla crece.

Además, lo que no existía:

- **Erratas.** Si una palabra de la consulta no aparece en ningún documento, se
  busca la más parecida del vocabulario real (trigramas) y se añade a la
  búsqueda. Se devuelve la corrección para poder enseñar «¿quisiste decir…?».
- **Palabra a medio escribir.** La última palabra se busca también como
  prefijo: «calib» encuentra «calibración».

Todo lo que depende de los datos se mantiene solo. El vocabulario de erratas se
reconstruye cuando cambia el número de páginas, manuales, vídeos o fragmentos,
comprobado como mucho cada `VIGENCIA_VOCABULARIO_S` segundos. Subir un manual,
reindexar o sincronizar el canal no exige tocar nada aquí.
"""

from __future__ import annotations

import logging
import threading
import time
import unicodedata
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import text

from .sinonimos import gestor_sinonimos

logger = logging.getLogger("buscador_manuales.busqueda")

CFG = "spanish"

# Cada cuánto, como máximo, se mira si los datos han cambiado. Es la demora
# máxima con la que un documento recién subido entra en la corrección de
# erratas; la búsqueda normal lo ve al instante, porque las columnas tsvector
# son generadas y el índice se actualiza en la misma transacción que el alta.
VIGENCIA_VOCABULARIO_S = 30.0

# Por debajo de esta similitud no se propone corrección: «bateria» y «batidora»
# se parecen, pero no son la misma palabra.
UMBRAL_CORRECCION = 0.45

# Las palabras muy cortas se corrigen mal: en tres letras cualquier cambio es
# otra palabra.
LONGITUD_MINIMA_CORRECCION = 4

# La página que contiene TODOS los términos pesa esto más que la que solo
# contiene alguno.
BONO_TODOS_LOS_TERMINOS = 2.0

OPCIONES_HEADLINE = "StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=15"


# ---------------------------------------------------------------------------
# Vocabulario para corregir erratas
# ---------------------------------------------------------------------------

def _trigramas(palabra: str) -> Set[str]:
    """Trigramas al estilo de pg_trgm: dos espacios delante y uno detrás."""
    p = f"  {palabra} "
    return {p[i:i + 3] for i in range(len(p) - 2)}


def similitud_trigramas(a: str, b: str) -> float:
    ta, tb = _trigramas(a), _trigramas(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def distancia_edicion(a: str, b: str) -> int:
    """Cambios de una letra para pasar de `a` a `b`, contando el intercambio de
    dos letras seguidas como UN cambio (distancia de Damerau restringida).

    Es lo que se le escapa a los trigramas: «vinuclar» por «vincular» o
    «perisana» por «persiana» —las erratas más típicas escribiendo deprisa en
    el móvil— se parecen solo un 0,38 por trigramas, por debajo del umbral,
    pero están a un solo cambio.
    """
    la, lb = len(a), len(b)
    anterior2: List[int] = []
    anterior = list(range(lb + 1))
    for i in range(1, la + 1):
        actual = [i] + [0] * lb
        for j in range(1, lb + 1):
            coste = 0 if a[i - 1] == b[j - 1] else 1
            actual[j] = min(anterior[j] + 1, actual[j - 1] + 1, anterior[j - 1] + coste)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                actual[j] = min(actual[j], anterior2[j - 2] + 1)
        anterior2, anterior = anterior, actual
    return anterior[lb]


def _cambios_tolerados(palabra: str) -> int:
    # En una palabra corta, dos cambios ya la convierten en otra palabra.
    return 1 if len(palabra) <= 7 else 2


class Vocabulario:
    """Lo que existe de verdad en los documentos indexados, para corregir erratas.

    Guarda dos cosas:

    - `frecuencia`: las RAÍCES (lexemas de la configuración 'spanish') y en
      cuántos documentos aparecen. Sirve para saber si una palabra de la
      consulta existe en el corpus.
    - `_palabras`: las PALABRAS tal como están escritas, sin tildes y con su
      forma original. Es contra esto contra lo que se corrige.

    Corregir contra raíces no funciona, y se descubrió así: el extractor de
    raíces solo recorta el sufijo si la palabra está bien escrita. «calibración»
    da «calibr», pero la errata «calibarcion» se queda en «calibarcion», y entre
    esas dos raíces el parecido es 0,36, por debajo del umbral. Palabra contra
    palabra —«calibarcion» contra «calibracion»— es 0,50. Así que se corrige a
    la palabra escrita y DESPUÉS se saca su raíz.

    Se reconstruye solo cuando cambia la «firma» de los datos (recuento y id
    máximo de cada tabla), consultada como mucho cada `VIGENCIA_VOCABULARIO_S`
    segundos: el coste por búsqueda es nulo en la práctica.
    """

    SQL_FIRMA = text("""
        SELECT (SELECT count(*) FROM paginas), (SELECT coalesce(max(id), 0) FROM paginas),
               (SELECT count(*) FROM manuales), (SELECT coalesce(max(id), 0) FROM manuales),
               (SELECT count(*) FROM videos), (SELECT coalesce(max(id), 0) FROM videos),
               (SELECT count(*) FROM video_fragmentos), (SELECT coalesce(max(id), 0) FROM video_fragmentos)
    """)

    SQL_LEXEMAS = text("""
        SELECT word, ndoc FROM ts_stat($$
            SELECT texto_tsv FROM paginas
            UNION ALL SELECT metadatos_tsv FROM manuales
            UNION ALL SELECT metadatos_tsv FROM videos
            UNION ALL SELECT texto_tsv FROM video_fragmentos
        $$)
    """)

    # 'simple' no extrae raíces ni quita palabras vacías: devuelve las palabras
    # tal cual, en minúsculas. Se calcula solo al reconstruir, no por búsqueda.
    SQL_PALABRAS = text("""
        SELECT word, ndoc FROM ts_stat($$
            SELECT to_tsvector('simple', texto) FROM paginas
            UNION ALL SELECT to_tsvector('simple', nombre_original || ' ' || coalesce(etiquetas, '')) FROM manuales
            UNION ALL SELECT to_tsvector('simple', titulo || ' ' || coalesce(etiquetas, '')) FROM videos
            UNION ALL SELECT to_tsvector('simple', texto) FROM video_fragmentos
        $$)
        WHERE length(word) >= 4 AND word !~ '[0-9]'
    """)

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._firma: Optional[Tuple] = None
        self._comprobado = 0.0
        self.frecuencia: Dict[str, int] = {}
        # palabra sin tildes -> (palabra original, documentos en que aparece)
        self._palabras: Dict[str, Tuple[str, int]] = {}
        self._por_trigrama: Dict[str, List[str]] = {}

    def _asegurar_vigente(self, db) -> None:
        ahora = time.monotonic()
        if self._firma is not None and ahora - self._comprobado < VIGENCIA_VOCABULARIO_S:
            return
        with self._lock:
            if self._firma is not None and ahora - self._comprobado < VIGENCIA_VOCABULARIO_S:
                return
            firma = tuple(db.execute(self.SQL_FIRMA).fetchone())
            self._comprobado = ahora
            if firma == self._firma:
                return
            frecuencia = {w: n for w, n in db.execute(self.SQL_LEXEMAS)}
            palabras: Dict[str, Tuple[str, int]] = {}
            for w, n in db.execute(self.SQL_PALABRAS):
                clave = _quitar_tildes(w)
                # Si una palabra aparece con y sin tilde, se queda la forma más
                # frecuente: casi siempre la bien escrita.
                if clave not in palabras or n > palabras[clave][1]:
                    palabras[clave] = (w, n)
            por_trigrama: Dict[str, List[str]] = defaultdict(list)
            for clave in palabras:
                for t in _trigramas(clave):
                    por_trigrama[t].append(clave)
            self.frecuencia = frecuencia
            self._palabras = palabras
            self._por_trigrama = dict(por_trigrama)
            self._firma = firma
            logger.info(
                f"Vocabulario de búsqueda reconstruido: {len(frecuencia)} raíces, {len(palabras)} palabras."
            )

    def invalidar(self) -> None:
        """Fuerza la reconstrucción en la siguiente búsqueda."""
        with self._lock:
            self._firma = None

    def contiene(self, db, lexema: str) -> bool:
        self._asegurar_vigente(db)
        return lexema in self.frecuencia

    def mas_parecida(self, db, palabra: str) -> Optional[str]:
        """La palabra del corpus más parecida a `palabra`, en su forma original.

        None si ninguna se parece lo bastante.
        """
        self._asegurar_vigente(db)
        clave = _quitar_tildes((palabra or "").lower())
        if len(clave) < LONGITUD_MINIMA_CORRECCION or clave.isdigit():
            return None
        candidatos: Set[str] = set()
        for t in _trigramas(clave):
            candidatos.update(self._por_trigrama.get(t, ()))
        tolerados = _cambios_tolerados(clave)
        mejor, mejor_orden = None, None
        for c in candidatos:
            sim = similitud_trigramas(clave, c)
            cambios = distancia_edicion(clave, c) if abs(len(c) - len(clave)) <= tolerados else 99
            # Vale si se parece por trigramas o si está a un par de cambios.
            if sim < UMBRAL_CORRECCION and cambios > tolerados:
                continue
            # Primero la que menos cambios necesita; luego la más parecida;
            # a igualdad, la que aparece en más documentos.
            orden = (cambios, -sim, -self._palabras[c][1])
            if mejor_orden is None or orden < mejor_orden:
                mejor, mejor_orden = c, orden
        return self._palabras[mejor][0] if mejor else None


vocabulario = Vocabulario()


# ---------------------------------------------------------------------------
# Construcción de la consulta
# ---------------------------------------------------------------------------

def _literal(lexema: str) -> str:
    """Un lexema como literal de tsquery, escapado."""
    return "'" + lexema.replace("\\", "\\\\").replace("'", "''") + "'"


def _quitar_tildes(palabra: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", palabra) if unicodedata.category(c) != "Mn")


# Sufijos que el extractor de raíces del español solo reconoce CON tilde.
# «instalación» → instal (la raíz de instalar, instalado, instalaciones), pero
# «instalacion», sin tilde, se queda en «instalacion» y ya no casa con nada de
# eso. Si el usuario no pone la tilde, se prueba también con ella.
_SUFIJOS_CON_TILDE = (("cion", "ción"), ("sion", "sión"), ("ia", "ía"))


def variantes_palabra(palabra: str) -> List[str]:
    """Las formas de una palabra que conviene buscar para que la tilde no importe.

    El índice se deja con la configuración 'spanish', que extrae bien las
    raíces. Se probó a cambiarlo a 'spanish_unaccent' y fue peor: esa
    configuración quita la tilde ANTES de extraer la raíz, el extractor deja de
    reconocer los sufijos acentuados, y «instalación» dejaba de encontrar
    «instalar», «instalado» e incluso «instalaciones». Así que las tildes se
    resuelven aquí, en la consulta, y en los dos sentidos:

    - sin tilde → se añade con tilde en el sufijo: «instalacion» → «instalación»
    - con tilde → se añade sin tilde, por los textos escritos sin ella (los
      tickets, sobre todo): «instalación» → «instalacion»
    """
    variantes = [palabra]
    sin = _quitar_tildes(palabra)
    if sin != palabra:
        variantes.append(sin)
    else:
        for sufijo, acentuado in _SUFIJOS_CON_TILDE:
            if palabra.lower().endswith(sufijo) and len(palabra) > len(sufijo) + 2:
                variantes.append(palabra[: -len(sufijo)] + acentuado)
                break
    return variantes


def _lexemas_de(db, textos: Iterable[str]) -> Dict[str, List[str]]:
    """Lexemas de cada texto, en el orden en que aparecen. Una sola consulta."""
    textos = list(dict.fromkeys(t for t in textos if t and t.strip()))
    if not textos:
        return {}
    filas = db.execute(
        text(f"""
            SELECT t, array_agg(l.lexeme ORDER BY l.positions[1])
            FROM unnest(CAST(:textos AS text[])) AS t,
                 unnest(to_tsvector('{CFG}', t)) AS l
            GROUP BY t
        """),
        {"textos": textos},
    ).fetchall()
    return {t: list(lex) for t, lex in filas}


def _grupo(literales: List[str]) -> str:
    literales = list(dict.fromkeys(literales))
    return literales[0] if len(literales) == 1 else "(" + " | ".join(literales) + ")"


def preparar_consulta(db, consulta: str, prefijo: bool = True) -> Dict[str, Any]:
    """Traduce lo que escribe el usuario a las dos consultas que se lanzan.

    Devuelve:
      - `tsquery`: la consulta amplia —basta con que aparezca alguna palabra—,
        como texto de tsquery, o None si no hay ninguna palabra con contenido.
      - `todas`: la consulta estricta —tienen que estar todas—. No filtra: solo
        sirve para dar el bono a las páginas que lo contienen todo.
      - `sinonimos` y `correcciones`: lo que se ha añadido, para poder
        explicarlo en la interfaz.

    Las dos se construyen aquí, palabra a palabra, y no con
    `websearch_to_tsquery`: así cada palabra lleva sus variantes con y sin tilde
    y su corrección de erratas, y la estricta sigue funcionando aunque el
    usuario no haya puesto ninguna tilde.
    """
    # Se mira ANTES de recortar: después del strip() nunca acaba en espacio.
    # Un espacio final quiere decir que la última palabra está completa.
    ultima_a_medias = prefijo and not (consulta or "").endswith(" ")
    consulta = (consulta or "").strip()
    vacia = {"tsquery": None, "todas": "", "sinonimos": [], "correcciones": []}
    if not consulta:
        return vacia

    # Exclusiones estilo buscador web: «persiana -gestual».
    tokens = consulta.split()
    excluidas = [t[1:] for t in tokens if t.startswith("-") and len(t) > 1]
    palabras = [t for t in tokens if not t.startswith("-")]

    variantes = {p: variantes_palabra(p) for p in palabras}
    sinonimos = gestor_sinonimos.terminos_sinonimos(" ".join(palabras))
    lexemas = _lexemas_de(db, [v for vs in variantes.values() for v in vs] + sinonimos + excluidas)

    # Un grupo por palabra: sus variantes, en OR. Las palabras vacías de
    # contenido («la», «no», «se»…) no dan lexemas y se quedan fuera solas.
    grupos: List[List[str]] = []
    palabra_de_grupo: List[str] = []
    for p in palabras:
        lex_palabra = [l for v in variantes[p] for l in lexemas.get(v, [])]
        if lex_palabra:
            grupos.append(list(dict.fromkeys(lex_palabra)))
            palabra_de_grupo.append(p)
    if not grupos:
        return {**vacia, "sinonimos": sinonimos}

    # Erratas: si ninguna variante de una palabra aparece en ningún documento,
    # se busca la PALABRA escrita más parecida del corpus y se añaden las raíces
    # de sus variantes. Se corrige palabra contra palabra, no raíz contra raíz:
    # ver `Vocabulario` para por qué lo segundo no funciona.
    correcciones = []
    try:
        for grupo, palabra in zip(grupos, palabra_de_grupo):
            if any(vocabulario.contiene(db, l) for l in grupo):
                continue
            sugerida = vocabulario.mas_parecida(db, palabra)
            if not sugerida or _quitar_tildes(sugerida.lower()) == _quitar_tildes(palabra.lower()):
                continue
            formas = variantes_palabra(sugerida)
            nuevas = [l for forma, lex in _lexemas_de(db, formas).items() for l in lex if l not in grupo]
            if nuevas:
                correcciones.append({"original": palabra, "sugerida": sugerida})
                grupo.extend(dict.fromkeys(nuevas))
    except Exception as e:  # la corrección es una ayuda: nunca puede tumbar la búsqueda
        logger.warning(f"No se pudo corregir la consulta «{consulta}»: {e}")

    literales_por_grupo = [[_literal(l) for l in g] for g in grupos]

    # La última palabra puede estar a medio escribir: se busca además como
    # prefijo. Solo si tiene cuerpo, o «a» acabaría encontrándolo todo. Las
    # consultas que arma el propio sistema (el triaje) no lo necesitan.
    if ultima_a_medias:
        ultimo = grupos[-1]
        literales_por_grupo[-1] += [_literal(l) + ":*" for l in ultimo if len(l) >= 3]

    amplia = [lit for g in literales_por_grupo for lit in g]
    for frase in sinonimos:
        lex_frase = lexemas.get(frase, [])
        if lex_frase:
            amplia.append(
                "(" + " & ".join(_literal(l) for l in lex_frase) + ")" if len(lex_frase) > 1
                else _literal(lex_frase[0])
            )

    tsquery = " | ".join(dict.fromkeys(amplia))
    todas = " & ".join(_grupo(g) for g in literales_por_grupo)

    lex_excluidas = [l for e in excluidas for l in lexemas.get(e, [])]
    for lex in dict.fromkeys(lex_excluidas):
        tsquery = f"({tsquery}) & !{_literal(lex)}"
        todas = f"({todas}) & !{_literal(lex)}"

    return {
        "tsquery": tsquery,
        "todas": todas,
        "sinonimos": sinonimos,
        "correcciones": correcciones,
    }


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def _filtros(prefijo: str, dispositivo: str, categoria: str, role: str) -> str:
    filtros = []
    # Sin distinguir mayúsculas: en la base conviven «CONNECT-1» y «Connect-1».
    if dispositivo:
        filtros.append(f"lower({prefijo}.dispositivo) = lower(:dispositivo)")
    if categoria:
        filtros.append(f"lower({prefijo}.categoria) = lower(:categoria)")
    if role == "comercial":
        filtros.append(f"{prefijo}.nivel_acceso = 'publico'")
    return " AND ".join(filtros) if filtros else "TRUE"


def buscar_manuales(db, prep: Dict[str, Any], dispositivo: str = "", categoria: str = "",
                    limite: int = 20, role: str = "admin") -> List[Dict[str, Any]]:
    if not prep.get("tsquery"):
        return []
    donde = _filtros("m", dispositivo, categoria, role)
    sql = text(f"""
        WITH q AS (
            SELECT CAST(:tsq AS tsquery) AS amplia,
                   CAST(:todas AS tsquery) AS todas
        ),
        coincidencias AS (
            SELECT m.id AS manual_id, m.nombre_original, m.nombre_archivo, m.dispositivo,
                   m.categoria, m.etiquetas, m.num_paginas, m.fecha_subida, m.nivel_acceso,
                   p.numero_pagina, p.texto,
                   COUNT(*) OVER (PARTITION BY m.id) AS paginas_coincidentes,
                   (numnode(q.todas) > 0 AND (m.metadatos_tsv || p.texto_tsv) @@ q.todas) AS completa,
                   ts_rank(setweight(m.metadatos_tsv, 'A') || setweight(p.texto_tsv, 'C'), q.amplia, 32)
                     * CASE WHEN numnode(q.todas) > 0 AND (m.metadatos_tsv || p.texto_tsv) @@ q.todas
                            THEN :bono ELSE 1.0 END AS relevancia
            FROM paginas p
            JOIN manuales m ON m.id = p.manual_id
            CROSS JOIN q
            WHERE {donde}
              AND (m.metadatos_tsv @@ q.amplia OR p.texto_tsv @@ q.amplia)
        ),
        mejor_por_manual AS (
            SELECT DISTINCT ON (manual_id) *
            FROM coincidencias
            ORDER BY manual_id, relevancia DESC, numero_pagina
        ),
        seleccion AS (
            SELECT * FROM mejor_por_manual ORDER BY relevancia DESC LIMIT :limite
        )
        -- El resaltado solo para lo que se va a enseñar.
        SELECT s.*, ts_headline('{CFG}', s.texto, (SELECT amplia FROM q), :opciones) AS fragmento
        FROM seleccion s
        ORDER BY s.relevancia DESC
    """)
    filas = db.execute(sql, {
        "tsq": prep["tsquery"], "todas": prep["todas"], "bono": BONO_TODOS_LOS_TERMINOS,
        "dispositivo": dispositivo, "categoria": categoria, "limite": limite,
        "opciones": OPCIONES_HEADLINE,
    }).fetchall()

    return [{
        "tipo": "manual",
        "id": f.manual_id,
        "manual_id": f.manual_id,
        "nombre": f.nombre_original,
        "nombre_original": f.nombre_original,
        "archivo": f.nombre_archivo,
        "nombre_archivo": f.nombre_archivo,
        "dispositivo": f.dispositivo,
        "categoria": f.categoria,
        "etiquetas": f.etiquetas or "",
        "num_paginas": f.num_paginas,
        "paginas": f.num_paginas,
        "fecha_subida": str(f.fecha_subida),
        "numero_pagina": f.numero_pagina,
        "pagina_encontrada": f.numero_pagina,
        "fragmento": f.fragmento,
        "relevancia": float(f.relevancia),
        "paginas_coincidentes": f.paginas_coincidentes,
        "nivel_acceso": f.nivel_acceso,
        # True si están TODOS los términos; False si solo algunos. Lo que antes
        # se deducía de que la búsqueda estricta devolviera algo o nada.
        "coincidencia_completa": bool(f.completa),
    } for f in filas]


def buscar_videos(db, prep: Dict[str, Any], dispositivo: str = "", categoria: str = "",
                  limite: int = 15, role: str = "admin") -> List[Dict[str, Any]]:
    if not prep.get("tsquery"):
        return []
    donde = _filtros("v", dispositivo, categoria, role)
    sql = text(f"""
        WITH q AS (
            SELECT CAST(:tsq AS tsquery) AS amplia,
                   CAST(:todas AS tsquery) AS todas
        ),
        coincidencias AS (
            SELECT v.id AS video_db_id, v.video_id, v.titulo, v.canal, v.url, v.miniatura_url,
                   v.dispositivo, v.categoria, v.etiquetas, v.nivel_acceso, v.fecha_subida,
                   COALESCE(vf.segundo_inicio, 0) AS segundo_inicio,
                   COALESCE(vf.texto, v.titulo) AS texto_fragmento,
                   (numnode(q.todas) > 0
                     AND (v.metadatos_tsv || COALESCE(vf.texto_tsv, v.transcripcion_tsv)) @@ q.todas) AS completa,
                   ts_rank(setweight(v.metadatos_tsv, 'A')
                           || setweight(COALESCE(vf.texto_tsv, v.transcripcion_tsv), 'C'), q.amplia, 32)
                     * CASE WHEN numnode(q.todas) > 0
                             AND (v.metadatos_tsv || COALESCE(vf.texto_tsv, v.transcripcion_tsv)) @@ q.todas
                            THEN :bono ELSE 1.0 END AS relevancia,
                   -- Sin el peso del título, que es igual para todos los
                   -- fragmentos del mismo vídeo: es lo que desempata para que
                   -- el enlace salte al trozo que de verdad habla de lo buscado
                   -- y no se quede en el segundo 0.
                   ts_rank(COALESCE(vf.texto_tsv, v.transcripcion_tsv), q.amplia, 32) AS relevancia_fragmento
            FROM videos v
            LEFT JOIN video_fragmentos vf ON vf.video_id = v.id
            CROSS JOIN q
            WHERE {donde}
              AND (v.metadatos_tsv @@ q.amplia
                   OR vf.texto_tsv @@ q.amplia
                   OR (vf.id IS NULL AND v.transcripcion_tsv @@ q.amplia))
        ),
        mejor_por_video AS (
            SELECT DISTINCT ON (video_db_id) *
            FROM coincidencias
            ORDER BY video_db_id, relevancia_fragmento DESC NULLS LAST, relevancia DESC, segundo_inicio
        ),
        seleccion AS (
            SELECT * FROM mejor_por_video ORDER BY relevancia DESC LIMIT :limite
        )
        SELECT s.*, ts_headline('{CFG}', s.texto_fragmento, (SELECT amplia FROM q), :opciones) AS fragmento
        FROM seleccion s
        ORDER BY s.relevancia DESC
    """)
    filas = db.execute(sql, {
        "tsq": prep["tsquery"], "todas": prep["todas"], "bono": BONO_TODOS_LOS_TERMINOS,
        "dispositivo": dispositivo, "categoria": categoria, "limite": limite,
        "opciones": OPCIONES_HEADLINE,
    }).fetchall()

    resultados = []
    for f in filas:
        segundos = int(f.segundo_inicio or 0)
        resultados.append({
            "tipo": "video",
            "id": f.video_db_id,
            "video_id": f.video_id,
            "nombre": f.titulo,
            "titulo": f.titulo,
            "canal": f.canal,
            "url": f"https://www.youtube.com/watch?v={f.video_id}&t={segundos}s",
            "url_embed": f"https://www.youtube.com/embed/{f.video_id}?start={segundos}&autoplay=1",
            "miniatura": f.miniatura_url,
            "dispositivo": f.dispositivo,
            "categoria": f.categoria,
            "etiquetas": f.etiquetas or "",
            "nivel_acceso": f.nivel_acceso,
            "segundo": segundos,
            "tiempo_formateado": f"{segundos // 60:02d}:{segundos % 60:02d}",
            "fragmento": f.fragmento,
            "relevancia": float(f.relevancia),
            "fecha_subida": str(f.fecha_subida),
            "coincidencia_completa": bool(f.completa),
        })
    return resultados
