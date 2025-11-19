class LevelsController:
    """
    Controlador para la vista de selección de niveles.

    Responsabilidades:
      - Manejar la navegación al menú principal (on_menu).
      - Manejar la selección de un nivel para abrir la vista de juego.
    """

    def __init__(self, switch_view, play_view_factory, progress_model):
        """
        Parámetros
        ----------
        switch_view : callable
            Función que monta la vista recibida en el contenedor principal.
        play_view_factory : callable
            Fábrica que recibe un número de nivel y devuelve una instancia de PlayView.
        progress_model : object
            Modelo de progreso (permite consultar/desbloquear niveles y estrellas).
        """
        self.switch_view = switch_view
        self.play_view_factory = play_view_factory
        self.progress = progress_model

    def on_menu(self):
        """
        Navega de vuelta al menú principal.
        Nota: este método se sobreescribe/inyecta desde App.
        """
        pass

    def on_pick_level(self, level_number: int):
        """
        Abre el nivel indicado en la vista de juego.

        Parámetros
        ----------
        level_number : int
            Número del nivel seleccionado.
        """
        self.switch_view(self.play_view_factory(level_number))
