# models/levels_model.py
import json
import os
from typing import Dict, List
from utils.resource_path import resource_path

DEFAULT_LEVEL_SIZE = 5


class LevelsModel:
    """
    Modelo que gestiona la relación entre niveles y preguntas.

    - Carga la definición de niveles desde un archivo JSON.
    - Si no existe el archivo, genera automáticamente niveles
      agrupando las preguntas en bloques de tamaño fijo.
    """

    def __init__(self, questions_model, levels_path: str = "data/levels.json", default_level_size: int = DEFAULT_LEVEL_SIZE):
        """
        Parámetros
        ----------
        questions_model : object
            Modelo de preguntas, debe exponer `all_ids() -> list[str]`.
        levels_path : str
            Ruta al archivo JSON con definición de niveles.
            Si no existe, se auto-generan los niveles en bloques de DEFAULT_LEVEL_SIZE.
        default_level_size : int
            Tamaño del bloque cuando se auto-generan niveles.
        """
        self.qm = questions_model
        self.default_level_size = int(default_level_size)
        self.levels_path = levels_path

        p = resource_path(levels_path)

        data = None
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[LevelsModel] Error leyendo {p}. Se regenerarán niveles. Detalle: {e}")
                data = None

        # Normalizar estructura cargada o generar fallback
        self.levels: Dict[str, List[str]] = self._normalize_levels(data) if data else self._generate_levels()

    # ---------------- API pública ----------------
    def total_levels(self) -> int:
        """Devuelve el número total de niveles."""
        return len(self.levels)

    def questions_for_level(self, number: int) -> List[str]:
        """
        Devuelve la lista de IDs de preguntas asociadas a un nivel.

        Parámetros
        ----------
        number : int
            Número del nivel a consultar.

        Retorna
        -------
        list[str]
            Lista de IDs de preguntas para ese nivel, o lista vacía si no existe.
        """
        return self.levels.get(str(int(number)), [])

    def level_numbers(self) -> List[int]:
        """Devuelve la lista de niveles disponibles como enteros ordenados."""
        out = []
        for k in self.levels.keys():
            try:
                out.append(int(k))
            except Exception:
                pass
        return sorted(out)

    # ---------------- Internos ----------------
    def _generate_levels(self) -> Dict[str, List[str]]:
        """Genera niveles automáticamente en bloques de tamaño fijo."""
        ids = list(self.qm.all_ids())
        size = max(1, self.default_level_size)
        return {
            str(i // size + 1): ids[i: i + size]
            for i in range(0, len(ids), size)
        }

    def _normalize_levels(self, data) -> Dict[str, List[str]]:
        """
        Acepta varias formas válidas de JSON y devuelve siempre:
          Dict[str, List[str]]
        Soporta:
          - dict: {"1": ["q1","q2"], "2": [...]}
          - list: [["q1","q2"], ["q3","q4"]]  -> niveles 1..N
        También ordena por número si las llaves son numéricas.
        """
        # Caso 1: lista de listas (niveles por posición)
        if isinstance(data, list):
            normalized: Dict[str, List[str]] = {}
            for i, block in enumerate(data, start=1):
                if isinstance(block, list):
                    normalized[str(i)] = [str(x) for x in block]
            return normalized if normalized else self._generate_levels()

        # Caso 2: dict
        if isinstance(data, dict):
            tmp: Dict[str, List[str]] = {}
            for k, v in data.items():
                key = str(k)
                if isinstance(v, list):
                    tmp[key] = [str(x) for x in v]
                else:
                    tmp[key] = []

            # Reordenar si las llaves son numéricas (para consistencia)
            numeric_keys = []
            non_numeric_keys = []
            for k in tmp.keys():
                try:
                    numeric_keys.append(int(k))
                except Exception:
                    non_numeric_keys.append(k)

            normalized: Dict[str, List[str]] = {}
            for nk in sorted(numeric_keys):
                normalized[str(nk)] = tmp.get(str(nk), [])
            for k in sorted(non_numeric_keys):
                normalized[k] = tmp.get(k, [])

            return normalized if normalized else self._generate_levels()

        # Si viene algo raro, regenerar
        return self._generate_levels()
