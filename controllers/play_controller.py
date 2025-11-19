# play_controller.py
class PlayController:
    """
    Controlador del flujo de juego por nivel.

    Funciones clave:
      - Navegación Back/Next por preguntas.
      - Habilita "Next" solo cuando la pregunta actual ha sido respondida.
      - En "Back", muestra la pregunta anterior en modo revisión (sin permitir cambiar la respuesta).
      - Persiste, por cada pregunta:
          * si fue respondida,
          * selección (índice en MCQ o booleano en True/False),
          * correcto/incorrecto,
          * texto de feedback (sin emojis).
      - Reporta a la vista:
          * render_question(q, idx, total, **state)
          * set_next_enabled(bool)
          * set_feedback(str), mark_choice(idx, good), disable_choices()
          * level_complete(...), on_quit_level/... (botones externos)
    """

    def __init__(self, view, level_number, levels_model, question_model, progress_model, switch_to_levels):
        """
        Inicializa el controlador para un nivel y renderiza la primera pregunta.

        Parámetros
        ----------
        view : object
            Vista que implementa la API requerida (ver docstring de la clase).
        level_number : int
            Número del nivel en curso.
        levels_model : object
            Modelo de niveles; expone questions_for_level(level:int) -> list[str].
        question_model : object
            Modelo de preguntas; expone get(qid:str) -> dict con claves "type", "answer_index"/"answer_bool", etc.
        progress_model : object
            Modelo de progreso; expone set_stars(level,int), stars_for(level), unlock_next(level).
        switch_to_levels : callable
            Función para regresar a la vista de niveles (con opciones para abrir un nivel y/o jugar de inmediato).
        """
        self.v = view
        self.level = level_number
        self.lvl_model = levels_model
        self.qm = question_model
        self.progress = progress_model
        self.switch_to_levels = switch_to_levels

        self.qids = self.lvl_model.questions_for_level(self.level)
        self.total = len(self.qids)
        self.index = 0
        self.score = 0

        # Estado por pregunta (persistencia de intento del usuario)
        self.state_by_qid = {
            qid: {
                "answered": False,
                "type": self.qm.get(qid).get("type"),
                "selected_index": None,   # para mcq
                "selected_tf": None,      # para true/false
                "correct": None,
                "feedback": "",
            }
            for qid in self.qids
        }

        # Conectar controller a la vista y renderizar primera pregunta
        self.v.controller = self
        self._render_current()

    # ----------------- Helpers -----------------
    def level_title(self):
        """Devuelve el título del nivel actual para mostrar en la vista."""
        return f"Level {self.level}"

    def _current_qid(self):
        """Devuelve el ID de la pregunta actual."""
        return self.qids[self.index]

    def _current_question(self):
        """Devuelve el dict de la pregunta actual desde el modelo de preguntas."""
        return self.qm.get(self._current_qid())

    def _render_current(self):
        """
        Renderiza la pregunta actual, aplicando modo revisión si ya fue respondida,
        y ajusta el estado del botón Next en la vista.
        """
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
        """
        Maneja la respuesta a una pregunta de opción múltiple (MCQ).

        Parámetros
        ----------
        choice_idx : int
            Índice elegido por el usuario.
        """
        q = self._current_question()
        qid = self._current_qid()
        st = self.state_by_qid[qid]

        # Si ya estaba respondida (revisión), se ignora nueva interacción
        if st["answered"]:
            return

        correct = (choice_idx == q["answer_index"])
        feedback = "Correct!" if correct else "Not quite."

        # Persistir estado
        st.update({
            "answered": True,
            "selected_index": choice_idx,
            "selected_tf": None,
            "correct": correct,
            "feedback": feedback,
        })

        # Aumentar score solo una vez por pregunta
        if correct:
            self.score += 1

        # Actualizar vista: feedback, marcado del usuario y (si falló) revelado de la correcta
        self.v.set_feedback(feedback)
        self.v.mark_choice(choice_idx, correct)
        if not correct:
            self.v.mark_choice(q["answer_index"], True)

        # Bloquear opciones y habilitar Next
        self.v.disable_choices()
        self.v.set_next_enabled(True)

    def on_answer_tf(self, val_true: bool):
        """
        Maneja la respuesta a una pregunta de verdadero/falso.

        Parámetros
        ----------
        val_true : bool
            True si el usuario eligió "True"; False si eligió "False".
        """
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
        """Retrocede una pregunta (si existe) y la renderiza en modo revisión si aplica."""
        if self.index > 0:
            self.index -= 1
            self._render_current()

    def on_nav_next(self):
        """
        Avanza a la siguiente pregunta si existe; en la última, muestra la pantalla
        de fin de nivel.
        """
        if self.index < self.total - 1:
            self.index += 1
            self._render_current()
        else:
            self._complete_level()

    # ----------------- Flujo de nivel -----------------
    def _complete_level(self):
        """
        Calcula estrellas en función del porcentaje de aciertos, registra progreso
        y notifica a la vista para mostrar la pantalla de nivel completado.
        """
        pct = (self.score / self.total) if self.total else 0
        stars = 3 if pct >= 0.8 else (2 if pct >= 0.6 else (1 if pct >= 0.4 else 0))
        self.progress.set_stars(self.level, max(stars, self.progress.stars_for(self.level)))
        self.progress.unlock_next(self.level)
        self.v.level_complete(stars, self.score, self.total)

    # ----------------- Acciones externas -----------------
    def on_quit_level(self):
        """Sale del nivel y vuelve al selector de niveles."""
        self.switch_to_levels()

    def on_retry_level(self):
        """
        Reinicia el estado del nivel actual (índice, score y estado por pregunta)
        y retorna al selector de niveles, abriendo de inmediato este nivel.
        """
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
        """Vuelve al selector y abre el siguiente nivel en modo juego (si procede)."""
        self.switch_to_levels(level_to_open=self.level + 1, play_now=True)

    def on_back_to_levels(self):
        """Vuelve al selector de niveles sin abrir ninguno en particular."""
        self.switch_to_levels()
