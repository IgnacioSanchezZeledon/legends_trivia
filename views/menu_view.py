import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageColor
from pathlib import Path
from utils.resource_path import resource_path, assets_path


class MenuView(ctk.CTkFrame):
    """
    MenuView escalable (solo reduce, no agranda) respecto a un diseño base 1080x720.

    Mantiene:
      - Fondo "cover" en Canvas.
      - Título y subtítulo centrados.
      - 3 botones (Play/How to Play/Exit) como imágenes en Canvas.
      - Íconos music/sfx abajo-izquierda, tintados, escalados.
      - Barra de logos: MISMA intención que tu versión original:
          * Pastilla con ancho extra (+70) a propósito.
          * Posicionamiento con bar_w - 90 (a propósito).
          * Ubicada arriba-derecha.
    """

    BASE_W = 1080
    BASE_H = 720

    def __init__(self, parent, controller, switch_view, sound_manager=None, sfx_manager=None):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.sound_manager = sound_manager
        self.sfx_manager = sfx_manager

        # Escala
        self.ui_scale = 1.0
        self._last_size = (0, 0)

        # Anti-spam hover SFX
        self._hover_cooldown = 0.08
        self._last_hover_ts = 0.0

        # Debounce resize
        self._resize_after = None

        # Fondo
        bg_path = assets_path("images", "bg.jpg")
        self._bg_src = Image.open(bg_path).convert("RGB")
        self._bg_photo = None

        # Canvas base
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # Caches
        self._btn_cache = {}
        self._icon_cache = {}
        self._logo_cache = {}

        # Título / subtítulo (items)
        self.title_item = self.canvas.create_text(
            0, 0,
            text="Legends Trivia Challenge",
            fill="white",
            font=("Mikado Ultra", 50, "bold"),
            anchor="center",
        )
        self.subtitle_item = self.canvas.create_text(
            0, 0,
            text="Costa Rican Legends • Unit 6 • Ninth Grade",
            fill="#cfd8dc",
            font=("Mikado Ultra", 22),
            anchor="center",
        )


        # Botones tipo imagen
        self._btns = []
        self._create_canvas_image_button(
            text="Play", dy=120,
            command=self.controller.on_play,
            width=320, height=64, r=16,
            color="#2b6ea6", hover="#327fbf",
        )
        self._create_canvas_image_button(
            text="How to Play", dy=195,
            command=lambda: messagebox.showinfo(
                "How to Play",
                "Choose a level and answer. Auto-advance; finish the level to unlock the next."
            ),
            width=320, height=64, r=16,
            color="#2b6ea6", hover="#327fbf",
        )
        self._create_canvas_image_button(
            text="Exit", dy=270,
            command=self.controller.on_exit,
            width=320, height=64, r=16,
            color="#2b6ea6", hover="#327fbf",
        )

        # Íconos music/SFX (abajo-izquierda)
        self._img_music_on = None
        self._img_music_off = None
        self._img_sound_on = None
        self._img_sound_off = None
        self._item_music = None
        self._item_sound = None
        self._icons_h_cur = None

        # Barra de logos (arriba-derecha)
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
        self.canvas.bind_all("<m>", lambda e: self._toggle_music())
        self.canvas.bind_all("<M>", lambda e: self._toggle_music())
        self.canvas.bind_all("<s>", lambda e: self._toggle_sfx())
        self.canvas.bind_all("<S>", lambda e: self._toggle_sfx())

        # Primer layout
        self.after(0, self._first_layout)

    # ===================== Escala =====================
    def _set_scale_from_canvas(self) -> bool:
        """Calcula escala (solo reduce). Retorna True si cambió."""
        try:
            w = max(1, self.canvas.winfo_width())
            h = max(1, self.canvas.winfo_height())
        except Exception:
            w, h = self.BASE_W, self.BASE_H

        s = min(w / self.BASE_W, h / self.BASE_H)
        s = min(1.0, max(0.6, s))
        changed = abs(s - getattr(self, "ui_scale", 1.0)) > 0.01
        self.ui_scale = s
        return changed

    def S(self, px: int) -> int:
        return max(1, int(round(px * self.ui_scale)))

    def F(self, pt: int, bold: bool = False):
        size = max(8, int(round(pt * self.ui_scale)))
        return ("Mikado Ultra", size, "bold") if bold else ("Mikado Ultra", size)

    # ===================== Utilidades color/tinte =====================
    def _get_title_color(self) -> str:
        try:
            color = self.canvas.itemcget(self.title_item, "fill")
            return color if color else "white"
        except Exception:
            return "white"

    def _tint_rgba(self, img: Image.Image, color_str: str) -> Image.Image:
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        r, g, b, a = img.split()
        rgb = ImageColor.getrgb(color_str)
        colored = Image.new("RGBA", img.size, rgb + (255,))
        colored.putalpha(a)
        return colored

    # ===================== Toggle handlers =====================
    def _toggle_music(self):
        if not self.sound_manager or not self._item_music:
            return
        self._play_sfx("toggle")
        muted = self.sound_manager.toggle_mute()
        self.canvas.itemconfig(self._item_music, image=self._img_music_off if muted else self._img_music_on)

    def _toggle_sfx(self):
        if not self.sfx_manager or not self._item_sound:
            return
        self._play_sfx("toggle")
        muted = self.sfx_manager.toggle_mute()
        self.canvas.itemconfig(self._item_sound, image=self._img_sound_off if muted else self._img_sound_on)

    # ===================== Botones tipo imagen (con SFX) =====================
    def _make_round_img(self, w: int, h: int, r: int, fill: str,
                        outline: str | None = None, outline_width: int = 0, aa_scale: int = 4):
        key = ("round", w, h, r, fill, outline, outline_width, aa_scale)
        if key in self._btn_cache:
            return self._btn_cache[key]

        W, H, R = w * aa_scale, h * aa_scale, r * aa_scale
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, W - 1, H - 1], R, fill=fill)
        if outline and outline_width > 0:
            ow = outline_width * aa_scale
            draw.rounded_rectangle(
                [ow // 2, ow // 2, W - 1 - ow // 2, H - 1 - ow // 2],
                R - ow // 2, outline=outline, width=ow
            )

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
        # Crear items; imágenes se asignan en _refresh_buttons() según escala
        img_item = self.canvas.create_image(0, 0, anchor="center")
        txt_item = self.canvas.create_text(
            0, 0, text=text, fill=text_color, font=("Mikado Ultra", 20, "bold"), anchor="center"
        )

        btn = {
            "img_item": img_item,
            "txt_item": txt_item,
            "base_w": width,
            "base_h": height,
            "base_r": r,
            "dy": dy,
            "color": color,
            "hover": hover,
            "text_color": text_color,
            "outline": outline,
            "outline_width": outline_width,
            "cmd": command,
            "img_norm": None,
            "img_hover": None,
            "hovering": False,
        }
        self._btns.append(btn)

        for item in (img_item, txt_item):
            self.canvas.tag_bind(item, "<Enter>",    lambda e, b=btn: self._on_button_hover(b))
            self.canvas.tag_bind(item, "<Leave>",    lambda e, b=btn: self._on_button_leave(b))
            self.canvas.tag_bind(item, "<Button-1>", lambda e, b=btn: self._on_button_click(b))

    def _refresh_buttons(self):
        """Re-renderiza imágenes y fuentes de botones según escala."""
        for b in self._btns:
            w = self.S(b["base_w"])
            h = self.S(b["base_h"])
            r = self.S(b["base_r"])
            outline_w = self.S(b["outline_width"]) if b["outline_width"] else 0

            img_norm = self._make_round_img(w, h, r, b["color"], b["outline"], outline_w)
            img_hover = self._make_round_img(w, h, r, b["hover"], b["outline"], outline_w)

            b["img_norm"] = img_norm
            b["img_hover"] = img_hover

            self.canvas.itemconfig(b["img_item"], image=(img_hover if b.get("hovering") else img_norm))
            self.canvas.itemconfigure(b["txt_item"], font=self.F(20, bold=True))

    def _on_button_hover(self, b: dict):
        now = time.time()
        if now - self._last_hover_ts >= self._hover_cooldown:
            self._play_sfx("hover")
            self._last_hover_ts = now
        b["hovering"] = True
        if b.get("img_hover"):
            self.canvas.itemconfig(b["img_item"], image=b["img_hover"])
        self.canvas.config(cursor="hand2")

    def _on_button_leave(self, b: dict):
        b["hovering"] = False
        if b.get("img_norm"):
            self.canvas.itemconfig(b["img_item"], image=b["img_norm"])
        self.canvas.config(cursor="")

    def _on_button_click(self, b: dict):
        self._play_sfx("click")
        try:
            if b.get("img_hover"):
                self.canvas.itemconfig(b["img_item"], image=b["img_hover"])
                self.after(60, lambda: self.canvas.itemconfig(b["img_item"], image=b.get("img_norm")))
        except Exception:
            pass
        try:
            b["cmd"]()
        except Exception as e:
            print("[MenuView] Error al ejecutar comando de botón:", e)

    # ===================== Despachador SFX =====================
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
            print(f"[MenuView] SFX error ({kind}):", e)

    # ===================== Íconos music/SFX escalables =====================
    def _ensure_icons_scaled(self):
        target_h = self.S(32)
        if self._icons_h_cur == target_h and self._item_music is not None and self._item_sound is not None:
            return
        self._icons_h_cur = target_h

        try:
            icons_dir = Path(assets_path("icons"))
            music_on  = Image.open(icons_dir / "music_on.png").convert("RGBA")
            music_off = Image.open(icons_dir / "music_off.png").convert("RGBA")
            sound_on  = Image.open(icons_dir / "sound_on.png").convert("RGBA")
            sound_off = Image.open(icons_dir / "sound_off.png").convert("RGBA")

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

            if self._item_music is None:
                self._item_music = self.canvas.create_image(0, 0, anchor="sw", image=initial_music)
                self.canvas.tag_bind(self._item_music, "<Button-1>", lambda e: self._toggle_music())
                self.canvas.tag_bind(self._item_music, "<Enter>",    lambda e: self.canvas.config(cursor="hand2"))
                self.canvas.tag_bind(self._item_music, "<Leave>",    lambda e: self.canvas.config(cursor=""))
            else:
                self.canvas.itemconfig(self._item_music, image=initial_music)

            if self._item_sound is None:
                self._item_sound = self.canvas.create_image(0, 0, anchor="sw", image=initial_sound)
                self.canvas.tag_bind(self._item_sound, "<Button-1>", lambda e: self._toggle_sfx())
                self.canvas.tag_bind(self._item_sound, "<Enter>",    lambda e: self.canvas.config(cursor="hand2"))
                self.canvas.tag_bind(self._item_sound, "<Leave>",    lambda e: self.canvas.config(cursor=""))
            else:
                self.canvas.itemconfig(self._item_sound, image=initial_sound)

        except Exception as e:
            print("[MenuView] No se pudieron cargar/tintar íconos:", e)

    def _place_bottom_left_icons(self, w: int, h: int):
        pad = self.S(14)
        gap = self.S(12)

        if self._item_music is not None:
            self.canvas.coords(self._item_music, pad, h - pad)
            self.canvas.itemconfig(self._item_music, anchor="sw")

        if self._item_sound is not None:
            if self._item_music is not None:
                try:
                    bbox = self.canvas.bbox(self._item_music)
                    music_w = (bbox[2] - bbox[0]) if bbox else self.S(28)
                except Exception:
                    music_w = self.S(28)
                self.canvas.coords(self._item_sound, pad + music_w + gap, h - pad)
            else:
                self.canvas.coords(self._item_sound, pad, h - pad)
            self.canvas.itemconfig(self._item_sound, anchor="sw")

        if self._item_music:
            self.canvas.tag_raise(self._item_music)
        if self._item_sound:
            self.canvas.tag_raise(self._item_sound)

    # ===================== Barra de logos escalable (misma intención original) =====================
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

            bg_img = self._make_round_img(bar_w, bar_h, radius, fill="#FFFFFF", outline=None, outline_width=0)
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
                self.canvas.itemconfig(self._logo_bar_logo2_item, image=self._img_logo2_bar) # type: ignore
                self.canvas.itemconfig(self._logo_bar_logo3_item, image=self._img_logo3_bar) # type: ignore

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
            self._logo_bar_cfg = None

    def _place_top_left_logobar(self, w: int, h: int):
        """
        Posiciona la barra de logos igual que tu versión original:
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
        bar_y = pad_window
        self.canvas.coords(self._logo_bar_bg_item, bar_x, bar_y)
        self.canvas.itemconfig(self._logo_bar_bg_item, anchor="nw")

        y_center = bar_y + cfg["bar_h"] // 2

        x = bar_x + cfg["left_pad"]
        widths = cfg["widths"]
        gap = cfg["gap"]

        # Logo 1
        x1_center = x + widths[0] // 2
        self.canvas.coords(self._logo_bar_logo1_item, x1_center, y_center) # type: ignore

        # Logo 2
        x = x + widths[0] + gap
        x2_center = x + widths[1] // 2
        self.canvas.coords(self._logo_bar_logo2_item, x2_center, y_center) # type: ignore

        # Logo 3
        x = x + widths[1] + gap
        x3_center = x + widths[2] // 2
        self.canvas.coords(self._logo_bar_logo3_item, x3_center, y_center) # type: ignore

        self.canvas.tag_raise(self._logo_bar_bg_item)
        self.canvas.tag_raise(self._logo_bar_logo1_item) # type: ignore
        self.canvas.tag_raise(self._logo_bar_logo2_item) # type: ignore
        self.canvas.tag_raise(self._logo_bar_logo3_item) # type: ignore

    # ===================== Background cover =====================
    def _redraw_background(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return
        src_w, src_h = self._bg_src.size
        scale = max(w / src_w, h / src_h)
        bg = self._bg_src.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))), Image.Resampling.LANCZOS)
        left = (bg.width - w) // 2
        top = (bg.height - h) // 2
        bg = bg.crop((left, top, left + w, top + h))
        self._bg_photo = ImageTk.PhotoImage(bg)
        self.canvas.itemconfig(self._bg_item, image=self._bg_photo)
        self.canvas.coords(self._bg_item, 0, 0)

    # ===================== Layout / Resize =====================
    def _first_layout(self):
        self._set_scale_from_canvas()
        self._ensure_icons_scaled()
        self._ensure_logobar_scaled()
        self._refresh_buttons()
        self._layout_all()

    def _on_resize(self, event=None):
        if self._resize_after:
            try:
                self.after_cancel(self._resize_after)
            except Exception:
                pass
        self._resize_after = self.after(16, self._do_resize)

    def _do_resize(self):
        self._resize_after = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return
        if (w, h) == self._last_size:
            return
        self._last_size = (w, h)

        scale_changed = self._set_scale_from_canvas()
        self._redraw_background()

        if scale_changed:
            self._ensure_icons_scaled()
            self._ensure_logobar_scaled()
            self._refresh_buttons()

            # opcional: limitar cache si crece demasiado
            if len(self._btn_cache) > 600:
                self._btn_cache.clear()

        self._layout_all()

    def _layout_all(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        # Texto escalado y centrado
        self.canvas.itemconfigure(self.title_item, font=self.F(50, bold=True))
        self.canvas.itemconfigure(self.subtitle_item, font=self.F(22, bold=False))

        cx, cy = w // 2, h // 2 - self.S(140)
        self.canvas.coords(self.title_item, cx, cy)
        self.canvas.coords(self.subtitle_item, cx, cy + self.S(60))

        # Botones centrados
        for b in self._btns:
            by = cy + self.S(b["dy"]) + self.S(30)
            self.canvas.coords(b["img_item"], cx, by)
            self.canvas.coords(b["txt_item"], cx, by)

        # Íconos (abajo-izquierda)
        self._place_bottom_left_icons(w, h)

        # Logo bar (arriba-derecha, igual que antes)
        self._place_top_left_logobar(w, h)
