# play_view.py — Next button only enabled after answering + SFX + enunciado con ✓/✗ + Auto-Scaling UI
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageColor
import math
from pathlib import Path
from utils.resource_path import resource_path, assets_path


class PlayView(ttk.Frame):
    """
    Vista de juego (PlayView) para preguntas tipo MCQ / True-False.

    Novedad: Auto-scaling de toda la UI según la resolución de la ventana.
             La escala solo reduce (no agranda) respecto a 1080x720.

    Características:
      - Fondo responsive con imagen.
      - Tarjeta de enunciado con coloración dinámica del texto: ✓ (verde) o ✗ (rojo)
        según el resultado del USUARIO.
      - Botones de respuesta con estados normal/hover y SFX (hover/click).
      - Reproducción de SFX de correcto/incorrecto solo en el primer marcado.
      - Botón "Next" deshabilitado hasta que exista respuesta (o en modo revisión).
      - Íconos de música/SFX anclados abajo-izquierda con hotkeys (m/M, s/S).
      - Pantalla de "Level Complete".
    """

    # === Paleta y medidas base (diseño en 1080x720) ===
    BG      = "#110D2E"
    CARD    = "#CCCCCC"
    TOPBAR  = "#150F33"
    TEXT    = "#FFFFFF"
    TEXT_SUB= "#cfd8dc"

    BAR_H       = 56
    FOOT_H      = 56
    CARD_R      = 16
    CARD_H      = 210
    CARD_TOP    = 24
    CARD_GAP    = 90
    SH_OFF      = 8
    SH_BLUR     = 3

    BTN_W       = 500
    BTN_H       = 75
    BTN_R       = 16
    BTN_GAP_X   = 28
    BTN_GAP_Y   = 20

    BTN_SH_OFF   = 6
    BTN_SH_BLUR  = 3
    BTN_SH_ALPHA = 90

    TWO_COL_MIN_W = 2*BTN_W + BTN_GAP_X + 40
    TF_ROW_MIN_W  = 2*BTN_W + BTN_GAP_X + 40

    NAV_W = 120
    NAV_H = 40
    NAV_R = 12

    COMPLETE_TOP_OFFSET = 140

    # Tamaño base para auto-scaling
    BASE_W = 1080
    BASE_H = 720

    def __init__(self, parent, controller, switch_view, sound_manager=None, sfx_manager=None):
        super().__init__(parent)
        self.controller = controller
        self.sound_manager = sound_manager
        self.sfx_manager  = sfx_manager

        # Estado de escala
        self.ui_scale = 1.0
        self._icons_h_cur = None

        # Control antispam para hover SFX
        self._hover_cooldown = 0.08
        self._last_hover_ts = 0.0

        # Fondo
        bg_path = assets_path("images", "bg.jpg")
        self._bg_src = Image.open(bg_path).convert("RGB")
        self._bg_photo = None

        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        self._bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # Caches
        self._btn_cache   = {}
        self._panel_cache = {}
        self._bar_cache   = {}
        self._hdr_photo_cache = {}
        self._foot_photo_cache = {}
        self._card_photo_cache = {}

        # Header
        self._hdr_img   = None
        self._hdr_item  = self.canvas.create_image(0, 0, anchor="nw")
        self._level_txt = self.canvas.create_text(
            0, 0, text="Level 1", fill=self.TEXT, font=("Mikado Ultra", 22), anchor="center"
        )
        self._prog_txt  = self.canvas.create_text(
            0, 0, text="", fill=self.TEXT, font=("Mikado Ultra", 20), anchor="e"
        )

        # Iconos de música/SFX (abajo-izquierda)
        self._img_music_on = None
        self._img_music_off = None
        self._img_sound_on = None
        self._img_sound_off = None
        self._item_music = None
        self._item_sound = None
        self._top_icons_h = 28       # se ajusta con escala
        self._top_icons_gap = 10
        self._top_icons_padding = 12
        # Se cargan tras conocer la escala en _on_first_layout

        # Cuerpo (tarjeta y preguntas)
        self._card_img  = None
        self._card_item = None
        self._question_item = None
        self._q_text = ""
        self._buttons   = []

        # Footer
        self._foot_img  = None
        self._foot_item = self.canvas.create_image(0, 0, anchor="sw")
        self._feed_txt  = self.canvas.create_text(
            0, 0, text="", fill=self.TEXT_SUB, font=("Mikado Ultra", 10), anchor="w"
        )
        self._quit_btn  = None

        # Navegación inferior
        self._back_btn = None
        self._next_btn = None
        self._next_enabled = False

        # Estado de pregunta/respuesta
        self._q = None
        self._idx = 0
        self._total = 0
        self._disabled = False
        self.feedback_text = ""
        self._last_choice_was_good = None

        # Bloqueo para evitar doble marcado y conservar el resultado del USUARIO
        self._user_outcome = None
        self._answer_locked = False
        self._answer_idx = None

        # Estado de revisión/preselección
        self._review = False
        self._preselected_index = None
        self._preselected_tf = None
        self._pre_feedback = None
        self._pre_correct = None

        # Redibujo y layout
        self._resize_after = None
        self._last_size = (0, 0)
        self.canvas.bind("<Configure>", self._on_resize)

        self._ready = False
        self._pending_render = None
        self.after(0, self._on_first_layout)

        # Estado de pantalla de nivel completado
        self._complete_active = False
        self._complete = {"title": 0, "score": 0, "stars": 0, "btn_next": 0, "btn_retry": 0, "btn_select": 0}

        self._played_answer_sfx = False

        # Atajos de teclado
        self.canvas.bind_all("<m>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
        self.canvas.bind_all("<M>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
        self.canvas.bind_all("<s>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
        self.canvas.bind_all("<S>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))

    # ===================== Escala =====================
    def _set_scale_from_canvas(self):
        """Actualiza self.ui_scale (solo reduce; nunca agranda)."""
        try:
            w = max(1, self.canvas.winfo_width())
            h = max(1, self.canvas.winfo_height())
        except Exception:
            w, h = self.BASE_W, self.BASE_H
        s = min(w / self.BASE_W, h / self.BASE_H)
        s = min(1.0, max(0.6, s))  # no bajar de 60% para legibilidad (ajustable)
        changed = (abs(getattr(self, "ui_scale", 1.0) - s) > 0.01)
        self.ui_scale = s
        return changed

    def S(self, val: int) -> int:
        """Escala medidas en px."""
        return max(1, int(round(val * getattr(self, "ui_scale", 1.0))))

    def F(self, size: int):
        """Fuente escalada."""
        return ("Mikado Ultra", max(8, int(round(size * getattr(self, "ui_scale", 1.0)))) )

    def _ensure_icons_scale(self):
        """Reescala y re-tintea iconos si cambió la escala."""
        base_h = 28
        new_h  = self.S(base_h)
        if getattr(self, "_icons_h_cur", None) != new_h:
            self._top_icons_h = new_h
            self._load_top_icons()
            self._icons_h_cur = new_h

    # ===================== API pública (Controller) =====================
    def render_question(self, q, idx, total, **state):
        if not self._ready:
            self._pending_render = (q, idx, total, state)
            return

        try:
            self.canvas.update_idletasks()
        except:
            pass

        self._q = q
        self._idx = idx
        self._total = total
        self._last_choice_was_good = None
        self._played_answer_sfx = False

        # Reset de respuesta del usuario
        self._user_outcome = None
        self._answer_locked = False
        self._answer_idx = None

        # Estado entrante
        self._review = bool(state.get("review", False))
        self._preselected_index = state.get("selected_index")
        self._preselected_tf = state.get("selected_tf")
        self._pre_feedback = state.get("feedback")
        self._pre_correct = state.get("correct", state.get("was_good"))

        # Header
        self.canvas.itemconfigure(self._level_txt, text=self.controller.level_title())
        self.canvas.itemconfigure(self._prog_txt,  text=f"{idx+1}/{total}")

        self.set_feedback("")  # neutro
        self._rebuild_body()

        # Visual de preselección
        if self._q:
            if self._q.get("type") == "mcq" and self._preselected_index is not None:
                if self._pre_correct is not None:
                    self.mark_choice(self._preselected_index, bool(self._pre_correct))
                else:
                    b = self._buttons[self._preselected_index]
                    self.canvas.itemconfig(b["img_item"], image=b["img_hover"])
            elif self._q.get("type") == "truefalse" and self._preselected_tf is not None:
                sel_idx = 0 if self._preselected_tf is True else 1
                if self._pre_correct is not None:
                    self.mark_choice(sel_idx, bool(self._pre_correct))
                else:
                    b = self._buttons[sel_idx]
                    self.canvas.itemconfig(b["img_item"], image=b["img_hover"])

        if self._pre_feedback:
            self._last_choice_was_good = True if self._pre_correct is True else (False if self._pre_correct is False else None)
            self.set_feedback(self._pre_feedback)

        # Next solo habilitado si está en revisión
        self.set_next_enabled(self._review)
        if self._review:
            self.disable_choices()

    def mark_choice(self, idx, good=True):
        if not (0 <= idx < len(self._buttons)):
            return

        b = self._buttons[idx]

        if not self._answer_locked:
            # Primer marcado: respuesta del usuario
            self._answer_locked = True
            self._answer_idx = idx
            self._user_outcome = bool(good)

            color = "#266e3b" if good else "#7b2a2a"
            b["img_norm"]  = self._make_button_img(b["w"], b["h"], b["r"], color)
            b["img_hover"] = b["img_norm"]
            self.canvas.itemconfig(b["img_item"], image=b["img_norm"])

            if not self._played_answer_sfx:
                self._play_answer_sfx(bool(good))
                self._played_answer_sfx = True

            self.disable_choices()
            self.set_feedback()
        else:
            # Revelado posterior (no altera el resultado del usuario)
            color = "#266e3b" if good else "#7b2a2a"
            b["img_norm"]  = self._make_button_img(b["w"], b["h"], b["r"], color)
            b["img_hover"] = b["img_norm"]
            self.canvas.itemconfig(b["img_item"], image=b["img_norm"])

    def disable_choices(self):
        self._disabled = True
        for b in self._buttons:
            self.canvas.itemconfig(b["img_item"], image=b["img_norm"])

    # === Enunciado coloreado con ✓/✗ (sin texto de feedback) ===
    def set_feedback(self, _text_ignored=None):
        base = self._q_text or (self._q.get("question","") if self._q else "")
        symbol = ""
        color = "#1a2a2d"  # neutro

        if self._user_outcome is True:
            symbol = "  ✓"
            color = "#2e7d32"
        elif self._user_outcome is False:
            symbol = "  ✗"
            color = "#c62828"

        if self._question_item is not None:
            self.canvas.itemconfigure(self._question_item, text=base + symbol, fill=color)

    # === Habilitar/Deshabilitar Next ===
    def set_next_enabled(self, enabled: bool):
        self._next_enabled = bool(enabled)
        if self._next_btn is not None:
            self._apply_next_visuals()

    def _apply_next_visuals(self):
        if self._next_btn is None:
            return
        enabled = self._next_enabled
        bg_enabled = "#110D2E"
        bg_enabled_hover = "#255B88"
        bg_disabled = "#3A365A"
        text_enabled = "#CCCCCC"
        text_disabled = "#888888"

        # usar dimensiones actuales del botón
        w = self._next_btn.get("w", self.S(self.NAV_W))
        h = self._next_btn.get("h", self.S(self.NAV_H))
        r = self._next_btn.get("r", self.S(self.NAV_R))

        if enabled:
            img_norm  = self._make_round_img(w, h, r, bg_enabled)
            img_hover = self._make_round_img(w, h, r, bg_enabled_hover)
        else:
            img_norm  = self._make_round_img(w, h, r, bg_disabled)
            img_hover = img_norm

        self._next_btn["img_norm"] = img_norm
        self._next_btn["img_hover"] = img_hover
        self.canvas.itemconfig(self._next_btn["img_item"], image=img_norm)
        self.canvas.itemconfig(self._next_btn["txt_item"], fill=(text_enabled if enabled else text_disabled))
        self.canvas.itemconfigure(self._next_btn["txt_item"], font=self.F(18))
        self._next_btn["cmd"] = (lambda: self.controller.on_nav_next()) if enabled else (lambda: None)

    def _refresh_button_visual(self, btn: dict, *, respect_enabled: bool = False):
        """
        Regenera imágenes/fuente del botón según w/h/r actuales.
        Si respect_enabled=True y el botón es Next, se delega a _apply_next_visuals().
        """
        if not btn:
            return

        # Next: tu lógica especial (enabled/disabled)
        if respect_enabled and btn is self._next_btn:
            self._apply_next_visuals()
            return

        # Actualiza fuente
        try:
            self.canvas.itemconfigure(btn["txt_item"], font=self.F(18))
        except Exception:
            pass

        w = btn.get("w", self.S(self.BTN_W))
        h = btn.get("h", self.S(self.BTN_H))
        r = btn.get("r", self.S(self.BTN_R))
        color = btn.get("color", "#110D2E")
        hover = btn.get("hover", "#255B88")
        shadow = bool(btn.get("shadow", True))

        if shadow:
            img_norm  = self._make_button_img(w, h, r, color)
            img_hover = self._make_button_img(w, h, r, hover)
        else:
            img_norm  = self._make_round_img(w, h, r, color)
            img_hover = self._make_round_img(w, h, r, hover)

        btn["img_norm"] = img_norm
        btn["img_hover"] = img_hover

        try:
            self.canvas.itemconfig(btn["img_item"], image=img_norm)
            self.canvas.itemconfig(btn["txt_item"], fill=btn.get("text_color", "#CCCCCC"))
        except Exception:
            pass

    # --- Level Complete ---
    def level_complete(self, stars, score, total):
        if self._card_item is not None:
            self.canvas.delete(self._card_item); self._card_item = None
        if self._question_item is not None:
            self.canvas.delete(self._question_item); self._question_item = None
        for b in self._buttons:
            self.canvas.delete(b["img_item"]); self.canvas.delete(b["txt_item"])
        self._buttons.clear()

        for k in ("_back_btn", "_next_btn", "_quit_btn"):
            btn = getattr(self, k, None)
            if btn:
                self.canvas.itemconfigure(btn["img_item"], state="hidden")
                self.canvas.itemconfigure(btn["txt_item"], state="hidden")

        self._complete_active = True
        self._build_level_complete_plain(stars, score, total)
        self._layout_all()

    def _build_level_complete_plain(self, stars, score, total):
        self._complete["title"] = self.canvas.create_text(
            0, 0, text="Level Complete!", fill=self.TEXT,
            font=self.F(40), anchor="center"
        )
        stars_text = "★"*stars + "☆"*(3 - stars)
        self._complete["score"] = self.canvas.create_text(
            0, 0, text=f"Score: {score}/{total}", fill=self.TEXT,
            font=self.F(22), anchor="center"
        )
        self._complete["stars"] = self.canvas.create_text(
            0, 0, text=f"Stars: {stars_text}", fill=self.TEXT,
            font=self.F(22), anchor="center"
        )
        self._complete["btn_next"] = self._create_button_item(  # type: ignore
            text="Next Level", command=self.controller.on_next_level,
            width=self.S(200), height=self.S(56), r=self.S(16), shadow=False
        )
        self._complete["btn_retry"] = self._create_button_item(  # type: ignore
            text="Retry", command=self.controller.on_retry_level,
            width=self.S(200), height=self.S(56), r=self.S(16), shadow=False
        )
        self._complete["btn_select"] = self._create_button_item(  # type: ignore
            text="Select Level", command=self.controller.on_back_to_levels,
            width=self.S(200), height=self.S(56), r=self.S(16), shadow=False
        )

    def _layout_level_complete_plain(self):
        if not self._complete_active:
            return
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return
        BAR_H   = self.S(self.BAR_H)
        top = BAR_H + self.S(self.COMPLETE_TOP_OFFSET)
        self.canvas.coords(self._complete["title"],  w//2, top)
        self.canvas.coords(self._complete["score"],  w//2, top + self.S(58))
        self.canvas.coords(self._complete["stars"],  w//2, top + self.S(58) + self.S(34))

        gap = self.S(28)
        btn_keys = ["btn_retry", "btn_select", "btn_next"]
        btns = []
        for k in btn_keys:
            btn = self._complete.get(k)
            if isinstance(btn, dict) and "w" in btn:
                btns.append(btn)
        if btns:
            total_w = sum(b["w"] for b in btns) + gap * (len(btns) - 1)
            start_x = w // 2 - total_w // 2
            y = top + self.S(58) + self.S(34) + self.S(70)
            x_cursor = start_x
            for b in btns:
                cx = x_cursor + b["w"] // 2
                self.canvas.coords(b["img_item"], cx, y)
                self.canvas.coords(b["txt_item"], cx, y)
                x_cursor += b["w"] + gap

    # ===================== LAYOUT & DRAW =====================
    def _on_first_layout(self):
        try:
            self.canvas.update_idletasks()
        except:
            pass
        self._set_scale_from_canvas()
        self._ensure_icons_scale()

        self._ready = True
        self._redraw_background()
        self._layout_all()
        if self._pending_render:
            q, idx, total, state = self._pending_render
            self._pending_render = None
            self.render_question(q, idx, total, **state)

    def _on_resize(self, event=None):
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

        self._redraw_background()

        # --- NUEVO: si cambió la escala, reconstruimos el body preservando estado ---
        if scale_changed and self._q is not None:
            # Snapshot del estado actual
            pre = {}
            if self._q.get("type") == "mcq":
                if self._answer_idx is not None:
                    pre["selected_index"] = self._answer_idx
                    pre["correct"] = (True if self._user_outcome is True else
                                      False if self._user_outcome is False else None)
            elif self._q.get("type") == "truefalse":
                if self._answer_idx is not None:
                    pre["selected_tf"] = (self._answer_idx == 0)
                    pre["correct"] = (True if self._user_outcome is True else
                                      False if self._user_outcome is False else None)

            # Reconstruye tarjeta + botones al nuevo tamaño
            self.render_question(self._q, self._idx, self._total, review=self._review, **pre)

        # IMPORTANTE: re-layout completo (header/footer/nav/iconos)
        self._layout_all()

        # Si ya había respuesta del usuario, mantén habilitado Next
        if self._answer_locked:
            self.set_next_enabled(True)

        else:
            # Si no hubo cambio de escala, solo relayout
            self._layout_all()

    def _layout_all(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return

        # === tamaños escalados ===
        BAR_H   = self.S(self.BAR_H)
        FOOT_H  = self.S(self.FOOT_H)
        NAV_W   = self.S(self.NAV_W)
        NAV_H   = self.S(self.NAV_H)
        NAV_R   = self.S(self.NAV_R)

        # Header
        bar_key = (w, BAR_H, self.TOPBAR, 230)
        pil_bar = self._make_bar_img(w, BAR_H, self.TOPBAR, alpha=230)
        if bar_key not in self._hdr_photo_cache:
            self._hdr_photo_cache[bar_key] = ImageTk.PhotoImage(pil_bar)
        self._hdr_img = self._hdr_photo_cache[bar_key]
        self.canvas.itemconfig(self._hdr_item, image=self._hdr_img)
        self.canvas.coords(self._hdr_item, 0, 0)

        # Fuentes escaladas header
        self.canvas.itemconfigure(self._level_txt, font=self.F(22))
        self.canvas.itemconfigure(self._prog_txt,  font=self.F(20))
        self.canvas.coords(self._level_txt, w//2, BAR_H//2)
        self.canvas.coords(self._prog_txt,  w-12,  BAR_H//2)

        # Iconos abajo-izquierda
        self._place_bottom_left_icons(w, h)

        # Footer
        foot_key = (w, FOOT_H, self.TOPBAR, 160)
        pil_foot = self._make_bar_img(w, FOOT_H, self.TOPBAR, alpha=160)
        if foot_key not in self._foot_photo_cache:
            self._foot_photo_cache[foot_key] = ImageTk.PhotoImage(pil_foot)
        self._foot_img = self._foot_photo_cache[foot_key]
        self.canvas.itemconfig(self._foot_item, image=self._foot_img)
        self.canvas.coords(self._foot_item, 0, h)

        # Fuente feedback/footer
        self.canvas.itemconfigure(self._feed_txt, font=self.F(10))
        self.canvas.coords(self._feed_txt, 12, h - FOOT_H//2)

        # Quit (arriba-izquierda)
        if self._quit_btn is None:
            self._quit_btn = self._create_button_item(
                text="Quit",
                command=lambda: self.controller and self.controller.on_quit_level(),
                width=self.S(120), height=self.S(40), r=self.S(12),
                shadow=False
            )
        # asegurar tamaño/estilo al escalar
        self._quit_btn["w"], self._quit_btn["h"], self._quit_btn["r"] = self.S(120), self.S(40), self.S(12)
        self._refresh_button_visual(self._quit_btn)
        self.canvas.coords(self._quit_btn["img_item"], 12 + self.S(60), BAR_H//2)
        self.canvas.coords(self._quit_btn["txt_item"], 12 + self.S(60), BAR_H//2)

        # Back/Next centrados en footer
        if self._back_btn is None:
            self._back_btn = self._create_button_item(
                text="Back",
                command=lambda: self.controller and hasattr(self.controller, 'on_nav_prev') and self.controller.on_nav_prev(),
                width=NAV_W, height=NAV_H, r=NAV_R,
                shadow=False
            )
        if self._next_btn is None:
            self._next_btn = self._create_button_item(
                text="Next",
                command=lambda: None,
                width=NAV_W, height=NAV_H, r=NAV_R,
                shadow=False
            )

        # asegurar que reflejen escala actual
        self._back_btn["w"], self._back_btn["h"], self._back_btn["r"] = NAV_W, NAV_H, NAV_R
        self._next_btn["w"], self._next_btn["h"], self._next_btn["r"] = NAV_W, NAV_H, NAV_R

        # refrescar visuales (aquí estaba el bug principal)
        self._refresh_button_visual(self._back_btn)
        self._refresh_button_visual(self._next_btn, respect_enabled=True)  # aplica enabled/disabled + font

        total_w = NAV_W*2 + self.S(20)
        start_x = w//2 - total_w//2 + NAV_W//2
        cy = h - FOOT_H//2
        self.canvas.coords(self._back_btn["img_item"], start_x, cy)
        self.canvas.coords(self._back_btn["txt_item"], start_x, cy)
        self.canvas.coords(self._next_btn["img_item"], start_x + NAV_W + self.S(20), cy)
        self.canvas.coords(self._next_btn["txt_item"], start_x + NAV_W + self.S(20), cy)

        # Cuerpo
        self._layout_body()

        # Fin de nivel
        if self._complete_active:
            self._layout_level_complete_plain()

        # Asegurar z-order de iconos
        if self._item_music: self.canvas.tag_raise(self._item_music)
        if self._item_sound: self.canvas.tag_raise(self._item_sound)

    # ---------------- Iconos (music / sfx) ----------------
    def _get_title_color(self) -> str:
        try:
            color = self.canvas.itemcget(self._level_txt, "fill")
            return color if color else self.TEXT
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

    def _load_top_icons(self):
        """Carga/escala/tinta iconos. Se llama al iniciar y cuando cambia escala."""
        try:
            icons_dir = Path(assets_path("icons"))
            music_on  = Image.open(icons_dir / "music_on.png").convert("RGBA")
            music_off = Image.open(icons_dir / "music_off.png").convert("RGBA")
            sound_on  = Image.open(icons_dir / "sound_on.png").convert("RGBA")
            sound_off = Image.open(icons_dir / "sound_off.png").convert("RGBA")

            def scale_keep_ratio(img, h):
                w = int(img.width * (h / img.height))
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

            # crear si no existen; si existen, solo actualizar imagen
            if self._item_music is None:
                initial_music = (self._img_music_off if (self.sound_manager and self.sound_manager.is_muted())
                                 else self._img_music_on)
                self._item_music = self.canvas.create_image(0, 0, anchor="sw", image=initial_music)
                self.canvas.tag_bind(self._item_music, "<Enter>",    lambda e: (self._on_icon_hover(), self.canvas.config(cursor="hand2")))
                self.canvas.tag_bind(self._item_music, "<Leave>",    lambda e: self.canvas.config(cursor=""))
                self.canvas.tag_bind(self._item_music, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_music()))
            else:
                self.canvas.itemconfig(
                    self._item_music,
                    image=(self._img_music_off if (self.sound_manager and self.sound_manager.is_muted())
                           else self._img_music_on)
                )

            if self._item_sound is None:
                initial_sound = (self._img_sound_off if (self.sfx_manager and self.sfx_manager.is_muted())
                                 else self._img_sound_on)
                self._item_sound = self.canvas.create_image(0, 0, anchor="sw", image=initial_sound)
                self.canvas.tag_bind(self._item_sound, "<Enter>",    lambda e: (self._on_icon_hover(), self.canvas.config(cursor="hand2")))
                self.canvas.tag_bind(self._item_sound, "<Leave>",    lambda e: self.canvas.config(cursor=""))
                self.canvas.tag_bind(self._item_sound, "<Button-1>", lambda e: (self._play_sfx("toggle"), self._toggle_sfx()))
            else:
                self.canvas.itemconfig(
                    self._item_sound,
                    image=(self._img_sound_off if (self.sfx_manager and self.sfx_manager.is_muted())
                           else self._img_sound_on)
                )

        except Exception as e:
            print("[PlayView] No se pudieron cargar/tintar íconos de sonido:", e)

    def _on_icon_hover(self):
        now = time.time()
        if now - self._last_hover_ts >= self._hover_cooldown:
            self._play_sfx("hover")
            self._last_hover_ts = now

    def _place_bottom_left_icons(self, w, h):
        pad = self.S(12)
        gap = self._top_icons_gap
        if self._item_music is not None:
            self.canvas.coords(self._item_music, pad, h - pad)
            self.canvas.itemconfig(self._item_music, anchor="sw")
        if self._item_sound is not None:
            try:
                bbox = self.canvas.bbox(self._item_music) if self._item_music else None
                music_w = (bbox[2] - bbox[0]) if bbox else self._top_icons_h
            except Exception:
                music_w = self._top_icons_h
            x = pad + (music_w + gap if self._item_music else 0)
            self.canvas.coords(self._item_sound, x, h - pad)
            self.canvas.itemconfig(self._item_sound, anchor="sw")

    def _right_limit_for_text(self) -> int:
        pad = self._top_icons_padding
        gap = self._top_icons_gap
        try:
            bbox = self.canvas.bbox(self._item_sound) if self._item_sound is not None else None
            sound_w = (bbox[2] - bbox[0]) if bbox else self._top_icons_h
        except Exception:
            sound_w = self._top_icons_h
        try:
            bbox2 = self.canvas.bbox(self._item_music) if self._item_music is not None else None
            music_w = (bbox2[2] - bbox2[0]) if bbox2 else self._top_icons_h
        except Exception:
            music_w = self._top_icons_h
        total_icons_w = sound_w + gap + music_w
        return self.canvas.winfo_width() - (pad + total_icons_w + gap)

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

    # ===================== BODY & FACTORIES =====================
    def _rebuild_body(self):
        if self._card_item is not None:
            self.canvas.delete(self._card_item); self._card_item = None
        if self._question_item is not None:
            self.canvas.delete(self._question_item); self._question_item = None
        for b in self._buttons:
            self.canvas.delete(b["img_item"]); self.canvas.delete(b["txt_item"])
        self._buttons.clear()
        self._disabled = False

        self._build_card_and_text()
        self._build_buttons()
        self._layout_body()

    def _layout_body(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2 or self._card_item is None:
            return

        # medidas escaladas
        BAR_H   = self.S(self.BAR_H)
        FOOT_H  = self.S(self.FOOT_H)
        CARD_H  = self.S(self.CARD_H)
        CARD_GAP= self.S(self.CARD_GAP)
        BTN_W   = self.S(self.BTN_W)
        BTN_H   = self.S(self.BTN_H)
        BTN_GAP_X = self.S(self.BTN_GAP_X)
        BTN_GAP_Y = self.S(self.BTN_GAP_Y)
        TWO_COL_MIN_W = self.S(self.TWO_COL_MIN_W)
        TF_ROW_MIN_W  = self.S(self.TF_ROW_MIN_W)

        usable_w = w - self.S(24)
        n = len(self._buttons)
        if n > 0:
            qtype = self._q.get("type") if self._q else None
            if qtype == "mcq":
                cols = 2 if (w >= TWO_COL_MIN_W) else 1
                rows = math.ceil(n / cols)
            else:
                row_fit = (w >= TF_ROW_MIN_W)
                rows = 1 if (row_fit and n >= 2) else n
            block_h = CARD_H + CARD_GAP + rows * BTN_H + (rows - 1) * BTN_GAP_Y
        else:
            block_h = CARD_H

        block_cy = BAR_H + (h - BAR_H - FOOT_H)//2

        card_cx = w//2
        card_cy = block_cy - block_h//2 + CARD_H//2
        self.canvas.coords(self._card_item, card_cx, card_cy)

        if self._question_item is not None:
            card_w = max(self.S(420), min(usable_w, self.S(1000)))
            self.canvas.itemconfig(self._question_item, width=int(card_w - self.S(48)))
            self.canvas.coords(self._question_item, card_cx, card_cy)

        top_y = card_cy + CARD_H//2 + CARD_GAP
        if n == 0:
            return

        qtype = self._q.get("type") if self._q else None
        if qtype == "mcq":
            two_cols = (w >= TWO_COL_MIN_W)
            cols = 2 if two_cols else 1
            total_w = cols * BTN_W + (cols - 1) * BTN_GAP_X
            start_x = w//2 - total_w//2 + BTN_W//2
            for i, b in enumerate(self._buttons):
                r, c = divmod(i, cols)
                x = start_x + c * (BTN_W + BTN_GAP_X)
                y = top_y + r * (BTN_H + BTN_GAP_Y)
                self.canvas.coords(b["img_item"], x, y)
                self.canvas.coords(b["txt_item"], x, y)
        else:
            row_fit = (w >= TF_ROW_MIN_W)
            if row_fit and n >= 2:
                total_w = n * BTN_W + (n - 1) * BTN_GAP_X
                start_x = w//2 - total_w//2 + BTN_W//2
                y = top_y
                for i, b in enumerate(self._buttons):
                    x = start_x + i * (BTN_W + BTN_GAP_X)
                    self.canvas.coords(b["img_item"], x, y)
                    self.canvas.coords(b["txt_item"], x, y)
            else:
                for i, b in enumerate(self._buttons):
                    x = w//2
                    y = top_y + i * (BTN_H + BTN_GAP_Y)
                    self.canvas.coords(b["img_item"], x, y)
                    self.canvas.coords(b["txt_item"], x, y)

    def _build_card_and_text(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            self.after(0, self._rebuild_body); return

        BAR_H   = self.S(self.BAR_H)
        CARD_H  = self.S(self.CARD_H)
        CARD_TOP= self.S(self.CARD_TOP)
        CARD_R  = self.S(self.CARD_R)

        usable_w = w - self.S(24)
        card_w = max(self.S(420), min(usable_w, self.S(1000)))

        panel_key = (card_w, CARD_H, CARD_R, self.CARD, (0,0,0,90), (0, self.S(self.SH_OFF)), self.S(self.SH_BLUR))
        pil_panel = self._make_panel_img(
            card_w, CARD_H, CARD_R,
            fill=self.CARD,
            shadow_color=(0,0,0,90),
            shadow_offset=(0, self.S(self.SH_OFF)),
            blur=self.S(self.SH_BLUR)
        )
        if panel_key not in self._card_photo_cache:
            self._card_photo_cache[panel_key] = ImageTk.PhotoImage(pil_panel)
        self._card_img = self._card_photo_cache[panel_key]

        self._card_item = self.canvas.create_image(
            w//2, BAR_H + CARD_TOP + CARD_H//2, image=self._card_img, anchor="center"
        )

        qtext = self._q.get("question","") if self._q else ""
        self._q_text = qtext
        self._question_item = self.canvas.create_text(
            w//2, BAR_H + CARD_TOP + CARD_H//2,
            text=qtext, fill="#1a2a2d",
            font=self.F(24),
            width=int(card_w - self.S(48)),
            anchor="center", justify="center"
        )

    def _build_buttons(self):
        qtype = self._q.get("type") if self._q else None
        if qtype == "mcq":
            for i, opt in enumerate(self._q.get("options", []) if self._q else []):
                self._buttons.append(self._create_button_item(
                    text=opt,
                    command=lambda i=i: (None if self._disabled else self.controller.on_answer_mcq(i))
                ))
        elif qtype == "truefalse":
            for label, val in [("True", True), ("False", False)]:
                self._buttons.append(self._create_button_item(
                    text=label,
                    command=lambda v=val: (None if self._disabled else self.controller.on_answer_tf(v))
                ))
        else:
            self._buttons.append(self._create_button_item(text="(Unsupported)", command=lambda: None))

    # ============= FACTORÍAS DE IMÁGENES =============
    def _redraw_background(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return
        src_w, src_h = self._bg_src.size
        scale = max(w/src_w, h/src_h)
        bg = self._bg_src.resize((max(1,int(src_w*scale)), max(1,int(src_h*scale))), Image.Resampling.LANCZOS)
        left = (bg.width - w)//2; top = (bg.height - h)//2
        bg = bg.crop((left, top, left + w, top + h))
        self._bg_photo = ImageTk.PhotoImage(bg)
        self.canvas.itemconfig(self._bg_item, image=self._bg_photo)
        self.canvas.coords(self._bg_item, 0, 0)

    def _make_bar_img(self, w, h, color_hex, alpha=160, aa_scale=4):
        key = ("bar", w, h, color_hex, alpha, aa_scale)
        if key in self._bar_cache:
            return self._bar_cache[key]
        color_hex = color_hex.lstrip("#")
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        W, H = max(1, w*aa_scale), max(1, h*aa_scale)
        img = Image.new("RGBA", (W, H), (r, g, b, alpha))
        img = img.resize((w, h), Image.Resampling.LANCZOS)
        self._bar_cache[key] = img
        return img

    def _make_panel_img(self, w, h, r, fill="#CCCCCC",
                        shadow_color=(0,0,0,90), shadow_offset=(0,8), blur=3, aa_scale=4):
        key = (w, h, r, fill, shadow_color, shadow_offset, blur, aa_scale)
        if key in self._panel_cache:
            return self._panel_cache[key].copy()
        W, H, R = w*aa_scale, h*aa_scale, r*aa_scale
        ox, oy = shadow_offset
        ox *= aa_scale; oy *= aa_scale
        base = Image.new("RGBA", (W + abs(ox), H + abs(oy)), (0,0,0,0))
        shadow = Image.new("RGBA", (W, H), (0,0,0,0))
        dsh = ImageDraw.Draw(shadow)
        dsh.rounded_rectangle([0,0,W-1,H-1], R, fill=shadow_color)
        if blur > 0:
            shadow = shadow.filter(ImageFilter.GaussianBlur(blur*aa_scale))
        sx = max(0, ox); sy = max(0, oy)
        base.alpha_composite(shadow, (sx, sy))
        card = Image.new("RGBA", (W, H), (0,0,0,0))
        dc = ImageDraw.Draw(card)
        dc.rounded_rectangle([0,0,W-1,H-1], R, fill=fill)
        base.alpha_composite(card, (0,0))
        base = base.resize((w + abs(ox)//aa_scale, h + abs(oy)//aa_scale), Image.Resampling.LANCZOS)
        self._panel_cache[key] = base.copy()
        return base

    def _make_round_img(self, w, h, r, fill, outline=None, outline_width=0, aa_scale=4):
        key = (w, h, r, fill, outline, outline_width, aa_scale)
        if key in self._btn_cache:
            return self._btn_cache[key]
        W, H, R = w*aa_scale, h*aa_scale, r*aa_scale
        img = Image.new("RGBA", (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0,0,W-1,H-1], R, fill=fill)
        if outline and outline_width>0:
            ow = outline_width*aa_scale
            draw.rounded_rectangle([ow//2, ow//2, W-1-ow//2, H-1-ow//2], R-ow//2, outline=outline, width=ow)
        img = img.resize((w, h), Image.Resampling.LANCZOS)
        tkimg = ImageTk.PhotoImage(img)
        self._btn_cache[key] = tkimg
        return tkimg

    def _make_button_img(self, w, h, r, fill, shadow_color=None, shadow_offset=None, blur=None):
        shadow_color   = shadow_color or (0, 0, 0, self.BTN_SH_ALPHA)
        shadow_offset  = shadow_offset or (0, self.S(self.BTN_SH_OFF))
        blur           = blur if blur is not None else self.S(self.BTN_SH_BLUR)
        key = ("btn_with_shadow", w, h, r, fill, shadow_color, shadow_offset, blur)
        if key in self._btn_cache:
            return self._btn_cache[key]
        pil_img = self._make_panel_img(w, h, r, fill=fill, shadow_color=shadow_color, shadow_offset=shadow_offset, blur=blur)
        tkimg = ImageTk.PhotoImage(pil_img)
        self._btn_cache[key] = tkimg
        return tkimg

    def _create_button_item(self, text, command, width=None, height=None, r=None,
                            color="#110D2E", hover="#255B88", text_color="#CCCCCC", shadow=True):
        w = width or self.S(self.BTN_W)
        h = height or self.S(self.BTN_H)
        rr = r or self.S(self.BTN_R)
        if shadow:
            img_norm  = self._make_button_img(w, h, rr, color)
            img_hover = self._make_button_img(w, h, rr, hover)
        else:
            img_norm  = self._make_round_img(w, h, rr, color)
            img_hover = self._make_round_img(w, h, rr, hover)
        img_item = self.canvas.create_image(0, 0, anchor="center", image=img_norm)
        txt_item = self.canvas.create_text(0, 0, text=text, fill=text_color, font=self.F(18), anchor="center")
        btn = {
            "img_item": img_item, "txt_item": txt_item,
            "img_norm": img_norm, "img_hover": img_hover,
            "w": w, "h": h, "r": rr,
            "cmd": command,
            # guardar estilo para poder re-render al cambiar escala
            "color": color, "hover": hover, "text_color": text_color, "shadow": shadow
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

        for item in (img_item, txt_item):
            self.canvas.tag_bind(item, "<Enter>",   _btn_hover)
            self.canvas.tag_bind(item, "<Leave>",   _btn_leave)
            self.canvas.tag_bind(item, "<Button-1>",_btn_click)

        return btn

    # ========= Despachador SFX =========
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
            print(f"[PlayView] SFX error ({kind}):", e)

    def _play_answer_sfx(self, good: bool):
        sm = self.sfx_manager
        if not sm:
            return
        kind = "correct" if good else "incorrect"
        try:
            if hasattr(sm, "play_ui"):
                sm.play_ui(kind); return
            if hasattr(sm, "play"):
                sm.play(kind); return
            if good and hasattr(sm, "play_correct"):
                sm.play_correct(); return
            if (not good) and hasattr(sm, "play_incorrect"):
                sm.play_incorrect(); return
        except Exception as e:
            print(f"[PlayView] SFX error ({kind}):", e)
