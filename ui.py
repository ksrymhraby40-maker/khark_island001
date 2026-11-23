"""
اجزای رابط کاربری: رسم متن فارسی و دکمه‌ها
--------------------------------------------
"""

from typing import Callable, Dict, List, Optional, Tuple

import pygame

from . import config, persian
from .persian import visual


def _ink_runs(image: "pygame.Surface") -> List[int]:
    """عرض تکه‌های پیوستهٔ «جوهر» (ستون‌هایی که پیکسل دیدنی دارند) را از چپ به راست برمی‌گرداند."""
    width, height = image.get_size()
    runs, current = [], 0
    for x in range(width):
        if any(image.get_at((x, y))[3] > 60 for y in range(height)):
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


class Text:
    """
    رسم متن فارسی با کش. هر متن فقط یک‌بار شکل‌دهی و رندر می‌شود؛
    فریم‌های بعدی تصویر آماده را می‌کشند.
    """

    def __init__(self) -> None:
        self._fonts: Dict[Tuple[int, bool], "pygame.font.Font"] = {}
        self._cache: Dict[tuple, "pygame.Surface"] = {}

    def font(self, size: int, bold: bool = False) -> "pygame.font.Font":
        key = (size, bold)
        if key not in self._fonts:
            path = config.FONT_BOLD if bold else config.FONT_REGULAR
            self._fonts[key] = pygame.font.Font(path, size)
        return self._fonts[key]

    def calibrate(self) -> bool:
        """
        بررسی می‌کند موتور متن pygame ترتیب حروف عربی را خودش برعکس می‌کند یا نه.
        دو حرف جدا (الف باریک و میم پهن) رسم می‌شوند؛ اگر حرف پهن سمت چپ دیده شود یعنی
        موتور ترتیب را عوض کرده و persian.visual باید خروجی‌اش را متناسب با آن تنظیم کند.
        """
        reordered = False
        try:
            font = self.font(48, True)
            white = (255, 255, 255)
            narrow, wide = chr(0xFE8D), chr(0xFEE1)               # الف و میم به شکل «جدا»
            wa = sum(_ink_runs(font.render(narrow, True, white)))
            wm = sum(_ink_runs(font.render(wide, True, white)))
            runs = _ink_runs(font.render(narrow + wide, True, white))
            if wm - wa >= 6 and len(runs) == 2:
                reordered = runs[0] > (wa + wm) / 2                # اولین تکه از چپ پهن است ← برعکس شده
        except Exception:                                          # هر مشکلی: حالت عادی
            reordered = False
        persian.set_engine_reorders(reordered)
        self._cache.clear()
        return reordered

    def render(self, text: str, size: int, color, bold: bool = False) -> "pygame.Surface":
        """متن (می‌تواند چندخطی باشد) را به یک تصویر تبدیل می‌کند."""
        key = (text, size, tuple(color), bold)
        surf = self._cache.get(key)
        if surf is None:
            font = self.font(size, bold)
            lines = [font.render(line or " ", True, color) for line in visual(text).split("\n")]
            if len(lines) == 1:
                surf = lines[0]
            else:
                width = max(l.get_width() for l in lines)
                line_h = font.get_height()
                surf = pygame.Surface((width, line_h * len(lines)), pygame.SRCALPHA)
                for i, line in enumerate(lines):
                    surf.blit(line, ((width - line.get_width()) // 2, i * line_h))
            if len(self._cache) > 600:       # جلوگیری از پر شدن حافظه
                self._cache.clear()
            self._cache[key] = surf
        return surf

    def draw(self, surf: "pygame.Surface", text: str, size: int, color, pos,
             anchor: str = "center", bold: bool = False, shadow: bool = True) -> "pygame.Rect":
        """متن را در نقطهٔ pos می‌کشد؛ anchor مثلاً center، midright، topleft و ... است."""
        image = self.render(text, size, color, bold)
        rect = image.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
        if shadow:
            surf.blit(self.render(text, size, (0, 0, 0), bold), rect.move(2, 3))
        surf.blit(image, rect)
        return rect

    def width(self, text: str, size: int, bold: bool = False) -> int:
        return self.render(text, size, (255, 255, 255), bold).get_width()


class Button:
    """دکمهٔ مستطیلی با برچسب فارسی."""

    def __init__(self, rect, label: str, on_click: Callable[[], None],
                 size: int = 34, enabled: bool = True) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.size = size
        self.enabled = enabled

    def hit(self, pos) -> bool:
        return self.enabled and self.rect.collidepoint(pos)

    def draw(self, surf: "pygame.Surface", text: Text, pointer, pressed: bool = False) -> None:
        hover = self.hit(pointer)
        if not self.enabled:
            fill, border, color = (34, 40, 50), (80, 86, 96), (120, 126, 136)
        elif pressed:
            fill, border, color = (12, 24, 42), config.GOLD, config.GOLD
        elif hover:
            fill, border, color = (34, 70, 112), (255, 214, 110), (255, 255, 255)
        else:
            fill, border, color = (18, 38, 66), config.GOLD, config.WHITE
        rect = self.rect.move(0, 3) if pressed else self.rect
        pygame.draw.rect(surf, (0, 0, 0), rect.move(0, 5), border_radius=16)           # سایه
        pygame.draw.rect(surf, fill, rect, border_radius=16)
        pygame.draw.rect(surf, border, rect, 3, border_radius=16)
        text.draw(surf, self.label, self.size, color, rect.center, bold=True)


class ButtonGroup:
    """
    چند دکمه را با هم مدیریت می‌کند: وقتی روی دکمه‌ای فشار و رها شود صدای کلیک
    پخش می‌شود و تابع دکمه اجرا می‌شود (مثل رفتار معمول دکمه‌ها).
    """

    def __init__(self, buttons: List[Button], play_click: Optional[Callable[[], None]] = None) -> None:
        self.buttons = buttons
        self.play_click = play_click
        self.pointer = (-1, -1)
        self.pressed: Optional[Button] = None

    def move(self, pos) -> None:
        self.pointer = pos

    def press(self, pos) -> None:
        self.pointer = pos
        self.pressed = next((b for b in self.buttons if b.hit(pos)), None)

    def release(self, pos) -> None:
        self.pointer = pos
        button, self.pressed = self.pressed, None
        if button is not None and button.hit(pos):
            if self.play_click:
                self.play_click()
            button.on_click()

    def draw(self, surf: "pygame.Surface", text: Text) -> None:
        for b in self.buttons:
            b.draw(surf, text, self.pointer, pressed=(b is self.pressed and b.hit(self.pointer)))
