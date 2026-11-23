"""منوی اصلی: «شروع بازی» در وسط و «خروج» زیر آن، روی پس‌زمینهٔ متحرک جزیره."""

import random

import pygame

from .. import config
from ..config import SCREEN_W
from ..graphics import dim_overlay
from ..ui import Button, ButtonGroup
from .base import Scene


class MenuScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.t = 0.0
        self.rng = random.Random()
        self.flybys = []                    # هواپیماهای تزئینی: [x، y، سرعت، نوع]
        self._next_flyby = 0.3
        logo = app.sprites.logo
        height = 118
        self.small_logo = pygame.transform.smoothscale(
            logo, (max(1, logo.get_width() * height // logo.get_height()), height))

        cx = SCREEN_W // 2
        self.group = ButtonGroup([
            Button((cx - 190, 300, 380, 78), "شروع بازی", self.start_game, 40),
            Button((cx - 190, 402, 380, 78), "خروج", app.quit, 40),
        ], play_click=lambda: app.sounds.play("click"))

    def on_enter(self) -> None:
        self.app.sounds.play_music("theme", config.MUSIC_VOLUME_MENU)

    # ---- کارها
    def start_game(self) -> None:
        from .levels import LevelSelectScene      # واردسازی دیرهنگام برای جلوگیری از چرخهٔ import
        self.app.change_scene(LevelSelectScene(self.app))

    # ---- رویدادها
    def on_press(self, pos) -> None:
        self.group.press(pos)

    def on_release(self, pos) -> None:
        self.group.release(pos)

    def on_move(self, pos) -> None:
        self.group.move(pos)

    # ---- به‌روزرسانی و رسم
    def update(self, dt: float) -> None:
        self.t += dt
        self._next_flyby -= dt
        if self._next_flyby <= 0:
            kind = self.rng.choice((config.F16, config.F35))
            self.flybys.append([-kind.width, self.rng.uniform(150, 420),
                                self.rng.uniform(90, 150), kind.key])
            self._next_flyby = self.rng.uniform(3.0, 5.5)
        for plane in self.flybys:
            plane[0] += plane[2] * dt
        self.flybys = [p for p in self.flybys if p[0] < SCREEN_W + 150]

    def draw(self, surf) -> None:
        backdrop = self.app.backdrop
        backdrop.draw_back(surf, self.t)
        for x, y, _speed, key in self.flybys:                 # هواپیماهای تزئینی پشت جزیره
            sprite = self.app.sprites.planes[key]
            surf.blit(sprite, sprite.get_rect(center=(int(x), int(y))))
        backdrop.draw_island(surf)
        dim_overlay(surf, 70, (4, 12, 28))

        text = self.app.text
        text.draw(surf, config.GAME_TITLE, 84, config.GOLD, (SCREEN_W // 2, 140), bold=True)
        pygame.draw.line(surf, config.GOLD, (SCREEN_W // 2 - 260, 196), (SCREEN_W // 2 + 260, 196), 3)
        self.group.draw(surf, text)

        surf.blit(self.small_logo, (24, 20))
        if config.GROUP_NAME:
            text.draw(surf, config.GROUP_NAME, 24, config.WHITE, (SCREEN_W // 2, 690))
