# views/how_to_play_view.py
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageColor

from utils.resource_path import assets_path


class HowToPlayView(ttk.Frame):
    """
    How To Play (tipo "libro"):
      - Fondo cover + overlay.
      - Header: Quit (izquierda) + "How To Play" centrado.
      - Body: Card centrado con: texto -> imagen -> texto.
      - Footer: iconos music/sfx (abajo-izquierda) + Back/Next (páginas).
      - Escalado: solo reduce.
      - Hotkeys:
          * Left / Right para cambiar página
          * m/M y s/S para toggles
          * Esc para Quit
    """

    BASE_W = 1080
    BASE_H = 720

    TOPBAR = "#150F33"
    TEXT = "#FFFFFF"
    TEXT_SUB = "#cfd8dc"

    BG_OVERLAY_ALPHA = 95

    HEAD_H = 64
    FOOT_H = 56

    # Card base
    CARD_W = 980   # antes 860
    CARD_H = 550   # antes 470
    CARD_R = 22
    CARD_FILL = "#120E2D"   # un poco más oscuro para contraste
    CARD_ALPHA = 210        # semitransparente

    PAD_IN = 26             # padding interno del card

    # Tipos
    HEADER_PT = 28
    BODY_PT = 13
    PAGE_PT = 14

    # Botones
    BTN_W = 190
    BTN_H = 44
    BTN_R = 14

    # Iconos
    ICON_H_BASE = 28
    ICON_GAP = 10
    ICON_PAD = 12

    HOVER_COOLDOWN = 0.08

    def __init__(
        self,
        parent,
        controller,
        switch_view,
        sound_manager=None,
        sfx_manager=None,
        pages=None,
        title="How To Play",
    ):
        super().__init__(parent)

        self.controller = controller
        self.switch_view = switch_view
        self.sound_manager = sound_manager
        self.sfx_manager = sfx_manager
        self.title = title

        # Páginas default (si no te pasan nada)
        self.pages = pages or self._default_pages()
        self.page_idx = 0

        # escala
        self.ui_scale = 1.0
        self._last_size = (0, 0)
        self._resize_after = None
        self._last_hover_ts = 0.0

        # Canvas
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")

        # Fondo
        bg_path = assets_path("images", "bg.jpg")
        self._bg_src = Image.open(bg_path).convert("RGB")
        self._bg_photo = None
        self._bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # caches
        self._bar_cache = {}
        self._btn_cache = {}
        self._card_cache = {}

        # Header / footer
        self._head_img_ref = None
        self._foot_img_ref = None
        self._head_item = self.canvas.create_image(0, 0, anchor="nw")
        self._foot_item = self.canvas.create_image(0, 0, anchor="sw")

        # Header text
        self._header_title_item = self.canvas.create_text(
            0, 0, text=self.title, fill=self.TEXT, font=("Mikado Ultra", self.HEADER_PT),
            anchor="center", justify="center"
        )

        # Card image (se crea como item en canvas)
        self._card_img_ref = None
        self._card_item = self.canvas.create_image(0, 0, anchor="center")

        # Textos dentro del card
        self._card_top_text_item = self.canvas.create_text(
            0, 0, text="", fill=self.TEXT_SUB, font=("Mikado Ultra", self.BODY_PT),
            anchor="nw", justify="left", width=10
        )
        self._card_img_item = self.canvas.create_image(0, 0, anchor="n")
        self._card_bottom_text_item = self.canvas.create_text(
            0, 0, text="", fill=self.TEXT_SUB, font=("Mikado Ultra", self.BODY_PT),
            anchor="nw", justify="left", width=10
        )

        # Indicador de página
        self._page_indicator_item = self.canvas.create_text(
            0, 0, text="", fill=self.TEXT_SUB, font=("Mikado Ultra", self.PAGE_PT),
            anchor="center", justify="center"
        )

        # Botones
        self._btn_quit = None
        self._btn_prev = None
        self._btn_next = None

        # Audio icons
        self._img_music_on = None
        self._img_music_off = None
        self._img_sound_on = None
        self._img_sound_off = None
        self._item_music = None
        self._item_sound = None
        self._icons_h_cur = None

        # Eventos
        self.canvas.bind("<Configure>", self._on_resize)

        # Hotkeys
        self.canvas.bind_all("<Left>",  lambda e: self._prev_page())
        self.canvas.bind_all("<Right>", lambda e: self._next_page())
        self.canvas.bind_all("<Escape>", lambda e: self._on_quit())

        self.canvas.bind_all("<m>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
        self.canvas.bind_all("<M>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
        self.canvas.bind_all("<s>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
        self.canvas.bind_all("<S>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))

        self.after(0, self._build)

    # ---------------- defaults ----------------
    def _default_pages(self):
        """
        Puedes reemplazar estas páginas pasando `pages=[...]` desde App.
        image: ruta relativa dentro de assets (ej: assets/images/xxx.png)
        """
        return [
          {
              "top": "Main Menu\n\n"
                    "Use the buttons to navigate:\n"
                    "• Play: start the game\n"
                    "• How to Play: open this guide\n"
                    "• Credits: project information\n"
                    "• Exit: close the game",
              "image": assets_path("images", "menu.png"),
              "bottom": "Tip: If audio is distracting, use the icons at the bottom-left to mute music or sound effects."
          },
          {
              "top": "Credits Screen\n\n"
                    "This section shows the academic context, institution, learning focus, and developer information.",
              "image": assets_path("images", "credits.png"),
              "bottom": "Use Back to return to the main menu."
          },
          {
              "top": "Select Level\n\n"
                    "Choose a level on the map.\n"
                    "Locked levels show a lock icon until you progress.",
              "image": assets_path("images", "level_selection.png"),
              "bottom": "Tip: Your performance is shown with stars under each completed level."
          },
          {
              "top": "Gameplay Basics\n\n"
                    "Each level contains multiple questions.\n"
                    "Read the question and click one of the four answers.",
              "image": assets_path("images", "question.png"),
              "bottom": "The top bar shows:\n• Level name\n• Question number (e.g., 1/5)"
          },
          {
              "top": "Correct Answer Feedback\n\n"
                    "When you choose correctly, the question is marked as correct and you can continue.",
              "image": assets_path("images", "correct_answer.png"),
              "bottom": "Use Next to move to the next question."
          },
          {
              "top": "Wrong Answer Feedback\n\n"
                    "If you choose the wrong option, the screen indicates the mistake.",
              "image": assets_path("images", "wrong_answer.png"),
              "bottom": "Keep going—finishing the level still helps you learn and improve."
          },
          {
              "top": "Navigation and Audio Controls\n\n"
                    "Bottom controls:\n"
                    "• Back / Next: move through the level questions\n"
                    "• Music icon: toggle background music\n"
                    "• Speaker icon: toggle sound effects",
              "image": assets_path("images", "sounds.png"),
              "bottom": "Shortcuts:\n• Press M to toggle music\n• Press S to toggle sound effects"
          },
          {
              "top": "Level Complete\n\n"
                    "After answering all questions, you will see your results:\n"
                    "• Score\n"
                    "• Stars earned",
              "image": assets_path("images", "level_complete.png"),
              "bottom": "Options:\n• Retry\n• Select Level\n• Next Level (if unlocked)"
          },
          {
              "top": "Congratulations Screen\n\n"
                    "When you finish all levels, the game shows a final message recognizing your progress.",
              "image": assets_path("images", "congratulations.png"),
              "bottom": "From here you can return to Levels or go back to the Main Menu."
          },
      ]

    # ---------------- scale helpers ----------------
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

    # ---------------- build ----------------
    def _build(self):
        self._set_scale_from_canvas()
        self._ensure_icons_scale()

        self._btn_quit = self._create_button_item(
            text="Quit",
            command=self._on_quit,
            width=self.S(self.BTN_W), height=self.S(self.BTN_H), r=self.S(self.BTN_R),
            color="#110D2E", hover="#255B88", text_color="#CCCCCC",
        )
        self._btn_prev = self._create_button_item(
            text="Back",
            command=self._prev_page,
            width=self.S(self.BTN_W), height=self.S(self.BTN_H), r=self.S(self.BTN_R),
            color="#110D2E", hover="#255B88", text_color="#CCCCCC",
        )
        self._btn_next = self._create_button_item(
            text="Next",
            command=self._next_page,
            width=self.S(self.BTN_W), height=self.S(self.BTN_H), r=self.S(self.BTN_R),
            color="#110D2E", hover="#255B88", text_color="#CCCCCC",
        )

        self._redraw_background()
        self._refresh_page_content()
        self._layout_all()

    # ---------------- header/footer bars ----------------
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

    # ---------------- card rendering ----------------
    def _make_card_img(self, w, h, r, fill_hex, alpha=210, aa=4):
        key = ("card", w, h, r, fill_hex, alpha, aa)
        if key in self._card_cache:
            return self._card_cache[key]

        fill_hex = fill_hex.lstrip("#")
        rr = int(fill_hex[0:2], 16)
        gg = int(fill_hex[2:4], 16)
        bb = int(fill_hex[4:6], 16)

        W, H, R = max(1, w * aa), max(1, h * aa), max(0, r * aa)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, W - 1, H - 1], R, fill=(rr, gg, bb, alpha))
        img = img.resize((max(1, w), max(1, h)), Image.Resampling.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self._card_cache[key] = tkimg
        return tkimg

    # ---------------- buttons ----------------
    def _make_round_img(self, w, h, r, fill, aa=4):
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

    def _create_button_item(self, text, command, width, height, r,
                            color="#110D2E", hover="#255B88", text_color="#CCCCCC"):
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

    # ---------------- content ----------------
    def _refresh_page_content(self):
        # header title
        self.canvas.itemconfigure(self._header_title_item, text=self.title, font=self.F(self.HEADER_PT), fill=self.TEXT)

        # card sizes
        card_w = self.S(self.CARD_W)
        card_h = self.S(self.CARD_H)
        card_r = self.S(self.CARD_R)

        card_img = self._make_card_img(card_w, card_h, card_r, self.CARD_FILL, alpha=self.CARD_ALPHA)
        self.canvas.itemconfig(self._card_item, image=card_img)
        self._card_img_ref = card_img

        # page content
        page = self.pages[self.page_idx]
        top_text = page.get("top", "")
        bottom_text = page.get("bottom", "")

        inner_pad = self.S(self.PAD_IN)
        inner_w = max(10, card_w - inner_pad * 2)

        self.canvas.itemconfigure(
            self._card_top_text_item,
            text=top_text,
            font=self.F(self.BODY_PT),
            fill=self.TEXT_SUB,
            width=inner_w,
            justify="left",
        )
        self.canvas.itemconfigure(
            self._card_bottom_text_item,
            text=bottom_text,
            font=self.F(self.BODY_PT),
            fill=self.TEXT_SUB,
            width=inner_w,
            justify="left",
        )

        # indicator
        self.canvas.itemconfigure(
            self._page_indicator_item,
            text=f"{self.page_idx + 1} / {len(self.pages)}",
            font=self.F(self.PAGE_PT),
            fill=self.TEXT_SUB,
        )

        # image in page
        self._set_page_image(page.get("image"), max_w=inner_w, max_h=self.S(280))

        # visual hint for prev/next boundaries (sin deshabilitar eventos)
        self._update_nav_button_states()

    def _set_page_image(self, rel_path: str | None, max_w: int, max_h: int):
        if not rel_path:
            self.canvas.itemconfig(self._card_img_item, image="")
            self._page_img_ref = None
            return

        try:
            img_path = assets_path(*rel_path.split("/"))
            src = Image.open(img_path).convert("RGBA")

            # fit keep ratio
            scale = min(max_w / src.width, max_h / src.height)
            scale = min(1.0, scale)
            nw = max(1, int(src.width * scale))
            nh = max(1, int(src.height * scale))
            out = src.resize((nw, nh), Image.Resampling.LANCZOS)

            tkimg = ImageTk.PhotoImage(out)
            self._page_img_ref = tkimg
            self.canvas.itemconfig(self._card_img_item, image=tkimg)

        except Exception as e:
            print("[HowToPlayView] Could not load page image:", e)
            self.canvas.itemconfig(self._card_img_item, image="")
            self._page_img_ref = None

    def _update_nav_button_states(self):
        # Cambia el color base para simular disabled
        def set_btn_color(btn, enabled: bool):
            if not isinstance(btn, dict):
                return
            btn["color"] = "#110D2E" if enabled else "#1a1538"
            btn["hover"] = "#255B88" if enabled else "#1a1538"
            self._refresh_button_visual(btn)

        set_btn_color(self._btn_prev, self.page_idx > 0)
        set_btn_color(self._btn_next, self.page_idx < (len(self.pages) - 1))

    # ---------------- navigation ----------------
    def _prev_page(self):
        if self.page_idx <= 0:
            self._play_sfx("toggle")
            return
        self._play_sfx("click")
        self.page_idx -= 1
        self._refresh_page_content()
        self._layout_all()

    def _next_page(self):
        if self.page_idx >= len(self.pages) - 1:
            self._play_sfx("toggle")
            return
        self._play_sfx("click")
        self.page_idx += 1
        self._refresh_page_content()
        self._layout_all()

    def _on_quit(self):
        if self.controller and hasattr(self.controller, "on_quit"):
            self.controller.on_quit()

    # ---------------- resize/layout ----------------
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

            # refresh button sizes
            for b in (self._btn_quit, self._btn_prev, self._btn_next):
                if isinstance(b, dict):
                    b["w"], b["h"], b["r"] = self.S(self.BTN_W), self.S(self.BTN_H), self.S(self.BTN_R)
                    self._refresh_button_visual(b)

            self._refresh_page_content()

        self._redraw_background()
        self._layout_all()

    def _layout_all(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        head_h = self.S(self.HEAD_H)
        foot_h = self.S(self.FOOT_H)

        # header bar
        head_img = ImageTk.PhotoImage(self._make_bar_img(w, head_h, self.TOPBAR, 160))
        self.canvas.itemconfig(self._head_item, image=head_img)
        self._head_img_ref = head_img
        self.canvas.coords(self._head_item, 0, 0)

        # footer bar
        foot_img = ImageTk.PhotoImage(self._make_bar_img(w, foot_h, self.TOPBAR, 160))
        self.canvas.itemconfig(self._foot_item, image=foot_img)
        self._foot_img_ref = foot_img
        self.canvas.coords(self._foot_item, 0, h)

        # header title centered
        self.canvas.coords(self._header_title_item, w // 2, head_h // 2)

        # Quit button left in header
        if isinstance(self._btn_quit, dict):
            x = self.S(18) + self._btn_quit["w"] // 2
            y = head_h // 2
            self.canvas.coords(self._btn_quit["img_item"], x, y)
            self.canvas.coords(self._btn_quit["txt_item"], x, y)
            self.canvas.tag_raise(self._btn_quit["img_item"])
            self.canvas.tag_raise(self._btn_quit["txt_item"])

        # Card centered in body area
        card_w = self.S(self.CARD_W)
        card_h = self.S(self.CARD_H)

        top = head_h
        bottom = h - foot_h
        body_h = max(1, bottom - top)

        cx = w // 2
        cy = top + body_h // 2

        self.canvas.coords(self._card_item, cx, cy)
        self.canvas.tag_raise(self._card_item)

        # Place content inside card
        card_left = cx - card_w // 2
        card_top = cy - card_h // 2
        inner_pad = self.S(self.PAD_IN)

        inner_x = card_left + inner_pad
        inner_y = card_top + inner_pad
        inner_w = max(10, card_w - inner_pad * 2)

        # top text
        self.canvas.coords(self._card_top_text_item, inner_x, inner_y)
        self.canvas.tag_raise(self._card_top_text_item)

        self.canvas.update_idletasks()
        tbox = self.canvas.bbox(self._card_top_text_item) or (inner_x, inner_y, inner_x, inner_y)
        y_after_top = tbox[3] + self.S(14)

        # image
        self.canvas.coords(self._card_img_item, inner_x + inner_w // 2, y_after_top)
        self.canvas.itemconfig(self._card_img_item, anchor="n")
        self.canvas.tag_raise(self._card_img_item)

        self.canvas.update_idletasks()
        ibox = self.canvas.bbox(self._card_img_item)
        y_after_img = (ibox[3] + self.S(14)) if ibox else (y_after_top + self.S(14))

        # bottom text
        self.canvas.coords(self._card_bottom_text_item, inner_x, y_after_img)
        self.canvas.tag_raise(self._card_bottom_text_item)

        # page indicator (just above footer)
        self.canvas.coords(self._page_indicator_item, w // 2, h - foot_h - self.S(12))
        self.canvas.tag_raise(self._page_indicator_item)

        # footer icons bottom-left
        self._place_bottom_left_icons(w, h)
        if self._item_music:
            self.canvas.tag_raise(self._item_music)
        if self._item_sound:
            self.canvas.tag_raise(self._item_sound)

        # footer nav buttons right side (Back, Next)
        gap = self.S(14)
        right_pad = self.S(18)

        if isinstance(self._btn_next, dict):
            nx = w - right_pad - self._btn_next["w"] // 2
            ny = h - foot_h // 2
            self.canvas.coords(self._btn_next["img_item"], nx, ny)
            self.canvas.coords(self._btn_next["txt_item"], nx, ny)
            self.canvas.tag_raise(self._btn_next["img_item"])
            self.canvas.tag_raise(self._btn_next["txt_item"])

        if isinstance(self._btn_prev, dict) and isinstance(self._btn_next, dict):
            px = w - right_pad - self._btn_next["w"] - gap - self._btn_prev["w"] // 2
            py = h - foot_h // 2
            self.canvas.coords(self._btn_prev["img_item"], px, py)
            self.canvas.coords(self._btn_prev["txt_item"], px, py)
            self.canvas.tag_raise(self._btn_prev["img_item"])
            self.canvas.tag_raise(self._btn_prev["txt_item"])

        # keep header title above bar
        self.canvas.tag_raise(self._header_title_item)

    # ---------------- background ----------------
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

    # ---------------- audio icons ----------------
    def _get_title_color(self) -> str:
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
            print("[HowToPlayView] No se pudieron cargar/tintar íconos:", e)

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
            self.canvas.coords(self._item_sound, pad + music_w + gap, h - pad) # type: ignore

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

    # ---------------- SFX dispatcher ----------------
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
            print(f"[HowToPlayView] SFX error ({kind}):", e)
