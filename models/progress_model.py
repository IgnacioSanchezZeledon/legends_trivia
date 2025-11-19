import json
import os


class ProgressModel:
    """
    Modelo de progreso del jugador.

    Funcionalidad:
      - Persiste y recupera el estado de progreso desde un archivo JSON.
      - Almacena:
          * nivel más alto desbloqueado,
          * estrellas obtenidas por nivel.
      - Permite actualizar estrellas, desbloquear nuevos niveles y consultar estado.
    """

    def __init__(self, path: str = "progress.json"):
        """
        Parámetros
        ----------
        path : str
            Ruta al archivo JSON donde se guarda el progreso.
        """
        self.path = path
        self.data: dict = {"unlocked": 1, "stars": {}}

        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                # Si el archivo está corrupto o no se puede leer, inicia en estado base
                pass

    def save(self) -> None:
        """Guarda el progreso actual en el archivo JSON."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def unlocked(self) -> int:
        """Devuelve el número del último nivel desbloqueado (1 por defecto)."""
        return self.data.get("unlocked", 1)

    def unlock_next(self, level: int) -> None:
        """
        Desbloquea el siguiente nivel después del indicado.

        Parámetros
        ----------
        level : int
            Número de nivel que acaba de completarse.
        """
        if self.unlocked() < level + 1:
            self.data["unlocked"] = level + 1
            self.save()

    def set_stars(self, level: int, stars: int) -> None:
        """
        Establece la cantidad de estrellas obtenidas en un nivel (0 a 3).

        Parámetros
        ----------
        level : int
            Número del nivel.
        stars : int
            Estrellas a registrar (se limita entre 0 y 3).
        """
        self.data["stars"][str(level)] = max(0, min(3, stars))
        self.save()

    def stars_for(self, level: int) -> int:
        """
        Devuelve el número de estrellas obtenidas en un nivel.

        Parámetros
        ----------
        level : int
            Número del nivel.

        Retorna
        -------
        int
            Cantidad de estrellas (0 si no tiene registro).
        """
        return int(self.data.get("stars", {}).get(str(level), 0))
