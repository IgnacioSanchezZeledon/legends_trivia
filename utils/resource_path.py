# utils/resource_path.py
import os
import sys
from typing import Union


def _base_dir() -> str:
    """
    Determina la base adecuada para resolver rutas de recursos:
      - PyInstaller (one-file): carpeta temporal _MEIPASS
      - PyInstaller (one-folder/frozen): carpeta del ejecutable
      - Desarrollo: raíz del proyecto (padre de utils/)
    """
    # PyInstaller one-file
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS  # type: ignore[attr-defined]

    # PyInstaller one-folder / ejecutable frozen
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    # Desarrollo: asumir que 'utils/' vive justo dentro de la raíz del proyecto
    #   .../tu_proyecto/utils/resource_path.py -> subir un nivel
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resource_path(relative: Union[str, os.PathLike]) -> str:
    """
    Devuelve una ruta absoluta al recurso, independientemente de dist/ o _MEIPASS.
    Acepta rutas tipo "assets/..." o "data/...".
    """
    return os.path.join(_base_dir(), str(relative))


# Helpers convenientes (evitan concatenaciones en el resto del código)
def assets_path(*parts: str) -> str:
    return resource_path(os.path.join("assets", *parts))


def data_path(*parts: str) -> str:
    return resource_path(os.path.join("data", *parts))
