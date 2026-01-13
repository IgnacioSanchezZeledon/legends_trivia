class CongratulationsController:
    def __init__(self, switch_view, to_menu, to_levels):
        self.switch_view = switch_view
        self.to_menu = to_menu
        self.to_levels = to_levels

    def on_menu(self):
        self.to_menu()

    def on_levels(self):
        self.to_levels()
