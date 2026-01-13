# views/levels_view.py — Mapa de niveles en Canvas + iconos música/sonido (abajo-izquierda) + Header escalable
import math
import os
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageColor
from pathlib import Path
from utils.resource_path import resource_path, assets_path  # <<< CLAVE


class LevelsView(ttk.Frame):
    """
    Vista del mapa de niveles, ahora con auto-scaling (solo reduce, no agranda)
    respecto a un diseño base 1080x720.

    Escala:
      - Header (altura + fuente del título + botón Back)
      - Íconos música/SFX (tamaño + padding + gap)
      - Nodos (diámetro + fuentes + label offset)
    """

    # ===== Base para escala =====
    BASE_W = 1080
    BASE_H = 720

    # Estilos
    TOPBAR = "#150F33"
    TEXT   = "#FFFFFF"

    # Medidas base (diseño)
    BAR_H_BASE   = 56
    NODE_D_BASE  = 60
    SH_OFF_BASE  = 6
    SH_BLUR_BASE = 3

    # Paleta de nodos
    PRIMARY        = "#2B6EA6"
    PRIMARY_HOVER  = "#3A84C2"
    PRIMARY_BORDER = "#1F5A86"

    LOCK_FILL   = "#9DA3A6"
    LOCK_BORDER = "#70757A"

    DEFAULT_BG = "assets/images/levels_spooky.png"

    NODE_POS = [
        (0.14, 0.38),
        (0.23, 0.65),
        (0.58, 0.74),
        (0.63, 0.48),
        (0.79, 0.30),
        (0.71, 0.14),
    ]

    PATH_POLY = [(0.20, 0.82), (0.35, 0.70), (0.50, 0.60), (0.62, 0.50), (0.74, 0.38), (0.86, 0.22)]

    # Iconos música/sonido (base)
    TOP_ICONS_H_BASE   = 28
    TOP_ICONS_GAP_BASE = 10
    TOP_ICONS_PAD_BASE = 12

    def __init__(self, parent, controller, progress_model, total_levels, switch_view, bg_path=None,
                 sound_manager=None, sfx_manager=None):
        super().__init__(parent)
        self.controller  = controller
        self.progress    = progress_model
        self.total       = int(total_levels)
        self.switch_view = switch_view

        # Ruta de fondo SIEMPRE absoluta
        self.bg_path = resource_path(bg_path or self.DEFAULT_BG)

        self.sound_manager = sound_manager
        self.sfx_manager   = sfx_manager

        # Escala
        self.ui_scale = 1.0
        self._last_size = (0, 0)

        # Anti-spam hover SFX
        self._hover_cooldown = 0.08
        self._last_hover_ts = 0.0

        # Debounce resize
        self._resize_after = None

        # Canvas + fondo
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        self._bg_src   = self._load_bg(self.bg_path)
        self._bg_photo = None
        self._bg_item  = self.canvas.create_image(0, 0, anchor="nw")

        # Header
        self._hdr_item  = self.canvas.create_image(0, 0, anchor="nw")
        self._title_txt = self.canvas.create_text(
            0, 0, text="Select Level", fill=self.TEXT, font=("Mikado Ultra", 32), anchor="center"
        )
        self._hdr_cache = {}

        # Botón Back
        self._back_btn = None

        # Nodos
        self.nodes = []
        self._img_cache = {}  # cache de PhotoImage para tokens y rects

        # Iconos música/SFX (abajo-izquierda)
        self._img_music_on  = None
        self._img_music_off = None
        self._img_sound_on  = None
        self._img_sound_off = None
        self._item_music = None
        self._item_sound = None
        self._icons_h_cur = None  # para reescalar íconos

        # Events
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-3>", self._print_norm_xy)

        # Hotkeys
        self.canvas.bind_all("<m>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
        self.canvas.bind_all("<M>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
        self.canvas.bind_all("<s>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
        self.canvas.bind_all("<S>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))

        # Build inicial (cuando haya tamaño válido)
        self.after(0, self._first_layout)

    # ===================== Escala =====================
    def _set_scale_from_canvas(self) -> bool:
        """Actualiza ui_scale (solo reduce). Retorna True si cambió."""
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

    # ================= API pública =================
    def refresh(self):
        """Actualiza desbloqueo, estrellas y aspecto (y re-render si la escala cambió)."""
        for nd in self.nodes:
            n = nd["n"]
            unlocked = n <= self.progress.unlocked()
            stars = self.progress.stars_for(n)
            nd["unlocked"] = unlocked
            nd["stars"] = stars

            # label inferior
            self.canvas.itemconfigure(
                nd["label_item"],
                text=("★" * stars + "☆" * (3 - stars)) if unlocked else ""
            )
            # centro
            self.canvas.itemconfigure(
                nd["num_item"],
                text=(str(n) if unlocked else "🔒"),
                font=self.F(20, bold=True) if unlocked else self.F(18, bold=False)
            )
            self._apply_node_visual(nd, hover=False)

    # ================= Build =================
    def _first_layout(self):
        self._set_scale_from_canvas()
        self._ensure_icons_scaled()
        self._build_header()
        self._build_nodes()
        self._redraw_background()
        self._layout_all()

    def _build_header(self):
        # Back escalable: si ya existe y cambia escala, reconstruimos
        if self._back_btn is None:
            self._back_btn = self._create_rect_button(
                "Back",
                lambda: hasattr(self.controller, "on_menu") and self.controller.on_menu(),
                self.S(120), self.S(40), self.S(12)
            )
        else:
            # Re-render del botón Back al cambiar escala (mantiene bindings)
            self._update_rect_button(self._back_btn, self.S(120), self.S(40), self.S(12))

    def _build_nodes(self):
        """(Re)construye nodos al tamaño actual."""
        # Borra nodos previos
        for nd in self.nodes:
            for k in ("img_item", "num_item", "label_item"):
                try:
                    self.canvas.delete(nd[k])
                except Exception:
                    pass
        self.nodes.clear()

        # Posiciones
        if len(self.NODE_POS) >= self.total:
            pts = self.NODE_POS[:self.total]
        else:
            pts = self._resample_path(self.PATH_POLY, self.total)

        # Medidas escaladas
        node_d = self.S(self.NODE_D_BASE)

        for i in range(self.total):
            n = i + 1
            unlocked = n <= self.progress.unlocked()
            stars = self.progress.stars_for(n)

            img_norm  = self._token_img(node_d, fill=self.PRIMARY,       border=self.PRIMARY_BORDER)
            img_hover = self._token_img(node_d, fill=self.PRIMARY_HOVER, border=self.PRIMARY_BORDER)
            img_lock  = self._token_img(node_d, fill=self.LOCK_FILL,     border=self.LOCK_BORDER)

            img_item = self.canvas.create_image(0, 0, image=img_norm, anchor="center")

            center_text = str(n) if unlocked else "🔒"
            center_font = self.F(20, bold=True) if unlocked else self.F(18, bold=False)
            num_item = self.canvas.create_text(0, 0, text=center_text, fill="#ffffff",
                                               font=center_font, anchor="center")

            label = ("★" * stars + "☆" * (3 - stars)) if unlocked else ""
            label_item = self.canvas.create_text(0, 0, text=label, fill="#ffffff",
                                                 font=self.F(12, bold=False), anchor="n")

            nd = {
                "n": n, "pos": pts[i], "unlocked": unlocked, "stars": stars,
                "img_item": img_item, "num_item": num_item, "label_item": label_item,
                "img_norm": img_norm, "img_hover": img_hover, "img_lock": img_lock,
            }
            self.nodes.append(nd)

            # Eventos
            for tag in (img_item, num_item, label_item):
                self.canvas.tag_bind(tag, "<Enter>",    lambda e, nd=nd: self._on_node_hover(nd))
                self.canvas.tag_bind(tag, "<Leave>",    lambda e, nd=nd: self._on_node_leave(nd))
                self.canvas.tag_bind(tag, "<Button-1>", lambda e, nd=nd: self._on_node_click(nd))

        for nd in self.nodes:
            self._apply_node_visual(nd, hover=False)

    # ================= Layout / Resize =================
    def _on_resize(self, _=None):
        if self._resize_after:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(16, self._do_resize)

    def _do_resize(self):
        self._resize_after = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if (w, h) == self._last_size or w < 2 or h < 2:
            return
        self._last_size = (w, h)

        scale_changed = self._set_scale_from_canvas()
        self._redraw_background()

        # Si cambia escala, hay que re-renderizar assets (header, back, nodos, iconos)
        if scale_changed:
            self._ensure_icons_scaled()
            self._build_header()
            self._build_nodes()

            # Limitar cache si se infla (opcional pero recomendable)
            if len(self._img_cache) > 800:
                self._img_cache.clear()
            self._hdr_cache.clear()

        self._layout_all()

    def _layout_all(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        BAR_H  = self.S(self.BAR_H_BASE)
        NODE_D = self.S(self.NODE_D_BASE)

        # Header bar (escalado)
        key = (w, BAR_H, self.TOPBAR, 220)
        if key not in self._hdr_cache:
            img = Image.new("RGBA", (w, BAR_H), (*self._hex(self.TOPBAR), 220))
            self._hdr_cache[key] = ImageTk.PhotoImage(img)
        self.canvas.itemconfig(self._hdr_item, image=self._hdr_cache[key])
        self.canvas.coords(self._hdr_item, 0, 0)

        # Título (fuente escalada)
        self.canvas.itemconfigure(self._title_txt, font=self.F(32, bold=False))
        self.canvas.coords(self._title_txt, w // 2, BAR_H // 2)

        # Botón Back (pos y fuente escaladas)
        if self._back_btn:
            self.canvas.itemconfigure(self._back_btn["txt_item"], font=self.F(16, bold=False))
            self.canvas.coords(self._back_btn["img_item"], self.S(12) + self.S(60), BAR_H // 2)
            self.canvas.coords(self._back_btn["txt_item"], self.S(12) + self.S(60), BAR_H // 2)

        # Nodos (posiciones relativas, pero offset header escalado)
        for nd in self.nodes:
            x_rel, y_rel = nd["pos"]
            cx = int(x_rel * w)
            cy = int(y_rel * max(1, (h - BAR_H))) + BAR_H
            self.canvas.coords(nd["img_item"], cx, cy)
            self.canvas.coords(nd["num_item"], cx, cy)
            self.canvas.coords(nd["label_item"], cx, cy + NODE_D // 2 + self.S(4))

        # Iconos música/sonido (escalados)
        self._place_bottom_left_icons(w, h)
        if self._item_music:
            self.canvas.tag_raise(self._item_music)
        if self._item_sound:
            self.canvas.tag_raise(self._item_sound)

    # ================= Interacción =================
    def _apply_node_visual(self, nd, hover=False):
        if nd["unlocked"]:
            self.canvas.itemconfig(nd["img_item"], image=nd["img_hover"] if hover else nd["img_norm"])
        else:
            self.canvas.itemconfig(nd["img_item"], image=nd["img_lock"])

    def _on_node_hover(self, nd):
        now = time.time()
        if now - self._last_hover_ts >= self._hover_cooldown:
            self._play_sfx("hover")
            self._last_hover_ts = now
        self._apply_node_visual(nd, hover=True)
        self.canvas.config(cursor="hand2")

    def _on_node_leave(self, nd):
        self._apply_node_visual(nd, hover=False)
        self.canvas.config(cursor="")

    def _on_node_click(self, nd):
        self._play_sfx("click")
        if nd["unlocked"]:
            self.controller.on_pick_level(nd["n"])

    # ================= Fondo / helpers de dibujo =================
    def _load_bg(self, path):
        return Image.open(path).convert("RGB") if os.path.exists(path) else Image.new("RGB", (1600, 900), (22, 12, 45))

    def _redraw_background(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return
        sw, sh = self._bg_src.size
        scale = max(w / sw, h / sh)
        bg = self._bg_src.resize((max(1, int(sw * scale)), max(1, int(sh * scale))), Image.Resampling.LANCZOS)
        left = (bg.width - w) // 2
        top = (bg.height - h) // 2
        bg = bg.crop((left, top, left + w, top + h))
        self._bg_photo = ImageTk.PhotoImage(bg)
        self.canvas.itemconfig(self._bg_item, image=self._bg_photo)
        self.canvas.coords(self._bg_item, 0, 0)

    def _token_img(self, d, fill="#2B6EA6", border="#1F5A86"):
        """Token circular con sombra. d ya viene escalado."""
        SH_OFF  = self.S(self.SH_OFF_BASE)
        SH_BLUR = self.S(self.SH_BLUR_BASE)

        key = ("token", d, fill, border, SH_OFF, SH_BLUR)
        if key in self._img_cache:
            return self._img_cache[key]

        aa = 4
        D = d * aa
        base = Image.new("RGBA", (D, D + SH_OFF * aa), (0, 0, 0, 0))

        # sombra
        sh = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([0, 0, D - 1, D - 1], fill=(0, 0, 0, 120))
        sh = sh.filter(ImageFilter.GaussianBlur(max(1, SH_BLUR) * aa))
        base.alpha_composite(sh, (0, (SH_OFF * aa) // 2))

        # círculo
        border_w = max(1, int(round(8 * aa * self.ui_scale)))
        ImageDraw.Draw(base).ellipse([0, 0, D - 1, D - 1], fill=fill, outline=border, width=border_w)

        base = base.resize((d, d + SH_OFF), Image.Resampling.LANCZOS)
        tkimg = ImageTk.PhotoImage(base)
        self._img_cache[key] = tkimg
        return tkimg

    def _create_rect_button(self, text, command, width, height, r,
                            color="#110D2E", hover="#255B88", text_color="#CCCCCC"):
        img_norm  = self._rect_img(width, height, r, color)
        img_hover = self._rect_img(width, height, r, hover)
        img_item = self.canvas.create_image(0, 0, anchor="center", image=img_norm)
        txt_item = self.canvas.create_text(0, 0, text=text, fill=text_color,
                                           font=self.F(16, bold=False), anchor="center")
        btn = {
            "img_item": img_item, "txt_item": txt_item,
            "img_norm": img_norm, "img_hover": img_hover,
            "cmd": command,
            "w": width, "h": height, "r": r,
            "color": color, "hover": hover, "text_color": text_color
        }

        def _btn_hover(_e=None, b=btn):
            now = time.time()
            if now - self._last_hover_ts >= self._hover_cooldown:
                self._play_sfx("hover")
                self._last_hover_ts = now
            self.canvas.itemconfig(b["img_item"], image=b["img_hover"])
            self.canvas.config(cursor="hand2")

        def _btn_leave(_e=None, b=btn):
            self.canvas.itemconfig(b["img_item"], image=b["img_norm"])
            self.canvas.config(cursor="")

        def _btn_click(_e=None, b=btn):
            self._play_sfx("click")
            try:
                self.canvas.itemconfig(b["img_item"], image=b["img_hover"])
                self.after(60, lambda: self.canvas.itemconfig(b["img_item"], image=b["img_norm"]))
            except Exception:
                pass
            if callable(b["cmd"]):
                b["cmd"]()

        for tag in (img_item, txt_item):
            self.canvas.tag_bind(tag, "<Enter>",    _btn_hover)
            self.canvas.tag_bind(tag, "<Leave>",    _btn_leave)
            self.canvas.tag_bind(tag, "<Button-1>", _btn_click)
        return btn

    def _update_rect_button(self, btn, width, height, r):
        """Actualiza imágenes del botón sin recrear los items (mantiene bindings)."""
        btn["w"], btn["h"], btn["r"] = width, height, r
        btn["img_norm"]  = self._rect_img(width, height, r, btn["color"])
        btn["img_hover"] = self._rect_img(width, height, r, btn["hover"])
        self.canvas.itemconfig(btn["img_item"], image=btn["img_norm"])

    def _rect_img(self, w, h, r, fill):
        key = ("rect", w, h, r, fill)
        if key in self._img_cache:
            return self._img_cache[key]
        aa = 4
        W, H, R = w * aa, h * aa, r * aa
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle([0, 0, W - 1, H - 1], R, fill=fill)
        img = img.resize((w, h), Image.Resampling.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self._img_cache[key] = tkimg
        return tkimg

    def _resample_path(self, poly, n):
        if not poly:
            return [(0.5, 0.5)] * n
        segs = []
        total = 0.0
        for i in range(len(poly) - 1):
            x1, y1 = poly[i]
            x2, y2 = poly[i + 1]
            d = math.hypot(x2 - x1, y2 - y1)
            segs.append((d, (x1, y1), (x2, y2)))
            total += d
        if total == 0 or n <= 1:
            return [poly[0]] * n
        out = []
        for k in range(n):
            t = (k / (n - 1)) * total
            acc = 0.0
            for d, (x1, y1), (x2, y2) in segs:
                if acc + d >= t:
                    u = (t - acc) / d if d > 0 else 0
                    out.append((x1 + u * (x2 - x1), y1 + u * (y2 - y1)))
                    break
                acc += d
        return out

    @staticmethod
    def _hex(hx):
        hx = hx.lstrip("#")
        return (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))

    # Debug: imprime coords normalizadas
    def _print_norm_xy(self, e):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        BAR_H = self.S(self.BAR_H_BASE)
        x_rel = round(e.x / max(1, w), 4)
        y_rel = round((e.y - BAR_H) / max(1, (h - BAR_H)), 4)
        print(f"click @ ({x_rel}, {y_rel})  # add to NODE_POS")

    # ========= Íconos de música/sonido (escalables) =========
    def _get_title_color(self) -> str:
        try:
            color = self.canvas.itemcget(self._title_txt, "fill")
            return color if color else self.TEXT
        except Exception:
            return self.TEXT

    def _tint_rgba(self, img: Image.Image, color_str: str) -> Image.Image:
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        r, g, b, a = img.split()
        rgb = ImageColor.getrgb(color_str)
        colored = Image.new("RGBA", img.size, rgb + (255,))
        colored.putalpha(a)
        return colored

    def _ensure_icons_scaled(self):
        """(Re)carga íconos al cambiar escala."""
        target_h = self.S(self.TOP_ICONS_H_BASE)
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

            color = self._get_title_color()
            music_on  = self._tint_rgba(music_on,  color)
            music_off = self._tint_rgba(music_off, color)
            sound_on  = self._tint_rgba(sound_on,  color)
            sound_off = self._tint_rgba(sound_off, color)

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
                self.canvas.tag_bind(self._item_music, "<Enter>",    lambda e: (self._on_icon_hover(), self.canvas.config(cursor="hand2")))
                self.canvas.tag_bind(self._item_music, "<Leave>",    lambda e: self.canvas.config(cursor=""))
                self.canvas.tag_bind(self._item_music, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
            else:
                self.canvas.itemconfig(self._item_music, image=initial_music)

            if self._item_sound is None:
                self._item_sound = self.canvas.create_image(0, 0, anchor="sw", image=initial_sound)
                self.canvas.tag_bind(self._item_sound, "<Enter>",    lambda e: (self._on_icon_hover(), self.canvas.config(cursor="hand2")))
                self.canvas.tag_bind(self._item_sound, "<Leave>",    lambda e: self.canvas.config(cursor=""))
                self.canvas.tag_bind(self._item_sound, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
            else:
                self.canvas.itemconfig(self._item_sound, image=initial_sound)

        except Exception as e:
            print("[LevelsView] No se pudieron cargar/tintar íconos de sonido:", e)

    def _on_icon_hover(self):
        now = time.time()
        if now - self._last_hover_ts >= self._hover_cooldown:
            self._play_sfx("hover")
            self._last_hover_ts = now

    def _place_bottom_left_icons(self, w, h):
        pad = self.S(self.TOP_ICONS_PAD_BASE)
        gap = self.S(self.TOP_ICONS_GAP_BASE)

        if self._item_music is not None:
            self.canvas.coords(self._item_music, pad, h - pad)
            self.canvas.itemconfig(self._item_music, anchor="sw")

        if self._item_sound is not None:
            try:
                bbox = self.canvas.bbox(self._item_music) if self._item_music else None
                music_w = (bbox[2] - bbox[0]) if bbox else self._icons_h_cur
            except Exception:
                music_w = self._icons_h_cur or self.S(self.TOP_ICONS_H_BASE)

            x = pad + (music_w + gap if self._item_music else 0) # type: ignore
            self.canvas.coords(self._item_sound, x, h - pad)
            self.canvas.itemconfig(self._item_sound, anchor="sw")

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

    # ========= Dispatcher SFX =========
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
            print(f"[LevelsView] SFX error ({kind}):", e)
