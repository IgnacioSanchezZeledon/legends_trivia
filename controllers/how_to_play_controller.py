# controllers/how_to_play_controller.py

class HowToPlayController:
    """
    Controlador de How To Play.
    - on_quit(): vuelve al menú principal (lo que pediste como "Quit").
    """

    def __init__(self, to_menu):
        self._to_menu = to_menu

    def on_quit(self):
        if callable(self._to_menu):
            self._to_menu()
