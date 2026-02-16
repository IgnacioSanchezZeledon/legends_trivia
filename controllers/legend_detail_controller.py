# controllers/legend_detail_controller.py

class LegendDetailController:
    """
    Controlador para el detalle de una leyenda.

    - Regresa a la pantalla de 'Legends Knowledge'.
    """

    def __init__(self, to_legends):
        self._to_legends = to_legends

    def on_back(self):
        self._to_legends()
