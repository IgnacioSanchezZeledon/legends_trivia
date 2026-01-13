# play_controller.py
class PlayController:
    """
    Controlador del flujo de juego por nivel.

    NUEVO:
      - Si se completa el ÚLTIMO nivel (level == total_levels), navega a CongratulationsView.
    """

    def __init__(
        self,
        view,
        level_number,
        levels_model,
        question_model,
        progress_model,
        switch_to_levels,
        switch_to_congrats=None,
        total_levels=None,
    ):
        self.v = view
        self.level = int(level_number)
        self.lvl_model = levels_model
        self.qm = question_model
        self.progress = progress_model
        self.switch_to_levels = switch_to_levels

        # NUEVO: router a Congrats + total_levels
        self.switch_to_congrats = switch_to_congrats or (lambda: None)
        # Si no te lo pasan, lo calculo del LevelsModel (que sí tiene total_levels())
        self.total_levels = int(total_levels) if total_levels is not None else int(self.lvl_model.total_levels())

        self.qids = self.lvl_model.questions_for_level(self.level)
        self.total = len(self.qids)
        self.index = 0
        self.score = 0

        self.state_by_qid = {
            qid: {
                "answered": False,
                "type": self.qm.get(qid).get("type"),
                "selected_index": None,
                "selected_tf": None,
                "correct": None,
                "feedback": "",
            }
            for qid in self.qids
        }

        self.v.controller = self
        self._render_current()

    # ----------------- Helpers -----------------
    def level_title(self):
        return f"Level {self.level}"

    def _current_qid(self):
        return self.qids[self.index]

    def _current_question(self):
        return self.qm.get(self._current_qid())

    def _render_current(self):
        q = self._current_question()
        qid = self._current_qid()
        st = self.state_by_qid[qid]

        kwargs = {}
        if st["answered"]:
            kwargs = {
                "review": True,
                "selected_index": st["selected_index"],
                "selected_tf": st["selected_tf"],
                "feedback": st["feedback"],
                "correct": st["correct"],
            }

        self.v.render_question(q, self.index, self.total, **kwargs)
        self.v.set_next_enabled(st["answered"])

    # ----------------- Respuestas -----------------
    def on_answer_mcq(self, choice_idx: int):
        q = self._current_question()
        qid = self._current_qid()
        st = self.state_by_qid[qid]

        if st["answered"]:
            return

        correct = (choice_idx == q["answer_index"])
        feedback = "Correct!" if correct else "Not quite."

        st.update({
            "answered": True,
            "selected_index": choice_idx,
            "selected_tf": None,
            "correct": correct,
            "feedback": feedback,
        })

        if correct:
            self.score += 1

        self.v.set_feedback(feedback)
        self.v.mark_choice(choice_idx, correct)
        if not correct:
            self.v.mark_choice(q["answer_index"], True)

        self.v.disable_choices()
        self.v.set_next_enabled(True)

    def on_answer_tf(self, val_true: bool):
        q = self._current_question()
        qid = self._current_qid()
        st = self.state_by_qid[qid]

        if st["answered"]:
            return

        correct = (val_true == q["answer_bool"])
        feedback = "Correct!" if correct else "Not quite."

        st.update({
            "answered": True,
            "selected_index": (0 if val_true else 1),
            "selected_tf": val_true,
            "correct": correct,
            "feedback": feedback,
        })

        if correct:
            self.score += 1

        self.v.set_feedback(feedback)
        self.v.mark_choice(0 if val_true else 1, correct)
        if not correct:
            self.v.mark_choice(0 if q["answer_bool"] else 1, True)

        self.v.disable_choices()
        self.v.set_next_enabled(True)

    # ----------------- Navegación -----------------
    def on_nav_prev(self):
        if self.index > 0:
            self.index -= 1
            self._render_current()

    def on_nav_next(self):
        if self.index < self.total - 1:
            self.index += 1
            self._render_current()
        else:
            self._complete_level()

    # ----------------- Flujo de nivel -----------------
    def _complete_level(self):
        pct = (self.score / self.total) if self.total else 0
        stars = 3 if pct >= 0.8 else (2 if pct >= 0.6 else (1 if pct >= 0.4 else 0))

        self.progress.set_stars(self.level, max(stars, self.progress.stars_for(self.level)))
        self.progress.unlock_next(self.level)

        # NUEVO: si este era el último nivel, ir a Congrats.
        if self.level >= self.total_levels:
            self.switch_to_congrats()
            return

        # Si NO era el último, pantalla normal de fin de nivel.
        self.v.level_complete(stars, self.score, self.total)

    # ----------------- Acciones externas -----------------
    def on_quit_level(self):
        self.switch_to_levels()

    def on_retry_level(self):
        self.index = 0
        self.score = 0
        for qid in self.qids:
            self.state_by_qid[qid].update({
                "answered": False,
                "selected_index": None,
                "selected_tf": None,
                "correct": None,
                "feedback": "",
            })
        self.switch_to_levels(level_to_open=self.level, play_now=True)

    def on_next_level(self):
        self.switch_to_levels(level_to_open=self.level + 1, play_now=True)

    def on_back_to_levels(self):
        self.switch_to_levels()
