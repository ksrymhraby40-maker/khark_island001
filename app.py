"""
برنامهٔ اصلی: ساخت پنجره، حلقهٔ بازی، تبدیل مختصات و تعویض صفحه‌ها.

بازی روی یک بوم ثابت ۱۲۸۰×۷۲۰ رسم می‌شود. هر فریم این بوم (با حفظ نسبت) به اندازهٔ
پنجرهٔ کامپیوتر یا صفحهٔ گوشی تغییر اندازه می‌دهد و مختصات ماوس/لمس به بوم برمی‌گردد؛
به همین دلیل همان کد روی کامپیوتر و اندروید بدون تغییر کار می‌کند.
"""

import os
import sys

import pygame

from . import config
from .config import FPS, SCREEN_H, SCREEN_W
from .graphics import Backdrop, Sprites, build_map_background
from .sound import SoundBank
from .ui import Text

FADE_SECONDS = 0.18            # مدت محو شدن هنگام تعویض صفحه
IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or hasattr(sys, "getandroidapilevel")


class App:
    def __init__(self) -> None:
        pygame.mixer.pre_init(22050, -16, 1, 1024)
        pygame.init()
        pygame.display.set_caption(config.GAME_TITLE)

        self.window = self._open_window()
        self.canvas = pygame.Surface((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.running = True

        # منابع مشترک بین صفحه‌ها (یک بار ساخته می‌شوند)
        self.text = Text()
        self.text.calibrate()                      # سازگاری با نسخه‌های مختلف موتور متن
        self.sprites = Sprites()
        self.sounds = SoundBank()
        self.backdrop = Backdrop(self.text)
        self.map_bg = build_map_background(self.text)

        # تعویض صفحه با محو شدن
        self._pending = None
        self._fade = 0.0           # ۰ تا ۱؛ هرچه بیشتر، صفحه تیره‌تر
        self._fading_out = False

        from .scenes.loading import LoadingScene
        self.scene = None
        self.set_scene(LoadingScene(self))

    # ------------------------------------------------------------ پنجره
    @staticmethod
    def _open_window() -> "pygame.Surface":
        if IS_ANDROID:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        info = pygame.display.Info()
        width = min(SCREEN_W, int(info.current_w * 0.94))
        height = width * SCREEN_H // SCREEN_W
        if height > info.current_h * 0.88:                    # روی نمایشگرهای کوتاه
            height = int(info.current_h * 0.88)
            width = height * SCREEN_W // SCREEN_H
        return pygame.display.set_mode((max(640, width), max(360, height)), pygame.RESIZABLE)

    def _view(self):
        """مستطیل نمایش بوم داخل پنجره (با حاشیهٔ سیاه برای حفظ نسبت تصویر)."""
        win_w, win_h = self.window.get_size()
        scale = min(win_w / SCREEN_W, win_h / SCREEN_H)
        w, h = max(1, int(SCREEN_W * scale)), max(1, int(SCREEN_H * scale))
        return pygame.Rect((win_w - w) // 2, (win_h - h) // 2, w, h), scale

    def _to_canvas(self, pos):
        """مختصات پنجره را به مختصات بوم ۱۲۸۰×۷۲۰ تبدیل می‌کند."""
        view, scale = self._view()
        x = (pos[0] - view.x) / scale
        y = (pos[1] - view.y) / scale
        return (max(0.0, min(SCREEN_W - 1, x)), max(0.0, min(SCREEN_H - 1, y)))

    # ------------------------------------------------------------ مدیریت صفحه‌ها
    def set_scene(self, scene) -> None:
        """تعویض فوری صفحه."""
        self.scene = scene
        scene.on_enter()

    def change_scene(self, scene) -> None:
        """تعویض صفحه با محو شدن کوتاه."""
        if self._pending is None:
            self._pending = scene
            self._fading_out = True

    def quit(self) -> None:
        self.running = False

    def _update_fade(self, dt: float) -> None:
        if self._pending is None and self._fade <= 0:
            return
        if self._fading_out:
            self._fade = min(1.0, self._fade + dt / FADE_SECONDS)
            if self._fade >= 1.0:
                self.set_scene(self._pending)
                self._pending = None
                self._fading_out = False
        else:
            self._fade = max(0.0, self._fade - dt / FADE_SECONDS)

    # ------------------------------------------------------------ رویدادها
    def _handle_events(self) -> None:
        back_keys = {pygame.K_ESCAPE}
        if hasattr(pygame, "K_AC_BACK"):
            back_keys.add(pygame.K_AC_BACK)               # دکمهٔ برگشت اندروید

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in back_keys:
                    self.scene.on_back()
                elif event.key == pygame.K_F11 and not IS_ANDROID:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_m:
                    self.sounds.toggle_mute()                    # بی‌صدا/باصدا
            elif self._pending is not None:
                continue                                  # هنگام تعویض صفحه ورودی نادیده گرفته می‌شود
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.scene.on_press(self._to_canvas(event.pos))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.scene.on_release(self._to_canvas(event.pos))
            elif event.type == pygame.MOUSEMOTION:
                self.scene.on_move(self._to_canvas(event.pos))

            # اندروید: وقتی برنامه به پس‌زمینه می‌رود تا بازگشت منتظر می‌مانیم
            if hasattr(pygame, "APP_WILLENTERBACKGROUND") and event.type == pygame.APP_WILLENTERBACKGROUND:
                self._wait_for_foreground()

    def _wait_for_foreground(self) -> None:
        pygame.mixer.pause()
        self.sounds.pause_music()
        while self.running:
            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                self.running = False
            elif hasattr(pygame, "APP_DIDENTERFOREGROUND") and event.type == pygame.APP_DIDENTERFOREGROUND:
                break
        pygame.mixer.unpause()
        self.sounds.resume_music()
        self.clock.tick()                                  # زمان توقف به حساب dt نیاید

    # ------------------------------------------------------------ حلقهٔ اصلی
    def _present(self) -> None:
        """بوم را به اندازهٔ پنجره درمی‌آورد و نمایش می‌دهد."""
        view, _scale = self._view()
        self.window.fill((0, 0, 0))
        if view.size == (SCREEN_W, SCREEN_H):
            self.window.blit(self.canvas, view.topleft)
        else:
            self.window.blit(pygame.transform.scale(self.canvas, view.size), view.topleft)
        pygame.display.flip()

    def frame(self, dt: float) -> None:
        """یک فریم کامل: ورودی، به‌روزرسانی، رسم و نمایش."""
        self.window = pygame.display.get_surface() or self.window    # بعد از تغییر اندازهٔ پنجره
        self._handle_events()
        self._update_fade(dt)
        self.scene.update(dt)
        self.scene.draw(self.canvas)
        if self._fade > 0:
            shade = pygame.Surface((SCREEN_W, SCREEN_H))
            shade.set_alpha(int(255 * self._fade))
            self.canvas.blit(shade, (0, 0))
        self._present()

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)       # حداکثر ۰٫۰۵ ثانیه تا بازی هنگام کندی نپرد
            self.frame(dt)
        pygame.quit()


def main() -> None:
    App().run()
    sys.exit(0)
