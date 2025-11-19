# utils/styles.py
import os
import shutil
import tempfile
import platform
from tkinter import ttk, font
import sys

from utils.resource_path import assets_path

# Archivos TTF esperados dentro de assets/fonts
MIKADO_FILES = [
    "MikadoRegular.ttf",
    "MikadoBold.ttf",
    "MikadoLight.ttf",
    "MikadoBlack.ttf",
    "MikadoUltra.ttf",
    "MikadoRegularItalic.ttf",
    "MikadoBoldItalic.ttf",
    "MikadoLightItalic.ttf",
    "MikadoBlackItalic.ttf",
    "MikadoUltraItalic.ttf",
]


def _install_fonts_to_temp(fonts_dir: str) -> dict:
    """
    Copia las fuentes TTF a una carpeta temporal y las registra usando gdi32.dll (Windows)
    o usando métodos específicos del OS.
    """
    families = {}
    if not os.path.isdir(fonts_dir):
        print(f"Directorio de fuentes no existe: {fonts_dir}")
        return families

    # Crear directorio temporal para fuentes
    temp_fonts_dir = os.path.join(tempfile.gettempdir(), "legends_trivia_fonts")
    os.makedirs(temp_fonts_dir, exist_ok=True)

    # Mapeo de archivos a roles
    file_to_role = {
        "MikadoRegular.ttf": "base",
        "MikadoBold.ttf": "bold", 
        "MikadoLight.ttf": "light",
        "MikadoBlack.ttf": "black",
        "MikadoUltra.ttf": "ultra",
    }

    registered_fonts = []
    
    for fname, role in file_to_role.items():
        font_path = os.path.join(fonts_dir, fname)
        if os.path.exists(font_path):
            temp_font_path = os.path.join(temp_fonts_dir, fname)
            
            try:
                # Copiar fuente a directorio temporal
                if not os.path.exists(temp_font_path):
                    shutil.copy2(font_path, temp_font_path)
                    print(f"Fuente copiada: {fname} -> {temp_font_path}")
                
                # Registrar fuente según el OS
                success = False
                if platform.system() == "Windows":
                    success = _register_font_windows(temp_font_path, f"Mikado-{role.capitalize()}")
                elif platform.system() == "Darwin":  # macOS
                    success = _register_font_macos(temp_font_path)
                else:  # Linux
                    success = _register_font_linux(temp_font_path)
                
                if success:
                    families[role] = f"Mikado-{role.capitalize()}"
                    registered_fonts.append(fname)
                    print(f"Fuente registrada: {fname} -> Mikado-{role.capitalize()}")
                
            except Exception as e:
                print(f"Error procesando {fname}: {e}")

    if registered_fonts:
        print(f"Total fuentes Mikado registradas: {len(registered_fonts)}")
    else:
        print("No se pudieron registrar fuentes Mikado")
    
    return families


def _register_font_windows(font_path: str, family_name: str = "") -> bool:
    """Registra una fuente en Windows usando gdi32.dll"""
    try:
        import ctypes
        from ctypes import wintypes
        
        gdi32 = ctypes.windll.gdi32
        FR_PRIVATE = 0x10
        
        # Registrar fuente temporalmente
        result = gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
        if result > 0:
            # Notificar cambio de fuentes
            user32 = ctypes.windll.user32
            user32.PostMessageW(0xFFFF, 0x001D, 0, 0)  # WM_FONTCHANGE
            return True
        else:
            print(f"AddFontResourceExW falló para {font_path}")
            return False
            
    except Exception as e:
        print(f"Error registrando fuente en Windows: {e}")
        return False


def _register_font_macos(font_path: str) -> bool:
    """Registra una fuente en macOS"""
    try:
        # En macOS, podemos usar CoreText pero es complejo
        # Por ahora, asumimos que está disponible si el archivo existe
        return True
    except Exception as e:
        print(f"Error registrando fuente en macOS: {e}")
        return False


def _register_font_linux(font_path: str) -> bool:
    """Registra una fuente en Linux"""
    try:
        # En Linux, podemos usar fontconfig pero es complejo
        # Por ahora, asumimos que está disponible si el archivo existe
        return True
    except Exception as e:
        print(f"Error registrando fuente en Linux: {e}")
        return False


def apply_theme(root, base_dir: str | None = None) -> bool:
    """
    Aplica estilos ttk y registra fuentes Mikado si están en assets/fonts.
    Retorna True si se cargaron las fuentes Mikado correctamente.
    """
    # Localización de fuentes compatible con ejecución normal y con PyInstaller
    fonts_dir = assets_path("fonts")
    print(f"Buscando fuentes en: {fonts_dir}")
    
    # Cargar fuentes Mikado
    mikado_families = _install_fonts_to_temp(fonts_dir)
    
    # Determinar qué fuentes usar
    has_mikado = bool(mikado_families)
    
    # Seleccionar fuentes por peso/estilo
    base_font = mikado_families.get("base", "Arial")
    bold_font = mikado_families.get("bold", base_font)
    light_font = mikado_families.get("light", base_font)
    black_font = mikado_families.get("black", bold_font)
    ultra_font = mikado_families.get("ultra", black_font)
    
    print(f"Fuentes seleccionadas:")
    print(f"  Base: {base_font}")
    print(f"  Bold: {bold_font}")
    print(f"  Light: {light_font}")
    print(f"  Black: {black_font}")
    print(f"  Ultra: {ultra_font}")
    print(f"¿Mikado disponible?: {'Sí' if has_mikado else 'No (usando Arial)'}")
    
    # Aplicar estilos ttk
    style = ttk.Style(root)
    style.theme_use("clam")
    
    # Colores del tema
    BG_COLOR = "#27474b"
    CARD_COLOR = "#2d4f54"
    TEXT_COLOR = "#ecf0f1"
    SUBTITLE_COLOR = "#cfd8dc"
    SMALL_TEXT_COLOR = "#b0bec5"
    
    # Configurar estilos base
    style.configure("Screen.TFrame", background=BG_COLOR)
    style.configure("Card.TFrame", background=CARD_COLOR)
    
    # Estilos de texto con fuentes apropiadas
    style.configure("TLabel", 
                   background=BG_COLOR, 
                   foreground=TEXT_COLOR, 
                   font=(base_font, 12))
    
    style.configure("Header.TLabel", 
                   background=BG_COLOR, 
                   foreground=TEXT_COLOR, 
                   font=(bold_font, 18))
    
    style.configure("Title.TLabel", 
                   background=BG_COLOR, 
                   foreground=TEXT_COLOR, 
                   font=(black_font, 24))
    
    style.configure("BigTitle.TLabel", 
                   background=BG_COLOR, 
                   foreground=TEXT_COLOR, 
                   font=(ultra_font, 32))
    
    style.configure("Subtitle.TLabel", 
                   background=BG_COLOR, 
                   foreground=SUBTITLE_COLOR, 
                   font=(base_font, 14))
    
    style.configure("Small.TLabel", 
                   background=BG_COLOR, 
                   foreground=SMALL_TEXT_COLOR, 
                   font=(light_font, 10))
    
    # Estilos de botones
    style.configure("Choice.TButton", 
                   padding=(12, 10), 
                   font=(base_font, 12))
    
    style.configure("MainButton.TButton", 
                   padding=(20, 15), 
                   font=(bold_font, 14))
    
    # Estilos de frames específicos
    style.configure("Question.TFrame", 
                   background=CARD_COLOR, 
                   relief="flat")
    
    return has_mikado


def get_mikado_font(weight: str = "base", size: int = 12) -> tuple:
    """
    Retorna una tupla (familia, tamaño) apropiada para el peso solicitado.
    """
    weight_map = {
        "light": "Mikado-Light",
        "base": "Mikado-Base", 
        "bold": "Mikado-Bold",
        "black": "Mikado-Black",
        "ultra": "Mikado-Ultra",
    }
    
    family = weight_map.get(weight, "Arial")
    return (family, size)