class MenuController:
    """
    Controlador para la vista de Menú.

    Responsabilidades:
      - Manejar navegación al mapa de niveles (Play).
      - Manejar salida de la aplicación (Exit).
    """

    def __init__(self, switch_view, levels_view_factory):
        """
        Parámetros
        ----------
        switch_view : callable
            Función que monta la vista recibida en el contenedor principal.
        levels_view_factory : callable
            Fábrica que devuelve una instancia de LevelsView.
        """
        self.switch_view = switch_view
        self.levels_view_factory = levels_view_factory

    def on_play(self):
        """Construye LevelsView y cambia la vista hacia el mapa de niveles."""
        self.switch_view(self.levels_view_factory())

    def on_exit(self):
        """Sale de la aplicación de forma inmediata."""
        import sys
        sys.exit(0)
