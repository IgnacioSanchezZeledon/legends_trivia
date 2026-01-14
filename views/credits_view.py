# views/credits_view.py — Credits (NO header bar + game title + 2 columns + FOOTER with Back + audio icons + LOGO BAR like MenuView)
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageColor, Image
from pathlib import Path

from utils.resource_path import assets_path


class CreditsView(ttk.Frame):
    """
    Pantalla Credits:
      - Fondo cover + overlay (baja fuerza del fondo).
      - SIN barra de header (no rectángulo arriba).
      - Título del juego arriba (solo texto).
      - Centro: "CREDITS" grande + créditos en 2 columnas.
      - Footer con:
          * Iconos music/sfx abajo-izquierda
          * Botón Back centrado
      - Barra de logos arriba-derecha EXACTA como MenuView (pastilla +70, bar_w - 90, heights 70/40/20).
      - UI auto-escalable (solo reduce).
      - Hotkeys: m/M y s/S.
    """

    TOPBAR   = "#150F33"
    TEXT     = "#FFFFFF"
    TEXT_SUB = "#cfd8dc"

    BG_OVERLAY_ALPHA = 95  # 70–130 recomendado

    BASE_W = 1080
    BASE_H = 720

    FOOT_H = 56

    BTN_W = 240
    BTN_H = 44
    BTN_R = 14

    ICON_H_BASE  = 28
    ICON_GAP     = 10
    ICON_PAD     = 12

    # Tipografías
    GAME_TITLE_PT = 22   # Título del juego arriba
    TITLE_PT      = 56   # "CREDITS"
    BODY_PT       = 18   # columnas

    # Layout
    TOP_PAD_Y      = 15   # padding superior para el título del juego
    AFTER_GAME_GAP = 5   # gap debajo del título del juego

    CONTENT_PAD_X = 64
    COL_GAP       = 48
    TITLE_GAP     = 24

    HOVER_COOLDOWN = 0.08

    def __init__(
        self,
        parent,
        controller,
        switch_view,
        sound_manager=None,
        sfx_manager=None,
        app_title="LEGENDS TRIVIA CHALLENGE",
        credits_lines=None,
        credits_left=None,
        credits_right=None,
    ):
        super().__init__(parent)

        self.controller = controller
        self.switch_view = switch_view
        self.sound_manager = sound_manager
        self.sfx_manager = sfx_manager
        self.app_title = app_title

        # ---- Contenido créditos ----
        # Si vienen columnas explícitas, se usan tal cual.
        if credits_left is not None or credits_right is not None:
            self._credits_left = credits_left or []
            self._credits_right = credits_right or []
        else:
            # Defaults: columnas definidas directamente.
            default_left = [
                "Educational Material",
                "• Trivia Game: Legends Trivia Challenge",
                "• Subject: Computing",
                "",
                "Institution",
                "• Liceo Rural El Progreso",
                "",
                "Academic Context",
                "• Level: Ninth Grade",
                "• Academic Plan",
                "• Unit 6",
            ]

            default_right = [
                "Learning Focus",
                "• Scenario: Open a Book, Open Your Mind",
                "• Theme: Costa Rican legends",
                "",
                "Developed by",
                "• Ignacio Sánchez Zeledón",
            ]

            # Si pasas credits_lines, lo ponemos a la izquierda completo (derecha vacía)
            if credits_lines is not None:
                self._credits_left = credits_lines
                self._credits_right = []
            else:
                self._credits_left = default_left
                self._credits_right = default_right

        # ---- escala ----
        self.ui_scale = 1.0
        self._last_size = (0, 0)
        self._resize_after = None

        # hover sfx
        self._last_hover_ts = 0.0

        # Canvas
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")

        # Fondo
        bg_path = assets_path("images", "bg.jpg")
        self._bg_src = Image.open(bg_path).convert("RGB")
        self._bg_photo = None
        self._bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # Caches
        self._bar_cache = {}
        self._btn_cache = {}

        # ---- Título del juego (arriba, sin barra) ----
        self._game_title_item = self.canvas.create_text(
            0, 0,
            text=self.app_title,
            fill=self.TEXT,
            font=("Mikado Ultra", self.GAME_TITLE_PT),
            anchor="n",
            justify="center",
        )

        # Footer
        self._foot_img_ref = None
        self._foot_item = self.canvas.create_image(0, 0, anchor="sw")

        # Centro: título + 2 columnas
        self._title_item = self.canvas.create_text(
            0, 0,
            text="CREDITS",
            fill=self.TEXT,
            font=("Mikado Ultra", self.TITLE_PT),
            anchor="n",
            justify="center",
        )

        # Columnas (anchor="nw" para x/y como esquina)
        self._col_left_item = self.canvas.create_text(
            0, 0,
            text="",
            fill=self.TEXT_SUB,
            font=("Mikado Ultra", self.BODY_PT),
            anchor="nw",
            justify="left",
            width=10,
        )
        self._col_right_item = self.canvas.create_text(
            0, 0,
            text="",
            fill=self.TEXT_SUB,
            font=("Mikado Ultra", self.BODY_PT),
            anchor="nw",
            justify="left",
            width=10,
        )

        # Botón Back
        self._btn_back = None

        # Iconos audio
        self._img_music_on = None
        self._img_music_off = None
        self._img_sound_on = None
        self._img_sound_off = None
        self._item_music = None
        self._item_sound = None
        self._icons_h_cur = None

        # Barra de logos (arriba-derecha) - EXACTA como MenuView
        self._logo_bar_cfg = None
        self._logo_bar_bg_item = None
        self._logo_bar_bg_img = None
        self._logo_bar_logo1_item = None
        self._logo_bar_logo2_item = None
        self._logo_bar_logo3_item = None
        self._img_logo1_bar = None
        self._img_logo2_bar = None
        self._img_logo3_bar = None
        self._logos_sig_cur = None

        # Eventos
        self.canvas.bind("<Configure>", self._on_resize)

        # Hotkeys
        self.canvas.bind_all("<m>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
        self.canvas.bind_all("<M>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
        self.canvas.bind_all("<s>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
        self.canvas.bind_all("<S>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))

        self.after(0, self._build)

    # ----------------- Escalado -----------------
    def _set_scale_from_canvas(self) -> bool:
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        s = min(w / self.BASE_W, h / self.BASE_H)
        s = min(1.0, max(0.6, s))
        changed = abs(self.ui_scale - s) > 0.01
        self.ui_scale = s
        return changed

    def S(self, v: int) -> int:
        return max(1, int(round(v * self.ui_scale)))

    def F(self, pt: int):
        return ("Mikado Ultra", max(8, int(round(pt * self.ui_scale))))

    # ----------------- Build -----------------
    def _build(self):
        self._set_scale_from_canvas()
        self._ensure_icons_scale()
        self._ensure_logobar_scaled()

        self._btn_back = self._create_button_item(
            text="Back",
            command=self._on_back,
            width=self.S(self.BTN_W), height=self.S(self.BTN_H), r=self.S(self.BTN_R),
            shadow=False
        )

        self._redraw_background()
        self._refresh_center_text()
        self._layout_all()

    def _on_back(self):
        if self.controller and hasattr(self.controller, "on_menu"):
            self.controller.on_menu()

    # ----------------- Texto (título + columnas) -----------------
    def _refresh_center_text(self):
        w = max(1, self.canvas.winfo_width())
        usable_w = max(1, w - self.S(self.CONTENT_PAD_X) * 2)
        gap = self.S(self.COL_GAP)
        col_w = max(10, int((usable_w - gap) // 2))

        self.canvas.itemconfigure(self._game_title_item, font=self.F(self.GAME_TITLE_PT), fill=self.TEXT)
        self.canvas.itemconfigure(self._title_item, font=self.F(self.TITLE_PT), fill=self.TEXT)

        self.canvas.itemconfigure(
            self._col_left_item,
            text="\n".join(self._credits_left),
            font=self.F(self.BODY_PT),
            fill=self.TEXT_SUB,
            width=col_w,
            justify="left",
        )
        self.canvas.itemconfigure(
            self._col_right_item,
            text="\n".join(self._credits_right),
            font=self.F(self.BODY_PT),
            fill=self.TEXT_SUB,
            width=col_w,
            justify="left",
        )

    # ----------------- Resize/Layout -----------------
    def _on_resize(self, _evt=None):
        if self._resize_after:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(16, self._do_resize)

    def _do_resize(self):
        self._resize_after = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2 or (w, h) == self._last_size:
            return
        self._last_size = (w, h)

        scale_changed = self._set_scale_from_canvas()
        if scale_changed:
            self._ensure_icons_scale()
            self._ensure_logobar_scaled()
            self._refresh_center_text()

            if isinstance(self._btn_back, dict):
                self._btn_back["w"], self._btn_back["h"], self._btn_back["r"] = (
                    self.S(self.BTN_W), self.S(self.BTN_H), self.S(self.BTN_R)
                )
                self._refresh_button_visual(self._btn_back)

        self._redraw_background()
        self._layout_all()

    def _layout_all(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        FOOT_H = self.S(self.FOOT_H)

        # Footer bar
        foot_img = ImageTk.PhotoImage(self._make_bar_img(w, FOOT_H, self.TOPBAR, 160))
        self.canvas.itemconfig(self._foot_item, image=foot_img)
        self._foot_img_ref = foot_img
        self.canvas.coords(self._foot_item, 0, h)

        # Área útil del contenido (sin header bar)
        top = 0
        bottom = h - FOOT_H

        # --- Logo bar (arriba-derecha, igual que MenuView) ---
        self._place_top_left_logobar(w, h)

        # --- Título del juego arriba ---
        game_y = top + self.S(self.TOP_PAD_Y)
        self.canvas.coords(self._game_title_item, w // 2, game_y)

        self.canvas.update_idletasks()
        gbox = self.canvas.bbox(self._game_title_item) or (0, 0, 0, 0)
        content_top = gbox[3] + self.S(self.AFTER_GAME_GAP)

        # Layout columnas
        pad_x = self.S(self.CONTENT_PAD_X)
        gap = self.S(self.COL_GAP)
        usable_w = max(1, w - pad_x * 2)
        col_w = max(10, int((usable_w - gap) // 2))

        left_x = pad_x
        right_x = pad_x + col_w + gap

        # Título grande "CREDITS"
        title_y = content_top + self.S(18)
        self.canvas.coords(self._title_item, w // 2, title_y)

        self.canvas.update_idletasks()
        tbox = self.canvas.bbox(self._title_item) or (0, 0, 0, 0)
        cols_y = tbox[3] + self.S(self.TITLE_GAP)

        # Columnas
        self.canvas.coords(self._col_left_item, left_x, cols_y)
        self.canvas.coords(self._col_right_item, right_x, cols_y)

        # Si se sale por abajo, subimos el bloque central
        self.canvas.update_idletasks()
        lbox = self.canvas.bbox(self._col_left_item) or (0, 0, 0, 0)
        rbox = self.canvas.bbox(self._col_right_item) or (0, 0, 0, 0)
        max_bottom = max(lbox[3], rbox[3])
        if max_bottom > bottom - self.S(12):
            shift = min(self.S(60), max_bottom - (bottom - self.S(12)))
            self.canvas.move(self._title_item, 0, -shift)
            self.canvas.move(self._col_left_item, 0, -shift)
            self.canvas.move(self._col_right_item, 0, -shift)

        # Iconos footer (abajo-izquierda)
        self._place_bottom_left_icons(w, h)
        if self._item_music:
            self.canvas.tag_raise(self._item_music)
        if self._item_sound:
            self.canvas.tag_raise(self._item_sound)

        # Botón Back centrado en footer
        if isinstance(self._btn_back, dict):
            cx = w // 2
            y = h - FOOT_H // 2
            self.canvas.coords(self._btn_back["img_item"], cx, y)
            self.canvas.coords(self._btn_back["txt_item"], cx, y)
            self.canvas.tag_raise(self._btn_back["img_item"])
            self.canvas.tag_raise(self._btn_back["txt_item"])

        # Elevar textos + logos
        self.canvas.tag_raise(self._game_title_item)
        self.canvas.tag_raise(self._title_item)
        self.canvas.tag_raise(self._col_left_item)
        self.canvas.tag_raise(self._col_right_item)

        if self._logo_bar_bg_item:
            self.canvas.tag_raise(self._logo_bar_bg_item)
        if self._logo_bar_logo1_item:
            self.canvas.tag_raise(self._logo_bar_logo1_item)
        if self._logo_bar_logo2_item:
            self.canvas.tag_raise(self._logo_bar_logo2_item)
        if self._logo_bar_logo3_item:
            self.canvas.tag_raise(self._logo_bar_logo3_item)

    # ----------------- Fondo (cover + overlay) -----------------
    def _redraw_background(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        sw, sh = self._bg_src.size
        scale = max(w / sw, h / sh)

        bg = self._bg_src.resize((max(1, int(sw * scale)), max(1, int(sh * scale))), Image.Resampling.LANCZOS)
        left = (bg.width - w) // 2
        top = (bg.height - h) // 2
        bg = bg.crop((left, top, left + w, top + h)).convert("RGBA")

        overlay = Image.new("RGBA", bg.size, (0, 0, 0, self.BG_OVERLAY_ALPHA))
        bg = Image.alpha_composite(bg, overlay)

        self._bg_photo = ImageTk.PhotoImage(bg)
        self.canvas.itemconfig(self._bg_item, image=self._bg_photo)
        self.canvas.coords(self._bg_item, 0, 0)

    # ----------------- PIL helpers -----------------
    def _make_bar_img(self, w, h, color_hex, alpha=160, aa=4):
        key = ("bar", w, h, color_hex, alpha, aa)
        if key in self._bar_cache:
            return self._bar_cache[key].copy()

        color_hex = color_hex.lstrip("#")
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        W, H = max(1, w * aa), max(1, h * aa)
        img = Image.new("RGBA", (W, H), (r, g, b, alpha))
        out = img.resize((max(1, w), max(1, h)), Image.Resampling.LANCZOS)
        self._bar_cache[key] = out.copy()
        return out

    def _make_round_img(self, w, h, r, fill, aa=4):
        w = max(1, int(w))
        h = max(1, int(h))
        r = max(0, int(r))
        aa = max(1, int(aa))
        key = ("round", w, h, r, fill, aa)
        if key in self._btn_cache:
            return self._btn_cache[key]
        W, H, R = w * aa, h * aa, r * aa
        img = Image.new("RGBA", (max(1, W), max(1, H)), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, W - 1, H - 1], R, fill=fill)
        img = img.resize((w, h), Image.Resampling.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self._btn_cache[key] = tkimg
        return tkimg

    # ----------------- Buttons -----------------
    def _create_button_item(self, text, command, width, height, r,
                            color="#110D2E", hover="#255B88", text_color="#CCCCCC", shadow=False):
        img_norm = self._make_round_img(width, height, r, color)
        img_hover = self._make_round_img(width, height, r, hover)
        img_item = self.canvas.create_image(0, 0, anchor="center", image=img_norm)
        txt_item = self.canvas.create_text(
            0, 0, text=text, fill=text_color, font=self.F(16),
            anchor="center", justify="center"
        )

        btn = {
            "img_item": img_item,
            "txt_item": txt_item,
            "img_norm": img_norm,
            "img_hover": img_hover,
            "w": int(width),
            "h": int(height),
            "r": int(r),
            "cmd": command,
            "color": color,
            "hover": hover,
            "text_color": text_color,
        }

        def _hover(_e=None, b=btn):
            now = time.time()
            if now - self._last_hover_ts >= self.HOVER_COOLDOWN:
                self._play_sfx("hover")
                self._last_hover_ts = now
            self.canvas.itemconfig(b["img_item"], image=b["img_hover"])
            self.canvas.config(cursor="hand2")

        def _leave(_e=None, b=btn):
            self.canvas.itemconfig(b["img_item"], image=b["img_norm"])
            self.canvas.config(cursor="")

        def _click(_e=None, b=btn):
            self._play_sfx("click")
            if callable(b["cmd"]):
                b["cmd"]()

        for item in (img_item, txt_item):
            self.canvas.tag_bind(item, "<Enter>", _hover)
            self.canvas.tag_bind(item, "<Leave>", _leave)
            self.canvas.tag_bind(item, "<Button-1>", _click)

        return btn

    def _refresh_button_visual(self, btn: dict):
        btn["img_norm"] = self._make_round_img(btn["w"], btn["h"], btn["r"], btn.get("color", "#110D2E"))
        btn["img_hover"] = self._make_round_img(btn["w"], btn["h"], btn["r"], btn.get("hover", "#255B88"))
        self.canvas.itemconfig(btn["img_item"], image=btn["img_norm"])
        self.canvas.itemconfig(btn["txt_item"], font=self.F(16), fill=btn.get("text_color", "#CCCCCC"))

    # ----------------- Audio icons -----------------
    def _get_title_color(self) -> str:
        # Color de referencia: el del título del juego
        try:
            c = self.canvas.itemcget(self._game_title_item, "fill")
            return c if c else self.TEXT
        except Exception:
            return self.TEXT

    def _tint_rgba(self, img, color_str: str):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        r, g, b, a = img.split()
        rgb = ImageColor.getrgb(color_str)
        colored = Image.new("RGBA", img.size, rgb + (255,))
        colored.putalpha(a)
        return colored

    def _ensure_icons_scale(self):
        new_h = self.S(self.ICON_H_BASE)
        if self._icons_h_cur == new_h and self._item_music is not None and self._item_sound is not None:
            return
        self._icons_h_cur = new_h
        self._load_icons()

    def _load_icons(self):
        try:
            icons_dir = Path(assets_path("icons"))
            music_on = Image.open(icons_dir / "music_on.png").convert("RGBA")
            music_off = Image.open(icons_dir / "music_off.png").convert("RGBA")
            sound_on = Image.open(icons_dir / "sound_on.png").convert("RGBA")
            sound_off = Image.open(icons_dir / "sound_off.png").convert("RGBA")

            def scale_keep_ratio(img, h):
                h = max(1, int(h))
                w = max(1, int(img.width * (h / img.height)))
                return img.resize((w, h), Image.Resampling.LANCZOS)

            music_on = scale_keep_ratio(music_on, self._icons_h_cur)
            music_off = scale_keep_ratio(music_off, self._icons_h_cur)
            sound_on = scale_keep_ratio(sound_on, self._icons_h_cur)
            sound_off = scale_keep_ratio(sound_off, self._icons_h_cur)

            color = self._get_title_color()
            music_on = self._tint_rgba(music_on, color)
            music_off = self._tint_rgba(music_off, color)
            sound_on = self._tint_rgba(sound_on, color)
            sound_off = self._tint_rgba(sound_off, color)

            self._img_music_on = ImageTk.PhotoImage(music_on)
            self._img_music_off = ImageTk.PhotoImage(music_off)
            self._img_sound_on = ImageTk.PhotoImage(sound_on)
            self._img_sound_off = ImageTk.PhotoImage(sound_off)

            if self._item_music is None:
                initial = self._img_music_off if (self.sound_manager and self.sound_manager.is_muted()) else self._img_music_on
                self._item_music = self.canvas.create_image(0, 0, anchor="sw", image=initial)
                self.canvas.tag_bind(self._item_music, "<Enter>", lambda e: (self._on_icon_hover(), self.canvas.config(cursor="hand2")))
                self.canvas.tag_bind(self._item_music, "<Leave>", lambda e: self.canvas.config(cursor=""))
                self.canvas.tag_bind(self._item_music, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
            else:
                self.canvas.itemconfig(
                    self._item_music,
                    image=self._img_music_off if (self.sound_manager and self.sound_manager.is_muted()) else self._img_music_on
                )

            if self._item_sound is None:
                initial = self._img_sound_off if (self.sfx_manager and self.sfx_manager.is_muted()) else self._img_sound_on
                self._item_sound = self.canvas.create_image(0, 0, anchor="sw", image=initial)
                self.canvas.tag_bind(self._item_sound, "<Enter>", lambda e: (self._on_icon_hover(), self.canvas.config(cursor="hand2")))
                self.canvas.tag_bind(self._item_sound, "<Leave>", lambda e: self.canvas.config(cursor=""))
                self.canvas.tag_bind(self._item_sound, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
            else:
                self.canvas.itemconfig(
                    self._item_sound,
                    image=self._img_sound_off if (self.sfx_manager and self.sfx_manager.is_muted()) else self._img_sound_on
                )

        except Exception as e:
            print("[CreditsView] No se pudieron cargar/tintar íconos:", e)

    def _on_icon_hover(self):
        now = time.time()
        if now - self._last_hover_ts >= self.HOVER_COOLDOWN:
            self._play_sfx("hover")
            self._last_hover_ts = now

    def _place_bottom_left_icons(self, w, h):
        pad = self.S(self.ICON_PAD)
        gap = self.ICON_GAP

        if self._item_music is not None:
            self.canvas.coords(self._item_music, pad, h - pad)

        if self._item_sound is not None:
            try:
                bbox = self.canvas.bbox(self._item_music) if self._item_music else None
                music_w = (bbox[2] - bbox[0]) if bbox else self._icons_h_cur
            except Exception:
                music_w = self._icons_h_cur
            self.canvas.coords(self._item_sound, pad + music_w + gap, h - pad)  # type: ignore

    def _toggle_music(self):
        if not self.sound_manager or not self._item_music:
            return
        muted = self.sound_manager.toggle_mute()
        self.canvas.itemconfig(self._item_music, image=self._img_music_off if muted else self._img_music_on)

    def _toggle_sfx(self):
        if not self.sfx_manager or not self._item_sound:
            return
        muted = self.sfx_manager.toggle_mute()
        self.canvas.itemconfig(self._item_sound, image=self._img_sound_off if muted else self._img_sound_on)

    # ===================== Barra de logos escalable (EXACTA como MenuView) =====================
    def _ensure_logobar_scaled(self):
        """
        Reconstruye logos + pastilla al cambiar escala.

        Mantiene:
          - alturas base 70/40/20 (escaladas)
          - padding y gap (escalados)
          - ancho extra intencional: +70 (escalado)
          - alto con extra intencional: +20 (escalado)
        """
        h1 = self.S(70)
        h2 = self.S(40)
        h3 = self.S(20)
        sig = (h1, h2, h3)

        if self._logos_sig_cur == sig and self._logo_bar_cfg is not None:
            return
        self._logos_sig_cur = sig

        try:
            logos_dir = Path(assets_path("logos"))
            logo1 = Image.open(logos_dir / "logo_ucr.png").convert("RGBA")
            logo2 = Image.open(logos_dir / "logo_tcu_658.png").convert("RGBA")
            logo3 = Image.open(logos_dir / "logo_escuela.png").convert("RGBA")

            def scale(img, h):
                w = int(img.width * (h / img.height))
                return img.resize((w, h), Image.Resampling.LANCZOS)

            logo1 = scale(logo1, h1)
            logo2 = scale(logo2, h2)
            logo3 = scale(logo3, h3)

            self._img_logo1_bar = ImageTk.PhotoImage(logo1)
            self._img_logo2_bar = ImageTk.PhotoImage(logo2)
            self._img_logo3_bar = ImageTk.PhotoImage(logo3)

            left_pad = self.S(18)
            right_pad = self.S(18)
            top_pad = self.S(10)
            bottom_pad = self.S(10)
            gap = self.S(22)

            widths = [logo1.width, logo2.width, logo3.width]
            logos_total_w = sum(widths) + gap * 2

            # === EXACTO: “tamaño extra” intencional ===
            bar_w = left_pad + logos_total_w + right_pad + self.S(70)
            bar_h = top_pad + h3 + bottom_pad + self.S(20)
            radius = bar_h // 2

            bg_img = self._make_round_img(bar_w, bar_h, radius, fill="#FFFFFF", aa=4)
            self._logo_bar_bg_img = bg_img

            if self._logo_bar_bg_item is None:
                self._logo_bar_bg_item = self.canvas.create_image(0, 0, anchor="nw", image=self._logo_bar_bg_img)
            else:
                self.canvas.itemconfig(self._logo_bar_bg_item, image=self._logo_bar_bg_img)

            if self._logo_bar_logo1_item is None:
                self._logo_bar_logo1_item = self.canvas.create_image(0, 0, anchor="center", image=self._img_logo1_bar)
                self._logo_bar_logo2_item = self.canvas.create_image(0, 0, anchor="center", image=self._img_logo2_bar)
                self._logo_bar_logo3_item = self.canvas.create_image(0, 0, anchor="center", image=self._img_logo3_bar)
            else:
                self.canvas.itemconfig(self._logo_bar_logo1_item, image=self._img_logo1_bar)
                self.canvas.itemconfig(self._logo_bar_logo2_item, image=self._img_logo2_bar)  # type: ignore
                self.canvas.itemconfig(self._logo_bar_logo3_item, image=self._img_logo3_bar)  # type: ignore

            self._logo_bar_cfg = {
                "bar_w": bar_w,
                "bar_h": bar_h,
                "left_pad": left_pad,
                "top_pad": top_pad,
                "gap": gap,
                "widths": widths,
            }

        except Exception as e:
            print("[CreditsView] No se pudo crear la barra de logos:", e)
            self._logo_bar_cfg = None

    def _place_top_left_logobar(self, w: int, h: int):
        """
        Posiciona la barra de logos igual que MenuView:
          - arriba-derecha
          - usando bar_w - 90 (intencional)
        """
        if not self._logo_bar_cfg or self._logo_bar_bg_item is None:
            return

        cfg = self._logo_bar_cfg
        pad_window = self.S(18)

        # === EXACTAMENTE como lo tenías ===
        bar_w = cfg["bar_w"] - self.S(90)
        bar_h = cfg["bar_h"]

        bar_x = w - pad_window - bar_w
        FOOT_H = self.S(self.FOOT_H)
        bar_y = h - FOOT_H - pad_window - bar_h
        self.canvas.coords(self._logo_bar_bg_item, bar_x, bar_y)
        self.canvas.itemconfig(self._logo_bar_bg_item, anchor="nw")

        y_center = bar_y + cfg["bar_h"] // 2

        x = bar_x + cfg["left_pad"]
        widths = cfg["widths"]
        gap = cfg["gap"]

        # Logo 1
        x1_center = x + widths[0] // 2
        self.canvas.coords(self._logo_bar_logo1_item, x1_center, y_center)  # type: ignore

        # Logo 2
        x = x + widths[0] + gap
        x2_center = x + widths[1] // 2
        self.canvas.coords(self._logo_bar_logo2_item, x2_center, y_center)  # type: ignore

        # Logo 3
        x = x + widths[1] + gap
        x3_center = x + widths[2] // 2
        self.canvas.coords(self._logo_bar_logo3_item, x3_center, y_center)  # type: ignore

        self.canvas.tag_raise(self._logo_bar_bg_item)
        self.canvas.tag_raise(self._logo_bar_logo1_item)  # type: ignore
        self.canvas.tag_raise(self._logo_bar_logo2_item)  # type: ignore
        self.canvas.tag_raise(self._logo_bar_logo3_item)  # type: ignore

    # ----------------- SFX -----------------
    def _play_sfx(self, kind: str):
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
            print(f"[CreditsView] SFX error ({kind}):", e)
