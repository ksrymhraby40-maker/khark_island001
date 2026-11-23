"""
صدای بازی
----------
همهٔ صداها هنگام اجرا با ریاضی ساخته می‌شوند (موج سینوسی و نویز)، پس فایل صوتی
جداگانه‌ای لازم نیست و حجم برنامه کم می‌ماند. اگر دستگاه صدا نداشته باشد، بازی
بی‌صدا ادامه پیدا می‌کند.
"""

import io
import math
import os
import random
import struct
import wave
from typing import Callable, Dict, Iterator, List

import pygame

from . import config

RATE = 22050


# ---------------------------------------------------------------- سازندهٔ موج
def _tone(freq: float, seconds: float, volume: float = 0.5,
          decay: float = 6.0, freq_end: float = None) -> List[float]:
    """یک صدای سینوسی که کم‌کم ضعیف می‌شود (و در صورت نیاز زیر و بم‌اش تغییر می‌کند)."""
    count = int(RATE * seconds)
    out, phase = [], 0.0
    for i in range(count):
        t = i / count
        f = freq if freq_end is None else freq + (freq_end - freq) * t
        phase += 2 * math.pi * f / RATE
        out.append(math.sin(phase) * volume * math.exp(-decay * t))
    return out


def _noise(seconds: float, volume: float = 0.5, decay: float = 8.0,
           smooth: float = 0.0, seed: int = 1) -> List[float]:
    """نویز تصادفی؛ هرچه smooth به ۱ نزدیک‌تر باشد صدا بم‌تر می‌شود (مثل انفجار)."""
    rng = random.Random(seed)
    count = int(RATE * seconds)
    out, prev = [], 0.0
    for i in range(count):
        prev = smooth * prev + (1 - smooth) * rng.uniform(-1, 1)
        out.append(prev * volume * math.exp(-decay * i / count))
    return out


def _mix(*tracks: List[float]) -> List[float]:
    length = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(length)]


def _concat(*tracks: List[float]) -> List[float]:
    out: List[float] = []
    for t in tracks:
        out.extend(t)
    return out


def _to_wav(samples: List[float]) -> io.BytesIO:
    """نمونه‌ها را به یک فایل WAV داخل حافظه تبدیل می‌کند."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(
            struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000)) for s in samples))
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- صداها
def _click() -> List[float]:
    return _tone(880, 0.07, 0.35, decay=8)


def _shot() -> List[float]:
    return _mix(_noise(0.14, 0.55, 9, smooth=0.55, seed=2), _tone(150, 0.14, 0.5, 7, 70))


def _hit() -> List[float]:
    return _mix(_noise(0.10, 0.45, 10, smooth=0.1, seed=3), _tone(1300, 0.10, 0.25, 9, 700))


def _boom() -> List[float]:
    return _mix(_noise(0.9, 0.9, 4.5, smooth=0.93, seed=4), _tone(70, 0.8, 0.6, 4, 35))


def _whistle() -> List[float]:
    return _tone(1500, 0.55, 0.18, decay=1.5, freq_end=500)


def _win() -> List[float]:
    notes = (523.25, 659.25, 783.99, 1046.5)
    return _concat(*[_tone(f, 0.16, 0.4, 3) for f in notes[:-1]], _tone(notes[-1], 0.5, 0.4, 3))


def _lose() -> List[float]:
    return _concat(*[_tone(f, 0.26, 0.4, 3) for f in (392.0, 329.6, 261.6)], _tone(196.0, 0.6, 0.4, 3))


def _tick() -> List[float]:
    """تق کوتاه ماشین‌تحریر (برای نوشتن تاریخ در معرفی)."""
    return _tone(2300, 0.035, 0.22, decay=9)


def _siren() -> List[float]:
    """آژیر هشدار: فرکانس مدام بالا و پایین می‌رود (۴٫۲ ثانیه)."""
    seconds, period = 4.2, 1.35
    count = int(RATE * seconds)
    out, phase = [], 0.0
    for i in range(count):
        t = i / RATE
        phase += 2 * math.pi * (760 + 250 * math.sin(2 * math.pi * t / period)) / RATE
        gain = min(1.0, t / 0.15, (seconds - t) / 0.4)
        out.append((math.sin(phase) + 0.35 * math.sin(3 * phase)) * 0.16 * gain)
    return out


def _stinger() -> List[float]:
    """ضربهٔ سنگین و بم برای نمایش «از جزیره دفاع کنید»."""
    return _mix(_tone(110, 1.3, 0.5, 2.4, 52), _tone(165, 1.3, 0.28, 2.6, 80),
                _noise(0.6, 0.4, 6.0, smooth=0.9, seed=9))


class SoundBank:
    """نگهدارندهٔ صداها. با play("نام") پخش می‌شوند."""

    _BUILDERS: Dict[str, Callable[[], List[float]]] = {
        "click": _click, "shot": _shot, "hit": _hit, "boom": _boom,
        "whistle": _whistle, "win": _win, "lose": _lose,
        "tick": _tick, "siren": _siren, "stinger": _stinger,
    }

    def __init__(self) -> None:
        self.sounds: Dict[str, "pygame.mixer.Sound"] = {}
        self.muted = False
        self.music_name = None           # قطعه‌ای که الان پخش می‌شود
        self._music_volume = 0.5
        self.enabled = False
        try:
            pygame.mixer.init(frequency=RATE, size=-16, channels=1)
            self.enabled = True
        except (pygame.error, NotImplementedError):
            self.enabled = False          # دستگاه صدا ندارد؛ بدون صدا ادامه می‌دهیم

    def load_steps(self) -> Iterator[float]:
        """
        صداها را یکی‌یکی می‌سازد و بعد از هر کدام پیشرفت (۰ تا ۱) را برمی‌گرداند؛
        صفحهٔ بارگذاری با آن نوار پیشرفت را پر می‌کند.
        """
        total = len(self._BUILDERS)
        for index, (name, build) in enumerate(self._BUILDERS.items(), start=1):
            if self.enabled:
                try:
                    self.sounds[name] = pygame.mixer.Sound(file=_to_wav(build()))
                except pygame.error:
                    pass
            yield index / total

    def play(self, name: str, volume: float = 1.0) -> None:
        sound = self.sounds.get(name)
        if sound is not None and not self.muted:
            sound.set_volume(max(0.0, min(1.0, volume)))
            sound.play()

    def stop(self, name: str) -> None:
        sound = self.sounds.get(name)
        if sound is not None:
            sound.stop()

    # ---------------------------------------------------------------- موسیقی
    def play_music(self, name: str, volume: float = 0.5) -> None:
        """
        قطعهٔ name (theme یا battle) را بی‌وقفه پخش می‌کند. اگر همان قطعه در حال پخش باشد
        فقط بلندی‌اش عوض می‌شود تا هنگام رفتن از صفحه‌ای به صفحهٔ دیگر موسیقی قطع نشود.
        """
        self._music_volume = volume
        if not self.enabled:
            return
        if self.music_name != name:
            try:
                pygame.mixer.music.load(os.path.join(config.MUSIC_DIR, name + ".wav"))
                try:
                    pygame.mixer.music.play(-1, 0.0, 800)          # تکرار بی‌پایان با شروع نرم
                except TypeError:                                  # نسخه‌های قدیمی pygame
                    pygame.mixer.music.play(-1)
                self.music_name = name
            except (pygame.error, FileNotFoundError):
                self.music_name = None
                return
        self._apply_music_volume()

    def _apply_music_volume(self) -> None:
        try:
            pygame.mixer.music.set_volume(0.0 if self.muted else max(0.0, min(1.0, self._music_volume)))
        except pygame.error:
            pass

    def stop_music(self) -> None:
        if self.enabled:
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass
        self.music_name = None

    def pause_music(self) -> None:
        if self.enabled:
            pygame.mixer.music.pause()

    def resume_music(self) -> None:
        if self.enabled:
            pygame.mixer.music.unpause()

    def toggle_mute(self) -> bool:
        """بی‌صدا/باصدا (کلید M)؛ وضعیت تازه را برمی‌گرداند."""
        self.muted = not self.muted
        self._apply_music_volume()
        return self.muted
