# views/congratulations_view.py — Pantalla final (Congratulations) independiente (NO OVERLAP + footer buttons)
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageColor
from pathlib import Path

from utils.resource_path import assets_path


class CongratulationsView(ttk.Frame):
    """
    Pantalla final cuando el jugador termina TODOS los niveles.

    - Independiente.
    - UI auto-escalable (solo reduce).
    - Fondo responsive.
    - Tarjeta central con texto (CR legends + English).
    - Botones en el FOOTER.
    - Iconos música/SFX abajo-izquierda + hotkeys m/M y s/S.
    """

    # === Paleta base ===
    CARD    = "#CCCCCC"
    TOPBAR  = "#150F33"
    TEXT    = "#FFFFFF"
    TEXT_DK = "#1a2a2d"
    TEXT_SUB= "#cfd8dc"

    # Layout base
    BASE_W = 1080
    BASE_H = 720

    BAR_H  = 56
    FOOT_H = 56

    CARD_R   = 18
    CARD_W   = 820
    CARD_H   = 390
    SH_OFF   = 10
    SH_BLUR  = 4

    # Botones footer
    BTN_W    = 220
    BTN_H    = 44
    BTN_R    = 14
    BTN_GAP  = 16

    # Iconos audio
    ICON_H_BASE  = 28
    ICON_GAP     = 10
    ICON_PAD     = 12

    # Padding interno del card + gaps entre textos
    CARD_PAD_X = 56
    CARD_PAD_TOP = 48
    CARD_PAD_BOTTOM = 44
    GAP_TITLE_SUB = 14
    GAP_SUB_PARA  = 18

    def __init__(
        self,
        parent,
        controller,
        switch_view,
        sound_manager=None,
        sfx_manager=None,
        title="CONGRATULATIONS!",
        subtitle="YOU FINISHED ALL LEVELS",
        paragraph=None,
    ):
        super().__init__(parent)

        self.controller = controller
        self.switch_view = switch_view
        self.sound_manager = sound_manager
        self.sfx_manager   = sfx_manager

        self._title = title
        self._subtitle = subtitle
        self._paragraph = paragraph or (
            "You’ve explored Costa Rica’s legends while practicing real English in context. "
            "Each question helped you build vocabulary, improve comprehension, and connect language "
            "with culture—just like learning is supposed to feel: memorable and meaningful."
        )

        # escala
        self.ui_scale = 1.0
        self._icons_h_cur = None

        # anti-spam hover sfx
        self._hover_cooldown = 0.08
        self._last_hover_ts = 0.0

        # Canvas + fondo
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")

        bg_path = assets_path("images", "bg.jpg")
        self._bg_src = Image.open(bg_path).convert("RGB")
        self._bg_photo = None
        self._bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # caches
        self._bar_cache = {}
        self._btn_cache = {}

        # header / footer
        self._hdr_img_ref = None
        self._foot_img_ref = None

        self._hdr_item = self.canvas.create_image(0, 0, anchor="nw")
        self._hdr_txt  = self.canvas.create_text(
            0, 0, text="LEGENDS TRIVIA CHALLENGE", fill=self.TEXT,
            font=("Mikado Ultra", 22), anchor="center"
        )

        self._foot_item = self.canvas.create_image(0, 0, anchor="sw")
        self._foot_txt  = self.canvas.create_text(
            0, 0, text="", fill=self.TEXT_SUB,
            font=("Mikado Ultra", 10), anchor="w"
        )

        # card + textos
        self._card_item = None
        self._card_img  = None
        self._title_item = None
        self._subtitle_item = None
        self._para_item = None

        # botones footer
        self._btn_levels  = None
        self._btn_menu    = None

        # iconos
        self._img_music_on = None
        self._img_music_off = None
        self._img_sound_on = None
        self._img_sound_off = None
        self._item_music = None
        self._item_sound = None
        self._top_icons_h = self.ICON_H_BASE

        # eventos
        self._resize_after = None
        self._last_size = (0, 0)
        self.canvas.bind("<Configure>", self._on_resize)

        # hotkeys
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

        self._build_card()

        # botones en footer
        self._btn_levels = self._create_button_item(
            text="Levels",
            command=self._on_levels,
            width=self.S(self.BTN_W), height=self.S(self.BTN_H), r=self.S(self.BTN_R),
            shadow=False
        )
        self._btn_menu = self._create_button_item(
            text="Main Menu",
            command=self._on_menu,
            width=self.S(self.BTN_W), height=self.S(self.BTN_H), r=self.S(self.BTN_R),
            shadow=False
        )

        self._redraw_background()
        self._layout_all()

    # ----------------- Controller actions -----------------

    def _on_levels(self):
        if self.controller and hasattr(self.controller, "on_levels"):
            self.controller.on_levels()

    def _on_menu(self):
        if self.controller and hasattr(self.controller, "on_menu"):
            self.controller.on_menu()

    # ----------------- Card + text items -----------------
    def _build_card(self):
        # limpiar anterior
        for item in (self._card_item, self._title_item, self._subtitle_item, self._para_item):
            if item:
                try:
                    self.canvas.delete(item)
                except Exception:
                    pass
        self._card_item = self._title_item = self._subtitle_item = self._para_item = None

        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())

        card_w = max(1, min(self.S(self.CARD_W), w - self.S(48)))
        card_h = max(1, self.S(self.CARD_H))
        card_r = max(1, self.S(self.CARD_R))

        # panel
        sh_off = max(0, self.S(self.SH_OFF))
        sh_blur = max(0, self.S(self.SH_BLUR))
        pil_panel = self._make_panel_img(
            card_w, card_h, card_r,
            fill=self.CARD,
            shadow_color=(0, 0, 0, 90),
            shadow_offset=(0, sh_off),
            blur=sh_blur,
        )
        self._card_img = ImageTk.PhotoImage(pil_panel)

        cx = w // 2
        cy = self.S(self.BAR_H) + (h - self.S(self.BAR_H) - self.S(self.FOOT_H)) // 2
        self._card_item = self.canvas.create_image(cx, cy, image=self._card_img, anchor="center")

        # textos (solo crear; el layout real se hace en _layout_card_texts con bbox)
        text_w_title = int(max(10, card_w - self.S(self.CARD_PAD_X)))
        text_w_para  = int(max(10, card_w - self.S(self.CARD_PAD_X + 30)))

        self._title_item = self.canvas.create_text(
            cx, cy, text=self._title,
            fill=self.TEXT_DK, font=self.F(44),
            anchor="n", justify="center", width=text_w_title
        )
        self._subtitle_item = self.canvas.create_text(
            cx, cy, text=self._subtitle,
            fill=self.TEXT_DK, font=self.F(22),
            anchor="n", justify="center", width=text_w_title
        )
        self._para_item = self.canvas.create_text(
            cx, cy, text=self._paragraph,
            fill=self.TEXT_DK, font=self.F(16),
            anchor="n", justify="center", width=text_w_para
        )

        # posicionar en cascada
        self._layout_card_texts()

    def _layout_card_texts(self):
        """Layout robusto: usa bbox de cada texto para evitar solapamientos."""
        if not (self._card_item and self._title_item and self._subtitle_item and self._para_item):
            return

        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        BAR_H  = self.S(self.BAR_H)
        FOOT_H = self.S(self.FOOT_H)

        cx = w // 2
        cy = BAR_H + (h - BAR_H - FOOT_H) // 2

        # dimensiones reales del card
        card_w = max(1, min(self.S(self.CARD_W), w - self.S(48)))
        card_h = max(1, self.S(self.CARD_H))

        top_y = cy - card_h // 2 + self.S(self.CARD_PAD_TOP)

        # gaps
        gap1 = self.S(self.GAP_TITLE_SUB)
        gap2 = self.S(self.GAP_SUB_PARA)

        # 1) title
        self.canvas.coords(self._title_item, cx, top_y)
        self.canvas.update_idletasks()
        b1 = self.canvas.bbox(self._title_item) or (0, 0, 0, 0)
        cur_y = b1[3] + gap1  # bottom + gap

        # 2) subtitle
        self.canvas.coords(self._subtitle_item, cx, cur_y)
        self.canvas.update_idletasks()
        b2 = self.canvas.bbox(self._subtitle_item) or (0, 0, 0, 0)
        cur_y = b2[3] + gap2

        # 3) paragraph
        self.canvas.coords(self._para_item, cx, cur_y)

        # si el párrafo se sale por abajo, reduce un poco el tamaño de fuente del título/subtítulo
        # (sin loop infinito: 1 ajuste máximo)
        self.canvas.update_idletasks()
        b3 = self.canvas.bbox(self._para_item) or (0, 0, 0, 0)
        card_bottom = cy + card_h // 2 - self.S(self.CARD_PAD_BOTTOM)
        if b3[3] > card_bottom:
            # bajar un poco el título y subtítulo (más seguro que cambiar tamaños agresivos)
            shift = min(self.S(18), max(0, b3[3] - card_bottom))
            self.canvas.move(self._title_item, 0, -shift)
            self.canvas.move(self._subtitle_item, 0, -shift)
            self.canvas.move(self._para_item, 0, -shift)

    # ----------------- Resize/Layout -----------------
    def _on_resize(self, _evt=None):
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
        if scale_changed:
            self._ensure_icons_scale()

            # reconstruye card y textos a nueva escala (font sizes cambian)
            self._build_card()

            # re-dimensiona botones
            for b in (self._btn_levels, self._btn_menu):
                if isinstance(b, dict):
                    b["w"], b["h"], b["r"] = self.S(self.BTN_W), self.S(self.BTN_H), self.S(self.BTN_R)
                    self._refresh_button_visual(b)

        self._redraw_background()
        self._layout_all()

    def _layout_all(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        BAR_H  = self.S(self.BAR_H)
        FOOT_H = self.S(self.FOOT_H)

        # header
        hdr_img = ImageTk.PhotoImage(self._make_bar_img(w, BAR_H, self.TOPBAR, 230))
        self.canvas.itemconfig(self._hdr_item, image=hdr_img)
        self._hdr_img_ref = hdr_img
        self.canvas.coords(self._hdr_item, 0, 0)

        self.canvas.itemconfigure(self._hdr_txt, font=self.F(22))
        self.canvas.coords(self._hdr_txt, w // 2, BAR_H // 2)

        # footer
        foot_img = ImageTk.PhotoImage(self._make_bar_img(w, FOOT_H, self.TOPBAR, 160))
        self.canvas.itemconfig(self._foot_item, image=foot_img)
        self._foot_img_ref = foot_img
        self.canvas.coords(self._foot_item, 0, h)

        self.canvas.itemconfigure(self._foot_txt, font=self.F(10))
        self.canvas.coords(self._foot_txt, self.S(12), h - FOOT_H // 2)

        # iconos bottom-left
        self._place_bottom_left_icons(w, h)
        if self._item_music: self.canvas.tag_raise(self._item_music)
        if self._item_sound: self.canvas.tag_raise(self._item_sound)

        # card centrado + textos cascada
        cx = w // 2
        cy = BAR_H + (h - BAR_H - FOOT_H) // 2
        if self._card_item:
            self.canvas.coords(self._card_item, cx, cy)
        self._layout_card_texts()

        # botones en footer centrados
        btns = [b for b in (self._btn_levels, self._btn_menu) if isinstance(b, dict)]
        if btns:
            gap = self.S(self.BTN_GAP)
            total_w = sum(b["w"] for b in btns) + gap * (len(btns) - 1)
            start_x = w // 2 - total_w // 2
            y = h - FOOT_H // 2

            x = start_x
            for b in btns:
                cx_btn = x + b["w"] // 2
                self.canvas.coords(b["img_item"], cx_btn, y)
                self.canvas.coords(b["txt_item"], cx_btn, y)
                x += b["w"] + gap

            for b in btns:
                self.canvas.tag_raise(b["img_item"])
                self.canvas.tag_raise(b["txt_item"])

    # ----------------- Fondo -----------------
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

    # ----------------- PIL helpers -----------------
    def _make_bar_img(self, w, h, color_hex, alpha=160, aa=4):
        key = ("bar", w, h, color_hex, alpha, aa)
        if key in self._bar_cache:
            return self._bar_cache[key].copy()

        color_hex = color_hex.lstrip("#")
        r = int(color_hex[0:2], 16); g = int(color_hex[2:4], 16); b = int(color_hex[4:6], 16)
        W, H = max(1, w * aa), max(1, h * aa)
        img = Image.new("RGBA", (W, H), (r, g, b, alpha))
        out = img.resize((max(1, w), max(1, h)), Image.Resampling.LANCZOS)
        self._bar_cache[key] = out.copy()
        return out

    def _make_panel_img(self, w, h, r, fill="#CCCCCC",
                        shadow_color=(0,0,0,90), shadow_offset=(0,10), blur=4, aa=4):
        w = max(1, int(w))
        h = max(1, int(h))
        r = max(0, int(r))

        aa = max(1, int(aa))
        ox, oy = shadow_offset
        ox = int(ox); oy = int(oy)

        W = max(1, w * aa)
        H = max(1, h * aa)
        R = max(0, r * aa)

        ox *= aa
        oy *= aa

        base_w = max(1, W + abs(ox))
        base_h = max(1, H + abs(oy))
        base = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))

        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(shadow)
        d.rounded_rectangle([0, 0, W - 1, H - 1], R, fill=shadow_color)

        blur = max(0, int(blur))
        if blur > 0:
            shadow = shadow.filter(ImageFilter.GaussianBlur(blur * aa))

        base.alpha_composite(shadow, (max(0, ox), max(0, oy)))

        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d2 = ImageDraw.Draw(card)
        d2.rounded_rectangle([0, 0, W - 1, H - 1], R, fill=fill)
        base.alpha_composite(card, (0, 0))

        out_w = max(1, w + abs(ox) // aa)
        out_h = max(1, h + abs(oy) // aa)
        return base.resize((out_w, out_h), Image.Resampling.LANCZOS)

    def _make_round_img(self, w, h, r, fill, aa=4):
        w = max(1, int(w)); h = max(1, int(h)); r = max(0, int(r)); aa = max(1, int(aa))
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
        img_norm  = self._make_round_img(width, height, r, color)
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
            if now - self._last_hover_ts >= self._hover_cooldown:
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
        if not btn:
            return
        btn["img_norm"]  = self._make_round_img(btn["w"], btn["h"], btn["r"], btn.get("color", "#110D2E"))
        btn["img_hover"] = self._make_round_img(btn["w"], btn["h"], btn["r"], btn.get("hover", "#255B88"))
        self.canvas.itemconfig(btn["img_item"], image=btn["img_norm"])
        self.canvas.itemconfig(btn["txt_item"], font=self.F(16), fill=btn.get("text_color", "#CCCCCC"))

    # ----------------- Audio icons -----------------
    def _get_title_color(self) -> str:
        try:
            c = self.canvas.itemcget(self._hdr_txt, "fill")
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
        if self._icons_h_cur != new_h:
            self._top_icons_h = new_h
            self._load_top_icons()
            self._icons_h_cur = new_h

    def _load_top_icons(self):
        try:
            icons_dir = Path(assets_path("icons"))
            music_on  = Image.open(icons_dir / "music_on.png").convert("RGBA")
            music_off = Image.open(icons_dir / "music_off.png").convert("RGBA")
            sound_on  = Image.open(icons_dir / "sound_on.png").convert("RGBA")
            sound_off = Image.open(icons_dir / "sound_off.png").convert("RGBA")

            def scale_keep_ratio(img, h):
                h = max(1, int(h))
                w = max(1, int(img.width * (h / img.height)))
                return img.resize((w, h), Image.Resampling.LANCZOS)

            music_on  = scale_keep_ratio(music_on,  self._top_icons_h)
            music_off = scale_keep_ratio(music_off, self._top_icons_h)
            sound_on  = scale_keep_ratio(sound_on,  self._top_icons_h)
            sound_off = scale_keep_ratio(sound_off, self._top_icons_h)

            color = self._get_title_color()
            music_on  = self._tint_rgba(music_on,  color)
            music_off = self._tint_rgba(music_off, color)
            sound_on  = self._tint_rgba(sound_on,  color)
            sound_off = self._tint_rgba(sound_off, color)

            self._img_music_on  = ImageTk.PhotoImage(music_on)
            self._img_music_off = ImageTk.PhotoImage(music_off)
            self._img_sound_on  = ImageTk.PhotoImage(sound_on)
            self._img_sound_off = ImageTk.PhotoImage(sound_off)

            if self._item_music is None:
                initial = self._img_music_off if (self.sound_manager and self.sound_manager.is_muted()) else self._img_music_on
                self._item_music = self.canvas.create_image(0, 0, anchor="sw", image=initial)
                self.canvas.tag_bind(self._item_music, "<Enter>", lambda e: (self._on_icon_hover(), self.canvas.config(cursor="hand2")))
                self.canvas.tag_bind(self._item_music, "<Leave>", lambda e: self.canvas.config(cursor=""))
                self.canvas.tag_bind(self._item_music, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
            else:
                self.canvas.itemconfig(self._item_music, image=self._img_music_off if (self.sound_manager and self.sound_manager.is_muted()) else self._img_music_on)

            if self._item_sound is None:
                initial = self._img_sound_off if (self.sfx_manager and self.sfx_manager.is_muted()) else self._img_sound_on
                self._item_sound = self.canvas.create_image(0, 0, anchor="sw", image=initial)
                self.canvas.tag_bind(self._item_sound, "<Enter>", lambda e: (self._on_icon_hover(), self.canvas.config(cursor="hand2")))
                self.canvas.tag_bind(self._item_sound, "<Leave>", lambda e: self.canvas.config(cursor=""))
                self.canvas.tag_bind(self._item_sound, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
            else:
                self.canvas.itemconfig(self._item_sound, image=self._img_sound_off if (self.sfx_manager and self.sfx_manager.is_muted()) else self._img_sound_on)

        except Exception as e:
            print("[CongratulationsView] No se pudieron cargar/tintar íconos:", e)

    def _on_icon_hover(self):
        now = time.time()
        if now - self._last_hover_ts >= self._hover_cooldown:
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
                music_w = (bbox[2] - bbox[0]) if bbox else self._top_icons_h
            except Exception:
                music_w = self._top_icons_h
            self.canvas.coords(self._item_sound, pad + music_w + gap, h - pad)

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
            print(f"[CongratulationsView] SFX error ({kind}):", e)
