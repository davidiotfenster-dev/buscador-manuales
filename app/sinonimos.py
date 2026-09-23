"""
Módulo de gestión y expansión de sinónimos técnicos para IoT Fenster.
Carga las reglas definidas en data/thesaurus_manuales.ths y expande
consultas de usuarios para que coincidan con la redacción técnica oficial de los manuales.
Soporta insensibilidad a tildes/acentos y correspondencia por límites de término.

El fichero se recarga solo cuando cambia en disco: añadir un sinónimo es editar
el .ths y guardar, sin reiniciar nada.
"""

import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger("buscador_manuales.sinonimos")

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_THS_PATH = BASE_DIR / "data" / "thesaurus_manuales.ths"


def _remover_acentos(texto: str) -> str:
    """Normaliza texto eliminando signos diacríticos (tildes, diéresis)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def _patron_frase(frase_norm: str) -> "re.Pattern[str]":
    """La frase delimitada por bordes de palabra o puntuación.

    Evita falsos positivos como 'red' dentro de 'pared'.
    """
    return re.compile(
        r'(?:(?<=[\s,;.:\-_/()\"\'`])|^)' + re.escape(frase_norm) + r'(?:(?=[\s,;.:\-_/()\"\'`])|$)'
    )


def _coincide_frase(frase_norm: str, q_norm: str, patron: Optional["re.Pattern[str]"] = None) -> bool:
    """
    Comprueba si frase_norm coincide en q_norm de manera exacta o delimitada
    por bordes de palabra/puntuación (evita falsos positivos como 'red' en 'pared').
    """
    if frase_norm == q_norm:
        return True
    return bool((patron or _patron_frase(frase_norm)).search(q_norm))


class GestorSinonimos:
    # Cada cuánto, como máximo, se mira si el fichero ha cambiado en disco.
    VIGENCIA_S = 5.0

    def __init__(self, ruta_ths: Path = DEFAULT_THS_PATH):
        self.ruta_ths = ruta_ths
        self.frase_a_target: Dict[str, str] = {}
        self.frases_ordenadas: List[Tuple[str, str]] = []  # (frase_norm, target) ordenadas por longitud desc
        self.target_a_frases: Dict[str, List[str]] = {}
        # Un patrón compilado por frase, en el mismo orden que frases_ordenadas.
        #
        # Antes se construía y compilaba la expresión regular de las 672 frases
        # EN CADA BÚSQUEDA. La caché de `re` guarda 512, así que con más frases
        # que eso se vaciaba sola y todas se recompilaban siempre: 66 ms por
        # consulta, más que todo el SQL junto. Compiladas una vez al cargar, la
        # expansión baja a menos de un milisegundo.
        self._patrones: List["re.Pattern[str]"] = []
        self._mtime: float = -1.0
        self._comprobado: float = 0.0
        self.cargar()

    def cargar(self) -> None:
        """Carga y parsea el archivo de tesauro .ths con normalización de acentos."""
        self.frase_a_target.clear()
        self.target_a_frases.clear()
        self.frases_ordenadas.clear()
        self._patrones = []

        if not self.ruta_ths.exists():
            logger.warning(f"Archivo de sinónimos no encontrado en {self.ruta_ths}")
            return

        try:
            with open(self.ruta_ths, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if ":" in line:
                        partes = line.split(":", 1)
                        frase = partes[0].strip().lower()
                        target = partes[1].strip().lower()
                        if not frase or not target:
                            continue

                        frase_norm = _remover_acentos(frase)
                        self.frase_a_target[frase_norm] = target

                        if target not in self.target_a_frases:
                            self.target_a_frases[target] = []
                        if frase not in self.target_a_frases[target]:
                            self.target_a_frases[target].append(frase)

            # Ordenar frases por longitud descendente para evaluar primero frases compuestas
            self.frases_ordenadas = sorted(
                self.frase_a_target.items(),
                key=lambda item: len(item[0]),
                reverse=True
            )
            self._patrones = [_patron_frase(f) for f, _ in self.frases_ordenadas]
            self._mtime = self.ruta_ths.stat().st_mtime

            logger.info(
                f"Cargados {len(self.frase_a_target)} términos hacia {len(self.target_a_frases)} conceptos técnicos."
            )
        except Exception as e:
            logger.error(f"Error cargando tesauro de sinónimos desde {self.ruta_ths}: {e}")

    def _recargar_si_cambio(self) -> None:
        """Recarga el tesauro si alguien lo ha editado.

        Antes se leía una sola vez al importar el módulo: añadir un sinónimo al
        .ths no servía de nada hasta reiniciar el servidor, y nada avisaba de
        ello. Ahora basta con guardar el fichero.
        """
        ahora = time.monotonic()
        if ahora - self._comprobado < self.VIGENCIA_S:
            return
        self._comprobado = ahora
        try:
            mtime = self.ruta_ths.stat().st_mtime
        except OSError:
            return
        if mtime != self._mtime:
            logger.info(f"El tesauro {self.ruta_ths.name} ha cambiado en disco: se recarga.")
            self.cargar()

    def _frases_que_coinciden(self, query: str) -> Iterator[Tuple[str, str, str]]:
        """(frase_norm, target, q_norm) de cada frase del tesauro presente en la consulta."""
        self._recargar_si_cambio()
        q_norm = _remover_acentos(query.strip().lower())
        for (frase_norm, target), patron in zip(self.frases_ordenadas, self._patrones):
            if _coincide_frase(frase_norm, q_norm, patron):
                yield frase_norm, target, q_norm

    def terminos_sinonimos(self, query: str, max_sinonimos: int = 3) -> List[str]:
        """Los términos que conviene buscar además de la consulta.

        Prioriza el término técnico objetivo (target) y después sus alternativas.
        Es lo que calcula `expandir_query`, pero como lista: el motor de búsqueda
        construye el tsquery él mismo en vez de volver a interpretar un texto con
        «or» que ya había pasado por aquí. Esa reinterpretación era justo lo que
        hacía que la consulta se expandiera dos veces.
        """
        if not query or not query.strip():
            return []
        terminos: List[str] = []
        for _frase_norm, target, q_norm in self._frases_que_coinciden(query):
            target_norm = _remover_acentos(target)
            if target_norm not in q_norm and target not in terminos and len(target) > 1:
                terminos.append(target)
            for alt in self.target_a_frases.get(target, []):
                alt_norm = _remover_acentos(alt)
                if alt_norm not in q_norm and alt not in terminos and len(alt) > 2:
                    terminos.append(alt)
        # Hasta max_sinonimos para no saturar el árbol de tsquery.
        return terminos[:max_sinonimos]

    def expandir_query(self, query: str, max_sinonimos: int = 3) -> str:
        """
        Si la query contiene un término/frase con sinónimos conocidos en el tesauro,
        expande la consulta con operadores 'or' para PostgreSQL websearch_to_tsquery.
        Prioriza siempre el término técnico objetivo (target).
        Soporta acentos de forma transparente.
        """
        if not query or not query.strip():
            return query

        q_orig = query.strip()
        principales = self.terminos_sinonimos(q_orig, max_sinonimos)
        if not principales:
            return q_orig
        partes_or = [f'"{s}"' if " " in s else s for s in principales]
        return f'{q_orig} or {" or ".join(partes_or)}'


# Instancia singleton para la aplicación
gestor_sinonimos = GestorSinonimos()


def expandir_query(query: str) -> str:
    """Función de conveniencia para expandir consultas con sinónimos técnicos."""
    return gestor_sinonimos.expandir_query(query)
