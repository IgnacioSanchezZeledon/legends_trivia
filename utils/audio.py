from __future__ import annotations
from pathlib import Path
import pygame

_mixer_ready = False


def _ensure_mixer(frequency=44100, size=-16, channels=2, buffer=512):
    """
    Inicializa `pygame.mixer` solo una vez, con los parámetros indicados.
    Si falla, imprime un mensaje en consola pero no detiene la aplicación.
    """
    global _mixer_ready
    if not _mixer_ready:
        try:
            pygame.mixer.pre_init(frequency=frequency, size=size, channels=channels, buffer=buffer)
            pygame.mixer.init()
            _mixer_ready = True
        except Exception as e:
            print("[audio] No se pudo inicializar pygame.mixer:", e)


class MusicManager:
    """
    Gestor de música de fondo usando `pygame.mixer.music`.

    Funciones principales:
      - Cargar y reproducir música en loop.
      - Pausar, detener y reanudar.
      - Ajustar volumen y mute.
    """

    def __init__(self, music_file: str | Path | None = None, volume: float = 0.5):
        _ensure_mixer()
        self._muted = False
        self._volume = max(0.0, min(1.0, volume))
        self._music_file = str(music_file) if music_file else None
        try:
            pygame.mixer.music.set_volume(self._volume)
        except Exception:
            pass

    def load(self, music_file: str | Path):
        """Carga un archivo de música (no la reproduce todavía)."""
        self._music_file = str(music_file)

    def play(self, loops: int = -1, start: float = 0.0):
        """
        Reproduce la música cargada.

        Parámetros
        ----------
        loops : int
            Número de repeticiones (-1 para loop infinito).
        start : float
            Posición inicial en segundos.
        """
        if not self._music_file:
            print("[MusicManager] No hay archivo de música cargado.")
            return
        try:
            pygame.mixer.music.load(self._music_file)
            pygame.mixer.music.set_volume(0.0 if self._muted else self._volume)
            pygame.mixer.music.play(loops=loops, start=start)
        except Exception as e:
            print("[MusicManager] Error al reproducir música:", e)

    def stop(self):
        """Detiene la música actual."""
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def pause(self):
        """Pausa la música actual."""
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass

    def resume(self):
        """Reanuda la música pausada."""
        try:
            pygame.mixer.music.unpause()
        except Exception:
            pass

    def set_volume(self, volume: float):
        """
        Ajusta el volumen de la música (0.0 a 1.0).
        Si está en mute, no tiene efecto inmediato.
        """
        self._volume = max(0.0, min(1.0, volume))
        try:
            if not self._muted:
                pygame.mixer.music.set_volume(self._volume)
        except Exception:
            pass

    def toggle_mute(self) -> bool:
        """
        Alterna mute/unmute de la música.
        Retorna True si queda en mute, False si queda con sonido.
        """
        self._muted = not self._muted
        try:
            pygame.mixer.music.set_volume(0.0 if self._muted else self._volume)
        except Exception:
            pass
        return self._muted

    def is_muted(self) -> bool:
        """Devuelve True si la música está en mute."""
        return self._muted


class SfxManager:
    """
    Gestor de efectos de sonido (SFX) usando `pygame.mixer.Sound`.

    Funciones principales:
      - Cargar sonidos y reproducirlos por clave.
      - Reproducir un sonido puntual sin cachearlo.
      - Ajustar volumen global y mute.
    """

    def __init__(self, volume: float = 0.8):
        _ensure_mixer()
        self._muted = False
        self._volume = max(0.0, min(1.0, volume))
        self._cache: dict[str, pygame.mixer.Sound] = {}

    def load(self, key: str, path: str | Path):
        """Carga un efecto y lo asocia a una clave."""
        try:
            snd = pygame.mixer.Sound(str(path))
            snd.set_volume(self._volume)
            self._cache[key] = snd
        except Exception as e:
            print(f"[SfxManager] No se pudo cargar '{path}':", e)

    def play(self, key_or_path: str | Path):
        """
        Reproduce un efecto.

        Parámetros
        ----------
        key_or_path : str | Path
            - Si coincide con una clave cargada, usa el sonido cacheado.
            - Si es una ruta, lo carga y reproduce sin cachearlo.
        """
        if self._muted:
            return
        try:
            key = str(key_or_path)
            if key in self._cache:
                self._cache[key].play()
            else:
                snd = pygame.mixer.Sound(str(key_or_path))
                snd.set_volume(self._volume)
                snd.play()
        except Exception as e:
            print("[SfxManager] Error al reproducir SFX:", e)

    def set_volume(self, volume: float):
        """Ajusta el volumen global de todos los SFX (0.0 a 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        for s in self._cache.values():
            try:
                s.set_volume(self._volume)
            except Exception:
                pass

    def toggle_mute(self) -> bool:
        """
        Alterna mute/unmute de los SFX.
        Retorna True si quedan en mute, False si quedan con sonido.
        """
        self._muted = not self._muted
        return self._muted

    def is_muted(self) -> bool:
        """Devuelve True si los SFX están en mute."""
        return self._muted
