import json
import os
from utils.resource_path import resource_path

DEFAULT_LEVEL_SIZE = 5


class LevelsModel:
    """
    Modelo que gestiona la relación entre niveles y preguntas.

    - Carga la definición de niveles desde un archivo JSON.
    - Si no existe el archivo, genera automáticamente niveles
      agrupando las preguntas en bloques de tamaño fijo.
    """

    def __init__(self, questions_model, levels_path: str = "data/levels.json"):
        """
        Parámetros
        ----------
        questions_model : object
            Modelo de preguntas, debe exponer `all_ids() -> list[str]`.
        levels_path : str
            Ruta al archivo JSON con definición de niveles.
            Si no existe, se auto-generan los niveles en bloques de DEFAULT_LEVEL_SIZE.
        """
        self.qm = questions_model
        p = resource_path(levels_path)

        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                self.levels: dict[str, list[str]] = json.load(f)
        else:
            # Fallback: genera niveles automáticos
            ids = self.qm.all_ids()
            self.levels = {
                str(i // DEFAULT_LEVEL_SIZE + 1): ids[i : i + DEFAULT_LEVEL_SIZE]
                for i in range(0, len(ids), DEFAULT_LEVEL_SIZE)
            }

    def total_levels(self) -> int:
        """Devuelve el número total de niveles."""
        return len(self.levels)

    def questions_for_level(self, number: int) -> list[str]:
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
        return self.levels.get(str(number), [])
