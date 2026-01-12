import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageColor
from pathlib import Path
from utils.resource_path import resource_path, assets_path


class MenuView(ctk.CTkFrame):
    """
    Vista del menú principal.

    Presenta:
      - Fondo en modo "cover" sobre un Canvas.
      - Título y subtítulo centrados.
      - Tres botones (Play / How to Play / Exit) renderizados como imágenes en el Canvas,
        con estados normal/hover y SFX de interfaz (hover/click).
      - Barra inferior izquierda con íconos de Música y SFX (on/off), tintados con
        el color del título para coherencia visual. Hotkeys: m/M (música), s/S (SFX).

    Parámetros
    ----------
    parent : tk.Widget
        Contenedor padre.
    controller : object
        Controlador con callbacks esperadas:
          - on_play()
          - on_exit()
    switch_view : callable
        No se usa aquí directamente; se inyecta por consistencia del proyecto.
    sound_manager : object | None
        Gestor de música. Debe exponer is_muted() y toggle_mute().
    sfx_manager : object | None
        Gestor de efectos. Idealmente expone:
          - is_muted(), toggle_mute()
          - play_ui(kind) o play(kind) o métodos específicos (play_hover, play_click, play_toggle).
    """

    def __init__(self, parent, controller, switch_view, sound_manager=None, sfx_manager=None):
        """
        Inicializa la vista, crea el Canvas base, título/subtítulo, botones y
        los íconos de música/SFX, y registra manejadores de tamaño y atajos.
        """
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.sound_manager = sound_manager
        self.sfx_manager = sfx_manager

        # Anti-spam para SFX de hover
        self._hover_cooldown = 0.08
        self._last_hover_ts = 0.0

        # Fondo
        bg_path = assets_path("images", "bg.jpg")
        self._bg_src = Image.open(bg_path).convert("RGB")
        self._bg_photo = None

        # Canvas base
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # Título / subtítulo
        self.title_item = self.canvas.create_text(
            0, 0,
            text="Legends Trivia Challenge",
            fill="white",
            font=("Mikado Ultra", 50, "bold"),
            anchor="center",
        )
        self.subtitle_item = self.canvas.create_text(
            0, 0,
            text="Costa Rican Legends • Unit 6",
            fill="#cfd8dc",
            font=("Mikado Ultra", 22),
            anchor="center",
        )

        # Botones tipo imagen
        self._btn_cache = {}
        self._btns = []
        self._create_canvas_image_button(
            text="Play", dy=120,
            command=self.controller.on_play,
            width=320, height=64, r=16,
        )
        self._create_canvas_image_button(
            text="How to Play", dy=195,
            command=lambda: messagebox.showinfo(
                "How to Play",
                "Choose a level and answer. Auto-advance; finish the level to unlock the next."
            ),
            width=320, height=64, r=16,
        )
        self._create_canvas_image_button(
            text="Exit", dy=270,
            command=self.controller.on_exit,
            width=320, height=64, r=16,
        )

        # Íconos música/SFX (abajo-izquierda)
        self._img_music_on = None
        self._img_music_off = None
        self._img_sound_on = None
        self._img_sound_off = None
        self._item_music = None
        self._item_sound = None
        self._load_top_icons()
        self._load_top_left_logobar()

        # Eventos
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind_all("<m>", lambda e: self._toggle_music())
        self.canvas.bind_all("<M>", lambda e: self._toggle_music())
        self.canvas.bind_all("<s>", lambda e: self._toggle_sfx())
        self.canvas.bind_all("<S>", lambda e: self._toggle_sfx())

    # ===================== Utilidades de color/íconos =====================
    def _get_title_color(self) -> str:
        """
        Devuelve el color actual del título para usarlo al tintar los íconos.

        Returns
        -------
        str
            Color en formato aceptado por Tk (p. ej., "#FFFFFF").
        """
        try:
            color = self.canvas.itemcget(self.title_item, "fill")
            return color if color else "white"
        except Exception:
            return "white"

    def _tint_rgba(self, img: Image.Image, color_str: str) -> Image.Image:
        """
        Aplica un tinte de color a una imagen RGBA respetando su canal alfa.

        Parámetros
        ----------
        img : PIL.Image
            Imagen de entrada.
        color_str : str
            Color destino (hex o nombre).

        Returns
        -------
        PIL.Image
            Imagen tintada en RGBA.
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        r, g, b, a = img.split()
        rgb = ImageColor.getrgb(color_str)
        colored = Image.new("RGBA", img.size, rgb + (255,))
        colored.putalpha(a)
        return colored

    def _load_top_icons(self):
        """
        Carga, redimensiona y tiñe los íconos music_on/off y sound_on/off;
        crea los items en el Canvas y bindea sus eventos (click/hover).
        """
        try:
            icons_dir = Path(assets_path("icons"))  # <- CLAVE: resuelto para exe y dev
            music_on  = Image.open(icons_dir / "music_on.png").convert("RGBA")
            music_off = Image.open(icons_dir / "music_off.png").convert("RGBA")
            sound_on  = Image.open(icons_dir / "sound_on.png").convert("RGBA")
            sound_off = Image.open(icons_dir / "sound_off.png").convert("RGBA")

            target_h = 32
            def scale_keep_ratio(img, h):
                w = int(img.width * (h / img.height))
                return img.resize((w, h), Image.Resampling.LANCZOS)

            music_on  = scale_keep_ratio(music_on,  target_h)
            music_off = scale_keep_ratio(music_off, target_h)
            sound_on  = scale_keep_ratio(sound_on,  target_h)
            sound_off = scale_keep_ratio(sound_off, target_h)

            title_color = self._get_title_color()
            music_on  = self._tint_rgba(music_on,  title_color)
            music_off = self._tint_rgba(music_off, title_color)
            sound_on  = self._tint_rgba(sound_on,  title_color)
            sound_off = self._tint_rgba(sound_off, title_color)

            self._img_music_on  = ImageTk.PhotoImage(music_on)
            self._img_music_off = ImageTk.PhotoImage(music_off)
            self._img_sound_on  = ImageTk.PhotoImage(sound_on)
            self._img_sound_off = ImageTk.PhotoImage(sound_off)

            initial_music = (self._img_music_off if (self.sound_manager and self.sound_manager.is_muted())
                            else self._img_music_on)
            initial_sound = (self._img_sound_off if (self.sfx_manager and self.sfx_manager.is_muted())
                            else self._img_sound_on)

            self._item_music = self.canvas.create_image(0, 0, anchor="sw", image=initial_music)
            self._item_sound = self.canvas.create_image(0, 0, anchor="sw", image=initial_sound)

            self.canvas.tag_bind(self._item_sound, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
            self.canvas.tag_bind(self._item_sound, "<Enter>",   lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(self._item_sound, "<Leave>",   lambda e: self.canvas.config(cursor=""))

            self.canvas.tag_bind(self._item_music, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
            self.canvas.tag_bind(self._item_music, "<Enter>",   lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(self._item_music, "<Leave>",   lambda e: self.canvas.config(cursor=""))
        except Exception as e:
            print("[MenuView] No se pudieron cargar/tintar íconos:", e)

    def _load_top_left_logobar(self):
        """
        Carga y prepara una barra tipo 'pastilla' con tres logos,
        ubicada arriba a la izquierda (sin funcionalidad).
        """
        try:
            logos_dir = Path(assets_path("logos"))  # ajusta la carpeta si ocupás

            # Cambia los nombres de archivo por los tuyos
            logo1 = Image.open(logos_dir / "logo_ucr.png").convert("RGBA")
            logo2 = Image.open(logos_dir / "logo_tcu_658.png").convert("RGBA")
            logo3 = Image.open(logos_dir / "logo_escuela.png").convert("RGBA")

            # Alturas personalizadas
            target_h_logo1 = 70   # logo 1 
            target_h_logo2 = 40   # logo 2
            target_h_logo3  = 20   # logo 3 normal

            def scale(img, h):
                w = int(img.width * (h / img.height))
                return img.resize((w, h), Image.Resampling.LANCZOS)

            logo1 = scale(logo1, target_h_logo1)
            logo2 = scale(logo2, target_h_logo2)
            logo3 = scale(logo3, target_h_logo3)

            self._img_logo1_bar = ImageTk.PhotoImage(logo1)
            self._img_logo2_bar = ImageTk.PhotoImage(logo2)
            self._img_logo3_bar = ImageTk.PhotoImage(logo3)

            # Padding dentro de la “pastilla”
            left_pad  = 18
            right_pad = 18
            top_pad   = 10
            bottom_pad = 10
            gap = 22  # espacio entre logos

            widths = [logo1.width, logo2.width, logo3.width]
            logos_total_w = sum(widths) + gap * 2  # dos gaps entre tres logos

            bar_w = left_pad + logos_total_w + right_pad + 70
            bar_h = top_pad + target_h_logo3 + bottom_pad + 20
            radius = bar_h // 2  # para que quede bien redondeado

            # Fondo tipo pastilla (blanco semi sobre el fondo)
            bar_img = self._make_round_img(
                bar_w, bar_h, radius,
                fill="#FFFFFF",
                outline=None,
                outline_width=0
            )

            self._logo_bar_bg_img = bar_img
            self._logo_bar_bg_item = self.canvas.create_image(0, 0, anchor="nw", image=self._logo_bar_bg_img)

            # Items de los logos (se posicionan en _place_top_left_logobar)
            self._logo_bar_logo1_item = self.canvas.create_image(0, 0, anchor="center", image=self._img_logo1_bar)
            self._logo_bar_logo2_item = self.canvas.create_image(0, 0, anchor="center", image=self._img_logo2_bar)
            self._logo_bar_logo3_item = self.canvas.create_image(0, 0, anchor="center", image=self._img_logo3_bar)

            # Guardar config para el layout
            self._logo_bar_cfg = {
                "bar_w": bar_w,
                "bar_h": bar_h,
                "left_pad": left_pad,
                "top_pad": top_pad,
                "gap": gap,
                "widths": widths,
            }

        except Exception as e:
            print("[MenuView] No se pudo crear la barra de logos:", e)





    def _place_bottom_left_icons(self, w: int, h: int):
        """
        Posiciona los íconos de música y SFX en la esquina inferior izquierda.

        Parámetros
        ----------
        w : int
            Ancho del Canvas.
        h : int
            Alto del Canvas.
        """
        pad = 14
        gap = 12
        if self._item_music is not None:
            self.canvas.coords(self._item_music, pad, h - pad)
            self.canvas.itemconfig(self._item_music, anchor="sw")
        if self._item_sound is not None and self._item_music is not None:
            try:
                bbox = self.canvas.bbox(self._item_music)
                music_w = (bbox[2] - bbox[0]) if bbox else 28
            except Exception:
                music_w = 28
            self.canvas.coords(self._item_sound, pad + music_w + gap, h - pad)
            self.canvas.itemconfig(self._item_sound, anchor="sw")
        elif self._item_sound is not None:
            self.canvas.coords(self._item_sound, pad, h - pad)
            self.canvas.itemconfig(self._item_sound, anchor="sw")

        if self._item_music:
            self.canvas.tag_raise(self._item_music)
        if self._item_sound:
            self.canvas.tag_raise(self._item_sound)
    
    def _place_top_left_logobar(self, w: int, h: int):
        """
        Posiciona la barra de logos arriba a la izquierda
        y distribuye los tres logos dentro de la 'pastilla'.
        """
        if not hasattr(self, "_logo_bar_bg_item") or not hasattr(self, "_logo_bar_cfg"):
            return

        cfg = self._logo_bar_cfg
        pad_window = 18  # separación respecto al borde de la ventana

        # Fondo arriba derecha
        bar_w = cfg["bar_w"] - 90
        bar_h = cfg["bar_h"]

        bar_x = w - pad_window - bar_w
        bar_y = pad_window
        self.canvas.coords(self._logo_bar_bg_item, bar_x, bar_y)
        self.canvas.itemconfig(self._logo_bar_bg_item, anchor="nw")

        # Centro vertical de los logos dentro de la pastilla
        y_center = bar_y + cfg["bar_h"] // 2

        # Posición horizontal de cada logo
        x = bar_x + cfg["left_pad"]
        widths = cfg["widths"]
        gap = cfg["gap"]

        # Logo 1
        x1_center = x + widths[0] // 2
        self.canvas.coords(self._logo_bar_logo1_item, x1_center, y_center)

        # Logo 2
        x = x + widths[0] + gap
        x2_center = x + widths[1] // 2
        self.canvas.coords(self._logo_bar_logo2_item, x2_center, y_center)

        # Logo 3
        x = x + widths[1] + gap
        x3_center = x + widths[2] // 2
        self.canvas.coords(self._logo_bar_logo3_item, x3_center, y_center)

        # Asegurar que quede encima del fondo y del background general
        self.canvas.tag_raise(self._logo_bar_bg_item)
        self.canvas.tag_raise(self._logo_bar_logo1_item)
        self.canvas.tag_raise(self._logo_bar_logo2_item)
        self.canvas.tag_raise(self._logo_bar_logo3_item)


    # ===================== Toggle handlers =====================
    def _toggle_music(self):
        """
        Alterna mute/unmute de música y actualiza el icono mostrado.
        """
        if not self.sound_manager or not self._item_music:
            return
        muted = self.sound_manager.toggle_mute()
        self.canvas.itemconfig(self._item_music, image=self._img_music_off if muted else self._img_music_on)

    def _toggle_sfx(self):
        """
        Alterna mute/unmute de efectos de sonido y actualiza el icono mostrado.
        """
        if not self.sfx_manager or not self._item_sound:
            return
        muted = self.sfx_manager.toggle_mute()
        self.canvas.itemconfig(self._item_sound, image=self._img_sound_off if muted else self._img_sound_on)

    # ===================== Botones tipo imagen (con SFX) =====================
    def _make_round_img(self, w: int, h: int, r: int, fill: str,
                        outline: str | None = None, outline_width: int = 0, aa_scale: int = 4):
        """
        Genera una imagen de rectángulo redondeado (sin sombra) y la cachea.

        Parámetros
        ----------
        w, h : int
            Tamaño del rectángulo.
        r : int
            Radio de esquinas.
        fill : str
            Color de relleno.
        outline : str | None
            Color del borde (opcional).
        outline_width : int
            Grosor del borde (opcional).
        aa_scale : int
            Factor de supermuestreo para suavizado.

        Returns
        -------
        ImageTk.PhotoImage
            Imagen para usar en el Canvas.
        """
        key = (w, h, r, fill, outline, outline_width, aa_scale)
        if key in self._btn_cache:
            return self._btn_cache[key]

        W, H, R = w * aa_scale, h * aa_scale, r * aa_scale
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, W - 1, H - 1], R, fill=fill)
        if outline and outline_width > 0:
            ow = outline_width * aa_scale
            draw.rounded_rectangle([ow // 2, ow // 2, W - 1 - ow // 2, H - 1 - ow // 2],
                                   R - ow // 2, outline=outline, width=ow)
        img = img.resize((w, h), Image.Resampling.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self._btn_cache[key] = tkimg
        return tkimg

    def _create_canvas_image_button(
        self, text: str, dy: int, command,
        width: int = 320, height: int = 64, r: int = 16,
        color: str = "#2b6ea6", hover: str = "#327fbf",
        text_color: str = "white", outline: str | None = None, outline_width: int = 0
    ):
        """
        Crea un botón (par imagen/texto) con estados normal/hover y SFX de interfaz.

        Parámetros
        ----------
        text : str
            Etiqueta del botón.
        dy : int
            Desplazamiento vertical relativo respecto al centro de bloque.
        command : callable
            Acción a ejecutar en click.
        width, height : int
            Dimensiones del botón.
        r : int
            Radio de esquinas.
        color, hover : str
            Colores de fondo normal y hover.
        text_color : str
            Color del texto.
        outline : str | None
            Color de borde (opcional).
        outline_width : int
            Grosor de borde (opcional).
        """
        img_norm = self._make_round_img(width, height, r, color, outline, outline_width)
        img_hover = self._make_round_img(width, height, r, hover, outline, outline_width)

        img_item = self.canvas.create_image(0, 0, anchor="center", image=img_norm)
        txt_item = self.canvas.create_text(
            0, 0, text=text, fill=text_color, font=("Mikado Ultra", 20, "bold"), anchor="center"
        )

        btn = {
            "img_item": img_item,
            "txt_item": txt_item,
            "img_norm": img_norm,
            "img_hover": img_hover,
            "w": width, "h": height,
            "r": r, "dy": dy,
            "cmd": command
        }
        self._btns.append(btn)

        for item in (img_item, txt_item):
            self.canvas.tag_bind(item, "<Enter>",   lambda e, b=btn: self._on_button_hover(b))
            self.canvas.tag_bind(item, "<Leave>",   lambda e, b=btn: self._on_button_leave(b))
            self.canvas.tag_bind(item, "<Button-1>", lambda e, b=btn: self._on_button_click(b))

    def _on_button_hover(self, b: dict):
        """
        SFX + cambio visual al pasar el ratón por un botón (con cooldown).
        """
        now = time.time()
        if now - self._last_hover_ts >= self._hover_cooldown:
            self._play_sfx("hover")
            self._last_hover_ts = now
        self.canvas.itemconfig(b["img_item"], image=b["img_hover"])

    def _on_button_leave(self, b: dict):
        """
        Restaura la imagen del botón al estado normal al salir el puntero.
        """
        self.canvas.itemconfig(b["img_item"], image=b["img_norm"])

    def _on_button_click(self, b: dict):
        """
        Reproduce SFX de click, hace un pequeño "flash" visual y ejecuta el comando.
        """
        self._play_sfx("click")
        try:
            self.canvas.itemconfig(b["img_item"], image=b["img_hover"])
            self.after(60, lambda: self.canvas.itemconfig(b["img_item"], image=b["img_norm"]))
        except Exception:
            pass
        try:
            b["cmd"]()
        except Exception as e:
            print("[MenuView] Error al ejecutar comando de botón:", e)

    def _play_sfx(self, kind: str):
        """
        Despachador tolerante de SFX. Intenta varias firmas comunes sin fallar
        si el gestor no las implementa.

        Parámetros
        ----------
        kind : str
            Identificador del sonido ('hover', 'click', 'toggle', etc.).
        """
        sm = self.sfx_manager
        if not sm:
            return
        try:
            if hasattr(sm, "play_ui"):
                sm.play_ui(kind); return
            if hasattr(sm, "play"):
                sm.play(kind); return
            if kind == "hover" and hasattr(sm, "play_hover"):
                sm.play_hover(); return
            if kind == "click" and hasattr(sm, "play_click"):
                sm.play_click(); return
            if kind == "toggle" and hasattr(sm, "play_toggle"):
                sm.play_toggle(); return
        except Exception as e:
            print(f"[MenuView] SFX error ({kind}):", e)

    # ===================== Redimensionado =====================
    def _on_resize(self, event=None):
        """
        Recompone el fondo (cover), centra título/subtítulo y reposiciona
        botones e íconos según el tamaño actual del Canvas.
        """
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        # Fondo: escalado proporcional y recorte central
        src_w, src_h = self._bg_src.size
        scale = max(w / src_w, h / src_h)
        new_size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
        bg = self._bg_src.resize(new_size, Image.Resampling.LANCZOS)
        left = (bg.width - w) // 2
        top = (bg.height - h) // 2
        bg = bg.crop((left, top, left + w, top + h))
        self._bg_photo = ImageTk.PhotoImage(bg)
        self.canvas.itemconfig(self._bg_item, image=self._bg_photo)
        self.canvas.coords(self._bg_item, 0, 0)

        # Bloque centrado (título/subtítulo)
        cx, cy = w // 2, h // 2 - 140
        self.canvas.coords(self.title_item, cx, cy)
        self.canvas.coords(self.subtitle_item, cx, cy + 60)

        # Botones
        for b in self._btns:
            by = cy + b["dy"] + 30
            self.canvas.coords(b["img_item"], cx, by)
            self.canvas.coords(b["txt_item"], cx, by)

        # Íconos (abajo-izquierda)
        self._place_bottom_left_icons(w, h)
        self._place_top_left_logobar(w, h)
