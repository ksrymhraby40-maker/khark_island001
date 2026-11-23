"""
صفحهٔ بارگذاری
---------------
صفحهٔ سیاه خالص؛ آرم گروه از یک نقطهٔ کوچک ظاهر می‌شود و با شتاب به اندازهٔ کامل
بزرگ می‌شود (در پایان کمی از اندازه می‌گذرد و برمی‌گردد). بعد نوشتهٔ «در حال بارگذاری»
و نوار پیشرفت پدیدار می‌شوند. وقتی نوار پر شد، کل صفحه بالا می‌رود و منو از زیرش پیدا می‌شود.
موسیقی هم از همین صفحه شروع می‌شود.
"""

import pygame

from .. import config
from ..config import SCREEN_H, SCREEN_W
from ..persian import fa_number
from .base import Scene
from .menu import MenuScene

LOGO_CENTER = (SCREEN_W // 2, 262)
LOGO_START_SCALE = 0.03            # اندازهٔ اولیهٔ آرم نسبت به اندازهٔ کامل


def clamp01(k: float) -> float:
    return max(0.0, min(1.0, k))


def ease_out_back(k: float) -> float:
    """شروع سریع، کمی عبور از ۱ و برگشت نرم؛ برای حس «جاگیر شدن» آرم."""
    k = clamp01(k) - 1.0
    return 1.0 + 2.0 * k ** 3 + 1.0 * k ** 2


def fade(color, k: float):
    """رنگ را به‌سمت سیاه می‌برد (k = ۰ سیاه، k = ۱ رنگ اصلی)."""
    return tuple(int(c * clamp01(k)) for c in color)


class LoadingScene(Scene):
    MIN_TIME = 4.8        # حداقل مدت نمایش (ثانیه)
    ZOOM_TIME = 3.0       # مدت بزرگ شدن آرم
    LOGO_FADE = 1.0       # مدت پیدا شدن آرم از سیاهی
    UI_DELAY = 2.0        # ظاهر شدن نوشته و نوار بعد از این زمان شروع می‌شود
    UI_FADE = 0.8
    HOLD_TIME = 0.5       # مکث روی ۱۰۰٪ قبل از بالا رفتن
    SLIDE_TIME = 0.75     # مدت بالا رفتن صفحهٔ بارگذاری

    def __init__(self, app) -> None:
        super().__init__(app)
        self.t = 0.0
        self.real_progress = 0.0                 # پیشرفت واقعی ساخت صداها
        self.progress = 0.0                      # پیشرفت نمایش داده‌شده (نرم)
        self.steps = app.sounds.load_steps()
        self.after_done = None                   # زمان سپری‌شده از رسیدن به ۱۰۰٪
        self.menu = MenuScene(app)               # زیر صفحهٔ بارگذاری آماده می‌شود
        self.layer = pygame.Surface((SCREEN_W, SCREEN_H))

    def on_enter(self) -> None:
        self.app.sounds.play_music("theme", config.MUSIC_VOLUME_MENU)

    # ---- به‌روزرسانی
    def update(self, dt: float) -> None:
        self.t += dt
        if self.real_progress < 1.0:
            try:
                self.real_progress = next(self.steps)
            except StopIteration:
                self.real_progress = 1.0
        goal = min(self.real_progress, self.t / self.MIN_TIME)
        self.progress = min(goal, self.progress + dt * 0.8)

        if self.progress >= 1.0:
            self.after_done = (self.after_done or 0.0) + dt
            self.menu.update(dt)
            if self.after_done >= self.HOLD_TIME + self.SLIDE_TIME:
                self.app.set_scene(self.menu)

    def _slide_offset(self) -> int:
        if self.after_done is None or self.after_done <= self.HOLD_TIME:
            return 0
        k = (self.after_done - self.HOLD_TIME) / self.SLIDE_TIME
        return int(SCREEN_H * min(1.0, k * k))

    # ---- رسم
    def draw(self, surf) -> None:
        offset = self._slide_offset()
        if offset == 0:
            self._draw_loading(surf)
            return
        self.menu.draw(surf)                          # منو از زیر پیدا می‌شود
        self._draw_loading(self.layer)
        surf.blit(self.layer, (0, -offset))           # صفحهٔ بارگذاری بالا می‌رود

    def _draw_logo(self, target) -> None:
        logo = self.app.sprites.logo
        zoom = LOGO_START_SCALE + (1.0 - LOGO_START_SCALE) * ease_out_back(self.t / self.ZOOM_TIME)
        if self.t >= self.ZOOM_TIME:
            image = logo                                # اندازهٔ نهایی؛ نیازی به تغییر اندازه نیست
        else:
            size = (max(2, int(logo.get_width() * zoom)), max(2, int(logo.get_height() * zoom)))
            image = pygame.transform.smoothscale(logo, size)
            alpha = clamp01(self.t / self.LOGO_FADE)
            if alpha < 1.0:
                image.set_alpha(int(255 * alpha))
        target.blit(image, image.get_rect(center=LOGO_CENTER))

    def _draw_loading(self, target) -> None:
        text = self.app.text
        target.fill((0, 0, 0))
        self._draw_logo(target)

        k = clamp01((self.t - self.UI_DELAY) / self.UI_FADE)
        if k <= 0:
            return
        cx = SCREEN_W // 2

        # «در حال بارگذاری…» با نقطه‌های متحرک؛ لبهٔ راست ثابت است تا متن نپرد
        label = "در حال بارگذاری" + "." * (1 + int(self.t * 2.5) % 3)
        full_width = text.width("در حال بارگذاری...", 30)
        text.draw(target, label, 30, fade(config.WHITE, k), (cx + full_width // 2, 536),
                  anchor="midright", shadow=False)

        bar = pygame.Rect(0, 0, 620, 18)
        bar.center = (cx, 580)
        pygame.draw.rect(target, fade((14, 22, 34), k), bar, border_radius=9)
        fill = bar.copy()
        fill.width = int(bar.width * self.progress)
        if fill.width > 6:
            pygame.draw.rect(target, fade(config.ORANGE, k), fill, border_radius=9)
            pygame.draw.rect(target, fade((255, 206, 120), k),
                             (fill.x + 4, fill.y + 3, max(0, fill.width - 8), 4), border_radius=2)
        pygame.draw.rect(target, fade(config.GOLD, k), bar, 2, border_radius=9)

        percent = int(self.progress * 100)
        text.draw(target, f"{fa_number(percent)} درصد", 24, fade((190, 200, 214), k), (cx, 620),
                  shadow=False)
