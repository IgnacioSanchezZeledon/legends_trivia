import os
import tkinter as tk
from tkinter import ttk
import tkextrafont as xfont  # noqa: F401
from pathlib import Path

from utils.resource_path import assets_path, data_path, resource_path
from utils.styles import apply_theme

from models.questions_model import QuestionModel
from models.levels_model import LevelsModel
from models.progress_model import ProgressModel
from controllers.menu_controller import MenuController
from controllers.levels_controller import LevelsController
from controllers.play_controller import PlayController
from views.menu_view import MenuView
from views.levels_view import LevelsView
from views.play_view import PlayView

from utils.audio import MusicManager, SfxManager

class App(tk.Tk):
    """
    Aplicación principal de "Legends Trivia Challenge".
    """

    def __init__(self):
        super().__init__()
        self.title("Legends Trivia Challenge")
        self.geometry("1080x720")
        self.minsize(900, 560)
        self.maxsize(1200, 800)

        # >>> CLAVE: usar base_dir=resource_path("") para que styles.py encuentre assets/fonts en el exe
        apply_theme(self, base_dir=resource_path(""))

        BG = "#27474b"
        self.configure(bg=BG)

        # === Audio ===
        # (assets_path ya apunta a assets dentro del exe/_MEIPASS o proyecto)
        music_path = assets_path("music", "halloween-114610.mp3")
        self.music = MusicManager(music_file=music_path, volume=0.3)
        self.music.play(loops=-1)

        self.sfx = SfxManager(volume=0.2)
        self.sfx.load("hover",     assets_path("sfx", "4.mp3"))
        self.sfx.load("click",     assets_path("sfx", "5.mp3"))
        self.sfx.load("toggle",    assets_path("sfx", "3.mp3"))
        self.sfx.load("correct",   assets_path("sfx", "correct.mp3"))
        self.sfx.load("incorrect", assets_path("sfx", "incorrect.mp3"))

        # Contenedor principal
        self.container = ttk.Frame(self, style="Screen.TFrame")
        self.container.pack(side="top", fill="both", expand=True)

        # === Modelos ===
        self.qm        = QuestionModel("data/questions.json")
        self.lvl_model = LevelsModel(self.qm, "data/levels.json")
        self.progress  = ProgressModel()

        # === Navegación ===
        def switch_view(view: tk.Widget):
            for child in self.container.winfo_children():
                if child is not view:
                    child.destroy()
            view.pack(expand=True, fill="both")

        def build_menu_view() -> MenuView:
            mc = MenuController(switch_view, build_levels_view)
            return MenuView(
                self.container, mc, switch_view,
                sound_manager=self.music, sfx_manager=self.sfx
            )

        def build_levels_view() -> LevelsView:
            lc = LevelsController(switch_view, lambda level: build_play_view(level), self.progress)
            v  = LevelsView(
                self.container, lc, self.progress,
                self.lvl_model.total_levels(), switch_view,
                sound_manager=self.music, sfx_manager=self.sfx
            )
            lc.on_menu = lambda: switch_view(build_menu_view())
            v.refresh()
            return v

        def build_play_view(level_num: int) -> PlayView:
            def switch_to_levels(level_to_open: int | None = None, play_now: bool = False):
                lv = build_levels_view()
                switch_view(lv)
                if play_now and level_to_open is not None and level_to_open <= self.progress.unlocked():
                    switch_view(build_play_view(level_to_open))

            v = PlayView(
                self.container, None, switch_view,
                sound_manager=self.music, sfx_manager=self.sfx
            )
            _ = PlayController(v, level_num, self.lvl_model, self.qm, self.progress, switch_to_levels)
            return v

        switch_view(build_menu_view())


if __name__ == "__main__":
    App().mainloop()
