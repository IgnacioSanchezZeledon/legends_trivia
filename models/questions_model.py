import json
from utils.resource_path import resource_path



class QuestionModel:
    """
    Modelo de preguntas del juego.

    - Carga todas las preguntas desde un archivo JSON.
    - Indexa preguntas por su ID para acceso rápido.
    - Permite obtener una pregunta específica o la lista de todos los IDs.
    """

    def __init__(self, data_path: str = "data/questions.json"):
        """
        Parámetros
        ----------
        data_path : str
            Ruta al archivo JSON con las preguntas.
            Cada entrada debe contener al menos un campo "id".
        """
        with open(resource_path(data_path), "r", encoding="utf-8") as f:
            self.questions: list[dict] = json.load(f)

        # Diccionario de acceso rápido: id -> pregunta
        self.by_id: dict[str, dict] = {q["id"]: q for q in self.questions}

    def get(self, qid: str) -> dict:
        """
        Devuelve la pregunta asociada a un ID.

        Parámetros
        ----------
        qid : str
            Identificador único de la pregunta.

        Retorna
        -------
        dict
            Diccionario con los datos de la pregunta.
        """
        return self.by_id[qid]

    def all_ids(self) -> list[str]:
        """
        Devuelve la lista de todos los IDs de preguntas disponibles.

        Retorna
        -------
        list[str]
            Lista de IDs de todas las preguntas.
        """
        return [q["id"] for q in self.questions]
