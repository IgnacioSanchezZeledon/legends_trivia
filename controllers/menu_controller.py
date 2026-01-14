# controllers/menu_controller.py

class MenuController:
    """
    Controlador para la vista de Menú.

    Responsabilidades:
      - Manejar navegación al mapa de niveles (Play).
      - Manejar navegación a Credits.
      - Manejar salida de la aplicación (Exit).
    """

    def __init__(self, switch_view, levels_view_factory, credits_view_factory=None):
        """
        Parámetros
        ----------
        switch_view : callable
            Función que monta la vista recibida en el contenedor principal.
        levels_view_factory : callable
            Fábrica que devuelve una instancia de LevelsView.
        credits_view_factory : callable | None
            Fábrica que devuelve una instancia de CreditsView (opcional).
        """
        self.switch_view = switch_view
        self.levels_view_factory = levels_view_factory
        self.credits_view_factory = credits_view_factory

    def on_play(self):
        """Construye LevelsView y cambia la vista hacia el mapa de niveles."""
        self.switch_view(self.levels_view_factory())

    def on_credits(self):
        """Construye CreditsView y cambia la vista a la pantalla de créditos."""
        if not self.credits_view_factory:
            return
        self.switch_view(self.credits_view_factory())

    def on_exit(self):
        """Sale de la aplicación de forma inmediata."""
        import sys
        sys.exit(0)
