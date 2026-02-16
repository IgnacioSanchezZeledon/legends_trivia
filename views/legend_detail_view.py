# views/legend_detail_view.py

import time
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageColor, ImageFont

from utils.resource_path import assets_path


class LegendDetailView(ctk.CTkFrame):
    """
    Pantalla de detalle: imagen grande + cuadro de texto con información.
    Incluye header morado semitransparente, botón Back en header
    e íconos music/sfx abajo-izquierda (mismo formato).
    """

    BASE_W = 1080
    BASE_H = 720

    # Header
    HEADER_H_BASE = 70
    HEADER_COLOR = "#150F33"
    HEADER_ALPHA = 160

    # Espaciados (base)
    TITLE_TOP_PAD_BASE = 18     # espacio entre header y título
    GAP_COL_BASE = 34           # gap entre imagen y panel
    GAP_TITLE_BLOCK_BASE = 22   # espacio entre título y bloque (imagen+panel)

    def __init__(self, parent, controller, switch_view, sound_manager=None, sfx_manager=None,
                 legend_title="", legend_text="", legend_image=None):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.switch_view = switch_view
        self.sound_manager = sound_manager
        self.sfx_manager = sfx_manager

        self.legend_title = legend_title
        self.legend_text = legend_text
        self.legend_image = legend_image  # tuple ("images","legends","file.jpg") o None

        # Escala
        self.ui_scale = 1.0
        self._last_size = (0, 0)
        self._resize_after = None

        # Anti-spam hover SFX
        self._hover_cooldown = 0.08
        self._last_hover_ts = 0.0

        # Fondo
        bg_path = assets_path("images", "bg.jpg")
        self._bg_src = Image.open(bg_path).convert("RGB")
        self._bg_photo = None

        # Canvas
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # Header (franja morada semitransparente)
        self._hdr_photo = None
        self._hdr_item = self.canvas.create_image(0, 0, anchor="nw")

        # Caches
        self._btn_cache = {}
        self._icon_cache = {}
        self._img_cache = {}

        # Título
        self.title_item = self.canvas.create_text(
            0, 0,
            text=self.legend_title or "Legend",
            fill="white",
            font=("Mikado Ultra", 35, "bold"),
            anchor="n",  # 👈 importante para calcular alturas (top-aligned)
        )

        # Back
        self._btns = []
        self._back_btn = self._create_canvas_round_button(
            text="Back",
            command=self.controller.on_back,
            base_w=170, base_h=52, base_r=14,
            color="#2b6ea6", hover="#327fbf",
        )

        # Imagen principal
        self._legend_img_item = self.canvas.create_image(0, 0, anchor="nw")  # usaremos "nw" para layout exacto
        self._legend_img_tk = None

        # Panel texto
        self._text_bg_item = self.canvas.create_image(0, 0, anchor="nw")
        self._text_bg_tk = None
        self._text_item = self.canvas.create_text(
            0, 0,
            text=self.legend_text or "",
            fill="white",
            font=("Mikado Ultra", 12),
            width=800,
            anchor="nw",
        )

        # Íconos music/SFX
        self._img_music_on = None
        self._img_music_off = None
        self._img_sound_on = None
        self._img_sound_off = None
        self._item_music = None
        self._item_sound = None
        self._icons_h_cur = None

        # Eventos
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind_all("<m>", lambda e: self._toggle_music())
        self.canvas.bind_all("<M>", lambda e: self._toggle_music())
        self.canvas.bind_all("<s>", lambda e: self._toggle_sfx())
        self.canvas.bind_all("<S>", lambda e: self._toggle_sfx())

        self.after(0, self._first_layout)

    # ===================== Escala =====================
    def _set_scale_from_canvas(self) -> bool:
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

    # ===================== Header helpers =====================
    @staticmethod
    def _hex(hx: str):
        hx = hx.lstrip("#")
        return (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))

    def _redraw_header(self):
        w = self.canvas.winfo_width()
        if w < 2:
            return

        header_h = self.S(self.HEADER_H_BASE)
        r, g, b = self._hex(self.HEADER_COLOR)

        key = ("hdr", w, header_h, self.HEADER_COLOR, self.HEADER_ALPHA)
        img = self._icon_cache.get(key)
        if img is None:
            pil = Image.new("RGBA", (w, header_h), (r, g, b, self.HEADER_ALPHA))
            img = ImageTk.PhotoImage(pil)
            self._icon_cache[key] = img

        self._hdr_photo = img
        self.canvas.itemconfig(self._hdr_item, image=self._hdr_photo)
        self.canvas.coords(self._hdr_item, 0, 0)

    # ===================== SFX dispatcher =====================
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
            print(f"[LegendDetailView] SFX error ({kind}):", e)

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

    # ===================== Íconos music/SFX =====================
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
            print("[LegendDetailView] No se pudieron cargar/tintar íconos:", e)

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

    # ===================== Botones redondos =====================
    def _make_round_img(self, w: int, h: int, r: int, fill: str,
                        outline: str | None = None, outline_width: int = 0, aa_scale: int = 4):
        key = ("round", w, h, r, fill, outline, outline_width, aa_scale)
        if key in self._btn_cache:
            return self._btn_cache[key]

        W, H, R = w * aa_scale, h * aa_scale, r * aa_scale
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, W - 1, H - 1], R, fill=fill)

        img = img.resize((w, h), Image.Resampling.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self._btn_cache[key] = tkimg
        return tkimg

    def _create_canvas_round_button(
        self, text: str, command,
        base_w: int, base_h: int, base_r: int,
        color: str = "#2b6ea6", hover: str = "#327fbf",
        text_color: str = "white",
    ):
        img_item = self.canvas.create_image(0, 0, anchor="center")
        txt_item = self.canvas.create_text(
            0, 0,
            text=text,
            fill=text_color,
            font=("Mikado Ultra", 18, "bold"),
            anchor="center"
        )

        btn = {
            "img_item": img_item,
            "txt_item": txt_item,
            "base_w": base_w,
            "base_h": base_h,
            "base_r": base_r,
            "color": color,
            "hover": hover,
            "cmd": command,
            "img_norm": None,
            "img_hover": None,
            "hovering": False,
            "text_pt": 18,
        }
        self._btns.append(btn)

        for item in (img_item, txt_item):
            self.canvas.tag_bind(item, "<Enter>",    lambda e, b=btn: self._on_button_hover(b))
            self.canvas.tag_bind(item, "<Leave>",    lambda e, b=btn: self._on_button_leave(b))
            self.canvas.tag_bind(item, "<Button-1>", lambda e, b=btn: self._on_button_click(b))

        return btn

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
            print("[LegendDetailView] Error al ejecutar comando de botón:", e)

    def _refresh_round_buttons(self):
        for b in self._btns:
            w = self.S(b["base_w"])
            h = self.S(b["base_h"])
            r = self.S(b["base_r"])

            img_norm = self._make_round_img(w, h, r, b["color"])
            img_hover = self._make_round_img(w, h, r, b["hover"])

            b["img_norm"] = img_norm
            b["img_hover"] = img_hover

            self.canvas.itemconfig(b["img_item"], image=(img_hover if b.get("hovering") else img_norm))
            self.canvas.itemconfigure(b["txt_item"], font=self.F(b.get("text_pt", 18), bold=True))

    # ===================== Imagen principal + cuadro texto =====================
    def _safe_open_legend_img(self) -> Image.Image:
        if self.legend_image:
            try:
                p = assets_path(*self.legend_image)
                return Image.open(p).convert("RGBA")
            except Exception:
                pass
        w, h = 900, 520
        img = Image.new("RGBA", (w, h), (40, 60, 65, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w - 1, h - 1], outline=(255, 255, 255, 90), width=3)
        try:
            font = ImageFont.truetype("arial.ttf", 50)
        except Exception:
            font = ImageFont.load_default()
        draw.text((28, 26), self.legend_title or "Legend", fill=(255, 255, 255, 220), font=font)
        return img

    def _refresh_legend_image(self):
        w_target = self.S(640)
        h_target = self.S(330)

        key = ("mainimg_contain", self.legend_title, w_target, h_target)
        if key in self._img_cache:
            self._legend_img_tk = self._img_cache[key]
            self.canvas.itemconfig(self._legend_img_item, image=self._legend_img_tk)
            return

        src = self._safe_open_legend_img()

        # 🔹 CONTAIN (no recorte)
        scale = min(w_target / src.width, h_target / src.height)
        new_w = int(src.width * scale)
        new_h = int(src.height * scale)

        img = src.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Fondo transparente del tamaño del cuadro
        out = Image.new("RGBA", (w_target, h_target), (0, 0, 0, 0))

        # Centrar la imagen dentro del cuadro
        x = (w_target - new_w) // 2
        y = (h_target - new_h) // 2
        out.paste(img, (x, y), img)

        # Bordes redondeados del contenedor
        r = self.S(20)
        mask = Image.new("L", (w_target, h_target), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, w_target - 1, h_target - 1], r, fill=255)

        final = Image.new("RGBA", (w_target, h_target), (0, 0, 0, 0))
        final.paste(out, (0, 0), mask)

        tkimg = ImageTk.PhotoImage(final)
        self._img_cache[key] = tkimg
        self._legend_img_tk = tkimg

        self.canvas.itemconfig(self._legend_img_item, image=self._legend_img_tk)


    def _refresh_text_panel(self):
        """
        Panel de texto más ANCHO y menos ALTO.
        Usa un ancho adaptable (hasta ~960) y reduce la altura.
        """
        # ancho adaptable según ventana (máx 960, con márgenes)
        canvas_w = max(1, self.canvas.winfo_width())
        panel_w = min(self.S(960), canvas_w - self.S(120))
        panel_h = self.S(190)  # ✅ menos alto
        r = self.S(22)

        key = ("panel", panel_w, panel_h, r)
        if key not in self._img_cache:
            img = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle(
                [0, 0, panel_w - 1, panel_h - 1],
                r,
                fill=(0, 0, 0, 140),
                outline=(255, 255, 255, 55),
                width=2
            )
            self._img_cache[key] = ImageTk.PhotoImage(img)

        self._text_bg_tk = self._img_cache[key]
        self.canvas.itemconfig(self._text_bg_item, image=self._text_bg_tk)

        # texto: wrap por ancho real del panel + alineado a la izquierda
        self.canvas.itemconfigure(
            self._text_item,
            text=self.legend_text or "",
            font=self.F(18, bold=False),
            width=panel_w - self.S(44),
            justify="left",
        )

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
        self._refresh_round_buttons()
        self._refresh_legend_image()
        self._refresh_text_panel()
        self._redraw_background()
        self._redraw_header()
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
        self._redraw_header()

        if scale_changed:
            self._ensure_icons_scaled()
            self._refresh_round_buttons()
            self._refresh_legend_image()
            self._refresh_text_panel()
            if len(self._btn_cache) > 600:
                self._btn_cache.clear()

        self._layout_all()

    def _layout_all(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        cx = w // 2
        header_h = self.S(self.HEADER_H_BASE)

        # ===== Back dentro del header =====
        back_x = self.S(105)
        back_y = header_h // 2
        self.canvas.coords(self._back_btn["img_item"], back_x, back_y)
        self.canvas.coords(self._back_btn["txt_item"], back_x, back_y)

        # ===== Título DENTRO del header (centrado verticalmente) =====
        self.canvas.itemconfigure(self.title_item, font=self.F(46, bold=True))
        self.canvas.coords(self.title_item, cx, header_h // 2)

        # ===== Imagen centrada debajo del header =====
        # (si quieres un poco más de aire, sube/baja IMG_TOP_GAP)
        IMG_TOP_GAP = self.S(50)   # ✅ espacio entre header y la imagen
        img_w = min(self.S(720), w - self.S(120))
        img_h = self.S(330)

        img_top = header_h + IMG_TOP_GAP
        self.canvas.itemconfig(self._legend_img_item, anchor="center")
        self.canvas.coords(self._legend_img_item, cx, img_top + (img_h // 2))

        # ===== Panel de texto: más ancho y menos alto =====
        PANEL_TOP_GAP = self.S(16)  # espacio entre imagen y panel
        panel_w = min(self.S(960), w - self.S(120))
        panel_h = self.S(190)

        panel_top = img_top + img_h + PANEL_TOP_GAP

        self.canvas.itemconfig(self._text_bg_item, anchor="n")
        self.canvas.coords(self._text_bg_item, cx, panel_top)

        pad = self.S(18)
        left = cx - (panel_w // 2) + pad
        top = panel_top + pad

        self.canvas.itemconfig(self._text_item, anchor="nw")
        self.canvas.coords(self._text_item, left, top)
        self.canvas.itemconfigure(self._text_item, width=panel_w - pad * 2, justify="left")

        # ===== Íconos abajo-izquierda =====
        self._place_bottom_left_icons(w, h)

        # ===== Orden de capas =====
        self.canvas.tag_lower(self._bg_item)

        # Contenido principal abajo
        self.canvas.tag_raise(self._legend_img_item)
        self.canvas.tag_raise(self._text_bg_item)
        self.canvas.tag_raise(self._text_item)

        # Header SIEMPRE arriba de todo
        self.canvas.tag_raise(self._hdr_item)
        self.canvas.tag_raise(self._back_btn["img_item"])
        self.canvas.tag_raise(self._back_btn["txt_item"])
        self.canvas.tag_raise(self.title_item)

        # Iconos (encima de todo, opcional)
        if self._item_music:
            self.canvas.tag_raise(self._item_music)
        if self._item_sound:
            self.canvas.tag_raise(self._item_sound)

