"""
Módulo de gestión y expansión de sinónimos técnicos para IoT Fenster.
Carga las reglas definidas en data/thesaurus_manuales.ths y expande
consultas de usuarios para que coincidan con la redacción técnica oficial de los manuales.
Soporta insensibilidad a tildes/acentos y correspondencia por límites de término.
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger("buscador_manuales.sinonimos")

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_THS_PATH = BASE_DIR / "data" / "thesaurus_manuales.ths"


def _remover_acentos(texto: str) -> str:
    """Normaliza texto eliminando signos diacríticos (tildes, diéresis)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def _coincide_frase(frase_norm: str, q_norm: str) -> bool:
    """
    Comprueba si frase_norm coincide en q_norm de manera exacta o delimitada
    por bordes de palabra/puntuación (evita falsos positivos como 'red' en 'pared').
    """
    if frase_norm == q_norm:
        return True
    patron = r'(?:(?<=[\s,;.:\-_/()\"\'`])|^)' + re.escape(frase_norm) + r'(?:(?=[\s,;.:\-_/()\"\'`])|$)'
    return bool(re.search(patron, q_norm))


class GestorSinonimos:
    def __init__(self, ruta_ths: Path = DEFAULT_THS_PATH):
        self.ruta_ths = ruta_ths
        self.frase_a_target: Dict[str, str] = {}
        self.frases_ordenadas: List[Tuple[str, str]] = []  # (frase_norm, target) ordenadas por longitud desc
        self.target_a_frases: Dict[str, List[str]] = {}
        self.cargar()

    def cargar(self) -> None:
        """Carga y parsea el archivo de tesauro .ths con normalización de acentos."""
        self.frase_a_target.clear()
        self.target_a_frases.clear()
        self.frases_ordenadas.clear()

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

            logger.info(
                f"Cargados {len(self.frase_a_target)} términos hacia {len(self.target_a_frases)} conceptos técnicos."
            )
        except Exception as e:
            logger.error(f"Error cargando tesauro de sinónimos desde {self.ruta_ths}: {e}")

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
        q_norm = _remover_acentos(q_orig.lower())
        terminos_a_incluir: List[str] = []

        for frase_norm, target in self.frases_ordenadas:
            if _coincide_frase(frase_norm, q_norm):
                target_norm = _remover_acentos(target)
                # 1. Priorizar el término técnico objetivo (target) si no está en la query
                if target_norm not in q_norm and target not in terminos_a_incluir and len(target) > 1:
                    terminos_a_incluir.append(target)

                # 2. Añadir sinónimos alternativos
                for alt in self.target_a_frases.get(target, []):
                    alt_norm = _remover_acentos(alt)
                    if alt_norm not in q_norm and alt not in terminos_a_incluir and len(alt) > 2:
                        terminos_a_incluir.append(alt)

        if not terminos_a_incluir:
            return q_orig

        # Seleccionar hasta max_sinonimos para no saturar el árbol de tsquery
        principales = terminos_a_incluir[:max_sinonimos]
        partes_or = [f'"{s}"' if " " in s else s for s in principales]
        return f'{q_orig} or {" or ".join(partes_or)}'


# Instancia singleton para la aplicación
gestor_sinonimos = GestorSinonimos()


def expandir_query(query: str) -> str:
    """Función de conveniencia para expandir consultas con sinónimos técnicos."""
    return gestor_sinonimos.expandir_query(query)
