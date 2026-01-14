# controllers/credits_controller.py
class CreditsController:
    """
    Controlador de Credits.
    - on_menu(): vuelve al menú principal.
    """

    def __init__(self, to_menu):
        self._to_menu = to_menu

    def on_menu(self):
        if callable(self._to_menu):
            self._to_menu()
