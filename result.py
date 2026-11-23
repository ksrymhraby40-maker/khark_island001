"""صفحهٔ نتیجه: «شما بردید» یا «شما باختید» همراه با آمار مرحله."""

import math
import random

import pygame

from .. import config
from ..config import SCREEN_H, SCREEN_W
from ..graphics import dim_overlay
from ..persian import fa_number, format_time
from ..ui import Button, ButtonGroup
from .base import Scene

CONFETTI_COLORS = ((240, 184, 64), (90, 210, 120), (110, 180, 250), (240, 100, 90), (250, 250, 250))


class ResultScene(Scene):
    def __init__(self, app, level, world, won: bool, background) -> None:
        super().__init__(app)
        self.level = level
        self.won = won
        self.t = 0.0
        self.rng = random.Random()
        self.background = background.copy() if background is not None else None

        # آمار
        self.downed = world.downed
        self.accuracy = int(round(world.accuracy * 100))
        self.tanks_alive = world.tanks_alive
        self.survived = level.duration - world.time_left

        # ذرات رنگی برای برد
        self.confetti = []
        if won:
            for _ in range(70):
                self.confetti.append([self.rng.uniform(0, SCREEN_W), self.rng.uniform(-SCREEN_H, 0),
                                      self.rng.uniform(70, 170), self.rng.uniform(0, math.tau),
                                      self.rng.choice(CONFETTI_COLORS)])

        has_next = won and level.number < len(config.LEVELS)
        self.next_level = config.LEVELS[level.number] if has_next else None
        cx = SCREEN_W // 2
        buttons = []
        if self.next_level is not None:
            buttons.append(Button((cx - 190, 468, 380, 64), "مرحلهٔ بعد", self.go_next, 32))
        elif not won:
            buttons.append(Button((cx - 190, 468, 380, 64), "تلاش دوباره", self.retry, 32))
        else:
            buttons.append(Button((cx - 190, 468, 380, 64), "بازی دوباره", self.retry, 32))
        buttons.append(Button((cx - 190, 546, 380, 64), "بازگشت به منو", self.to_menu, 32))
        self.group = ButtonGroup(buttons, play_click=lambda: app.sounds.play("click"))

    def on_enter(self) -> None:
        self.app.sounds.stop_music()                 # فقط جینگل برد یا باخت شنیده شود

    # ---- کارها
    def retry(self) -> None:
        from .play import PlayScene
        self.app.change_scene(PlayScene(self.app, self.level))

    def go_next(self) -> None:
        from .intro import IntroScene
        self.app.change_scene(IntroScene(self.app, self.next_level))

    def to_menu(self) -> None:
        from .menu import MenuScene
        self.app.change_scene(MenuScene(self.app))

    # ---- رویدادها
    def on_press(self, pos) -> None:
        self.group.press(pos)

    def on_release(self, pos) -> None:
        self.group.release(pos)

    def on_move(self, pos) -> None:
        self.group.move(pos)

    def on_back(self) -> None:
        self.to_menu()

    def update(self, dt: float) -> None:
        self.t += dt
        for p in self.confetti:
            p[1] += p[2] * dt
            p[3] += dt * 3
            if p[1] > SCREEN_H + 20:
                p[1] = -20
                p[0] = self.rng.uniform(0, SCREEN_W)

    # ---- رسم
    def draw(self, surf) -> None:
        text = self.app.text
        if self.background is not None:
            surf.blit(self.background, (0, 0))
        else:
            surf.fill((10, 20, 36))
        dim_overlay(surf, 165, (2, 8, 20))

        accent = config.GREEN if self.won else config.RED
        panel = pygame.Rect(0, 0, 720, 560)
        panel.center = (SCREEN_W // 2, 372)
        layer = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (8, 18, 34, 232), layer.get_rect(), border_radius=26)
        surf.blit(layer, panel)
        pygame.draw.rect(surf, accent, panel, 4, border_radius=26)

        title = "شما بردید" if self.won else "شما باختید"
        pop = min(1.0, self.t / 0.35)                       # اندازهٔ عنوان کمی با افکت بزرگ می‌شود
        text.draw(surf, title, int(60 + 28 * pop), accent, (SCREEN_W // 2, 150), bold=True)
        subtitle = ("جزیره خارک از حمله حفظ شد" if self.won
                    else "همهٔ مخزن‌های نفت نابود شدند")
        text.draw(surf, subtitle, 28, config.WHITE, (SCREEN_W // 2, 214), shadow=False)
        pygame.draw.line(surf, accent, (SCREEN_W // 2 - 250, 246), (SCREEN_W // 2 + 250, 246), 3)

        rows = [
            ("هواپیماهای سرنگون‌شده", fa_number(self.downed)),
            ("دقت شلیک", f"{fa_number(self.accuracy)} درصد"),
            ("مخزن‌های سالم", f"{fa_number(self.tanks_alive)} از {fa_number(config.TANK_COUNT)}"),
            ("زمان مقاومت", format_time(math.floor(self.survived))),
        ]
        for i, (label, value) in enumerate(rows):
            y = 286 + i * 44
            text.draw(surf, label, 28, (200, 212, 228), (SCREEN_W // 2 + 290, y), anchor="midright", shadow=False)
            text.draw(surf, value, 28, config.WHITE, (SCREEN_W // 2 - 290, y), anchor="midleft",
                      bold=True, shadow=False)

        self.group.draw(surf, text)
        for x, y, _speed, angle, color in self.confetti:
            w = 12 * abs(math.cos(angle)) + 3
            pygame.draw.rect(surf, color, (x, y, w, 8))
