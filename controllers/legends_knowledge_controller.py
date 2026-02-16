# controllers/legends_knowledge_controller.py

class LegendsKnowledgeController:
    """
    Controlador para la pantalla "Legends Knowledge".

    - Navega de regreso al menú.
    - Abre el detalle de una leyenda específica.
    """

    def __init__(self, to_menu, open_legend):
        """
        Parámetros
        ----------
        to_menu : callable
            Acción para volver al menú inicial.
        open_legend : callable
            Acción para abrir el detalle: open_legend(legend_key: str)
        """
        self._to_menu = to_menu
        self._open_legend = open_legend

        # La llave es la que se usa internamente (y en los botones).
        # Las imágenes se esperan en: assets/images/legends/<filename>
        self.legends = [
            {
                "key": "La Cegua",
                "image": ("images", "legends", "cegua.jpg"),
                "text": (
                    "La Cegua is part of Costa Rican oral tradition. She usually appears on lonely roads at night, "
                    "where travelers are isolated and vulnerable. She looks like a beautiful woman, but when men "
                    "approach her, her face transforms into that of a horse. She punishes unfaithful or disrespectful men, "
                    "serving as a moral warning about deception and fidelity. The legend teaches that beauty can be deceiving "
                    "and that bad behavior has consequences."
                ),
            },
            {
                "key": "El Cadejos",
                "image": ("images", "legends", "cadejos.jpg"),
                "text": (
                    "El Cadejos is a supernatural dog that appears at night on lonely roads. There are two versions: "
                    "a white Cadejos that protects people who behave well, and a black Cadejos that harms or drives "
                    "bad people mad. He is sometimes described as dragging chains, which symbolize burden or punishment. "
                    "This legend warns travelers at night and reflects the dual nature of protection and danger, "
                    "teaching that a person’s actions determine what they face."
                ),
            },
            {
                "key": "La Tulevieja",
                "image": ("images", "legends", "tulevieja.jpg"),
                "text": (
                    "La Tulevieja is a spirit associated with rivers and crossroads in Costa Rican folklore. "
                    "She is often described as carrying a wicker basket on her back. According to the legend, "
                    "she is punished because of abandonment, and her figure symbolizes guilt and punishment. "
                    "Her presence serves as a moral lesson about responsibility and the consequences of harmful actions."
                ),
            },
            {
                "key": "La Llorona",
                "image": ("images", "legends", "llorona.jpg"),
                "text": (
                    "La Llorona is the spirit of a woman cursed for drowning her child. Her cries are heard "
                    "near rivers and dark places at night. She represents remorse, loss, and the tragic consequences "
                    "of her actions. Like other Costa Rican legends, her story is passed down through oral tradition "
                    "and serves as a warning to the community."
                ),
            },
            {
                "key": "La Mona",
                "image": ("images", "legends", "mona.jpg"),
                "text": (
                    "La Mona is a figure from Costa Rican oral tradition associated with mystery and fear at night. "
                    "According to the legend, a woman can transform into a strange creature that climbs rooftops "
                    "and trees to frighten people. She appears in dark and isolated places, reinforcing the idea "
                    "that harmful actions and negative intentions bring consequences. Like other legends, her story "
                    "serves as a moral warning and helps preserve cultural values within the community."
                ),
            },
        ]

    def on_back(self):
        self._to_menu()

    def on_open_legend(self, legend_key: str):
        self._open_legend(legend_key)
