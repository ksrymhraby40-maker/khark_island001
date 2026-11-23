"""
صفحهٔ اصلی بازی: پدافند، هواپیماها، مخزن‌ها، زمان‌سنج و منوی سه‌نقطه.

قوانین بازی در logic.World است؛ این فایل فقط ورودی بازیکن را به World می‌دهد و
رویدادهای آن (شلیک، انفجار، آسیب مخزن، ...) را به صدا و جلوه‌های تصویری تبدیل می‌کند.
"""

import math
import random

import pygame

from .. import config, logic
from ..config import HUD_HEIGHT, SCREEN_H, SCREEN_W
from ..effects import Effects
from ..graphics import (dim_overlay, draw_rotated, draw_tank, draw_tank_icon,
                        draw_turret, muzzle_position)
from ..persian import fa_number, format_time
from ..ui import Button, ButtonGroup
from .base import Scene

END_DELAY_WON = 1.4        # مکث بعد از برد/باخت تا انفجارها دیده شوند (ثانیه)
END_DELAY_LOST = 2.2
DOTS_RECT = pygame.Rect(18, 12, 62, 46)       # دکمهٔ سه‌نقطه (بالا، سمت چپ)


class FloatingText:
    """نوشتهٔ کوتاهی که بالا می‌رود و محو می‌شود (مثل «مخزن ۲ آسیب دید»)."""

    def __init__(self, text: str, x: float, y: float, color, key=None) -> None:
        self.text, self.x, self.y, self.color, self.key = text, x, y, color, key
        self.age, self.life = 0.0, 1.9


class PlayScene(Scene):
    def __init__(self, app, level) -> None:
        super().__init__(app)
        self.level = level
        self.rng = random.Random()
        self.world = logic.World(level, self.rng)
        self.fx = Effects(self.rng)
        self.texts = []
        self.t = 0.0
        self.paused = False
        self.menu_open = False
        self.end_timer = None            # بعد از برد/باخت شروع به شمارش می‌کند
        self.finished = False            # بعد از رفتن به صفحهٔ نتیجه true می‌شود
        self.frame = None                # آخرین تصویر رسم‌شده (پس‌زمینهٔ صفحهٔ نتیجه)
        self.hint_seconds = 7.0          # راهنمای کوتاه ابتدای مرحله
        self.pointer = (SCREEN_W // 2, SCREEN_H // 2)
        self.since_pointer = 99.0
        self._smoke_timer = 0.0
        self.plane_flash = {}            # هواپیمایی که تازه ضربه خورده: id ← زمان باقی‌مانده
        self._masks = {}                 # تصویر سفید هر نوع هواپیما برای جلوهٔ ضربه

        self.menu_buttons = [
            Button((26, 76, 284, 58), "توقف بازی", self.pause, 30),
            Button((26, 142, 284, 58), "ادامه بازی", self.resume, 30),
            Button((26, 208, 284, 58), "بازگشت به منو", self.to_menu, 30),
        ]
        self.menu = ButtonGroup(self.menu_buttons, play_click=lambda: app.sounds.play("click"))
        self._sync_menu_buttons()

    def on_enter(self) -> None:
        self.app.sounds.play_music("battle", config.MUSIC_VOLUME_BATTLE)

    # ------------------------------------------------------------ دکمه‌های منو
    def _sync_menu_buttons(self) -> None:
        self.menu_buttons[0].enabled = not self.paused      # توقف: فقط وقتی بازی در جریان است
        self.menu_buttons[1].enabled = self.paused          # ادامه: فقط وقتی متوقف شده است

    def pause(self) -> None:
        self.paused = True
        self.app.sounds.pause_music()
        self._sync_menu_buttons()

    def resume(self) -> None:
        self.paused = False
        self.menu_open = False
        self.app.sounds.resume_music()
        self._sync_menu_buttons()

    def to_menu(self) -> None:
        from .menu import MenuScene
        self.app.change_scene(MenuScene(self.app))

    # ------------------------------------------------------------ ورودی
    def on_press(self, pos) -> None:
        self.pointer = pos
        self.since_pointer = 0.0
        if self.end_timer is not None:
            return
        if DOTS_RECT.collidepoint(pos):
            self.menu_open = not self.menu_open
            self.app.sounds.play("click")
            return
        if self.menu_open:
            if any(b.hit(pos) for b in self.menu_buttons):
                self.menu.press(pos)
            else:
                self.menu_open = False                      # کلیک بیرون از فهرست، آن را می‌بندد
            return
        if self.paused or pos[1] < HUD_HEIGHT:
            return
        self.world.fire(pos[0], pos[1])

    def on_release(self, pos) -> None:
        if self.menu_open:
            self.menu.release(pos)

    def on_move(self, pos) -> None:
        self.pointer = pos
        self.since_pointer = 0.0
        self.menu.move(pos)

    def on_back(self) -> None:
        if self.end_timer is None:
            self.menu_open = not self.menu_open

    # ------------------------------------------------------------ به‌روزرسانی
    def update(self, dt: float) -> None:
        if self.paused:
            return
        self.t += dt
        self.since_pointer += dt
        self.world.update(dt)
        self._handle_events()
        self._emit_trails(dt)
        self.fx.update(dt)

        for key in list(self.plane_flash):
            self.plane_flash[key] -= dt
            if self.plane_flash[key] <= 0:
                del self.plane_flash[key]
        for item in self.texts:
            item.age += dt
            item.y -= 26 * dt
        self.texts = [i for i in self.texts if i.age < i.life]

        if self.end_timer is not None and not self.finished:
            self.end_timer -= dt
            if self.end_timer <= 0:
                self.finished = True
                self._finish()

    def _handle_events(self) -> None:
        sounds = self.app.sounds
        for ev in self.world.pop_events():
            if ev.name == "shot":
                angle = math.atan2(ev.y - config.TURRET_PIVOT_Y, ev.x - config.TURRET_X)
                mx, my = muzzle_position(angle)
                self.fx.tracer(mx, my, ev.x, ev.y)
                sounds.play("shot", 0.55)
            elif ev.name == "miss":
                self.fx.hit_sparks(ev.x, ev.y)
            elif ev.name == "plane_hit":
                self.fx.hit_sparks(ev.x, ev.y)
                self.plane_flash[id(ev.data)] = 0.12
                sounds.play("hit", 0.6)
            elif ev.name == "plane_down":
                self.fx.plane_explosion(ev.x, ev.y)
                sounds.play("boom", 0.4)
            elif ev.name == "bomb_drop":
                sounds.play("whistle", 0.35)
            elif ev.name == "bomb_hit":
                tank = ev.data
                number = fa_number(tank.index + 1)
                if tank.destroyed:
                    self.fx.explode(ev.x, ev.y, size=120, sparks=34, shake=14)
                    sounds.play("boom", 1.0)
                    label, color = f"مخزن {number} نابود شد", config.RED
                else:
                    self.fx.explode(ev.x, ev.y, size=78, sparks=22, shake=8)
                    sounds.play("boom", 0.8)
                    label, color = f"مخزن {number} آسیب دید", config.ORANGE
                self.texts = [i for i in self.texts if i.key != tank.index]      # پیام تازه جای قبلی را می‌گیرد
                self.texts.append(FloatingText(label, tank.x, tank.y - 128 - (tank.index % 2) * 30,
                                               color, key=tank.index))
            elif ev.name == "game_won":
                self.end_timer = END_DELAY_WON
                sounds.play("win")
            elif ev.name == "game_lost":
                self.end_timer = END_DELAY_LOST
                sounds.play("lose")

    def _emit_trails(self, dt: float) -> None:
        """دود پشت هواپیمای آسیب‌دیده و رد بمب‌های در حال سقوط."""
        self._smoke_timer -= dt
        if self._smoke_timer > 0:
            return
        self._smoke_timer = 0.06
        for plane in self.world.planes:
            if plane.hp < plane.kind.hp:
                self.fx.add_smoke(plane.x - plane.kind.width / 2 + 8, plane.y, size=9,
                                  dark=True, life=1.0, vy=-10)
        for bomb in self.world.bombs:
            self.fx.add_smoke(bomb.x - 8 * math.cos(bomb.angle), bomb.y - 8 * math.sin(bomb.angle),
                              size=5, dark=False, life=0.5, vy=0)

    def _finish(self) -> None:
        from .result import ResultScene
        self.app.change_scene(ResultScene(self.app, self.level, self.world,
                                          self.world.state == logic.WON, self.frame))

    # ------------------------------------------------------------ رسم
    def draw(self, surf) -> None:
        world, text = self.world, self.app.text
        backdrop = self.app.backdrop
        t = self.t
        backdrop.draw_back(surf, t)
        backdrop.draw_island(surf)

        for tank in world.tanks:
            draw_tank(surf, tank.x, tank.y, tank.state, t)
            text.draw(surf, fa_number(tank.index + 1), 20, (70, 56, 34), (tank.x, 606),
                      bold=True, shadow=False)

        for plane in world.planes:
            self._draw_plane(surf, plane)
        draw_turret(surf, self.app.sprites, world.turret_angle, world.since_shot < 0.07)
        for bomb in world.bombs:
            draw_rotated(surf, self.app.sprites.bomb, bomb.x, bomb.y, bomb.angle)

        self.fx.draw(surf)
        for item in self.texts:
            alpha_k = min(1.0, (item.life - item.age) / 0.6)
            color = tuple(int(c * alpha_k) for c in item.color)
            text.draw(surf, item.text, 26, color, (item.x, item.y), bold=True)

        self._draw_hud(surf)
        if self.t < self.hint_seconds and not self.paused:
            self._draw_hint(surf)
        if self.since_pointer < 1.5 and not self.paused and not self.menu_open:
            self._draw_reticle(surf)
        if self.paused:
            dim_overlay(surf, 110, (4, 10, 24))
            text.draw(surf, "بازی متوقف شد", 80, config.WHITE, (SCREEN_W // 2, 330), bold=True)
            text.draw(surf, "برای ادامه، سه‌نقطهٔ بالا را بزنید", 30, (210, 220, 235),
                      (SCREEN_W // 2, 410))
        self._draw_menu(surf)

        # لرزش صفحه هنگام انفجار: تصویر ساخته‌شده کمی جابه‌جا می‌شود
        dx, dy = self.fx.shake_offset()
        if dx or dy:
            copy = surf.copy()
            surf.fill((0, 0, 0))
            surf.blit(copy, (dx, dy))
        self.frame = surf       # آخرین تصویر؛ پس‌زمینهٔ صفحهٔ نتیجه

    def _plane_mask(self, plane):
        key = plane.kind.key
        if key not in self._masks:
            sprite = self.app.sprites.planes[key]
            mask = pygame.mask.from_surface(sprite)
            self._masks[key] = mask.to_surface(setcolor=(255, 255, 255, 200), unsetcolor=(0, 0, 0, 0))
        return self._masks[key]

    def _draw_plane(self, surf, plane) -> None:
        sprite = self.app.sprites.planes[plane.kind.key]
        rect = sprite.get_rect(center=(int(plane.x), int(plane.y)))
        surf.blit(sprite, rect)
        if id(plane) in self.plane_flash:
            surf.blit(self._plane_mask(plane), rect)

    def _draw_hud(self, surf) -> None:
        world, text = self.world, self.app.text
        bar = pygame.Surface((SCREEN_W, HUD_HEIGHT), pygame.SRCALPHA)
        bar.fill((6, 16, 32, 175))
        surf.blit(bar, (0, 0))
        pygame.draw.line(surf, config.GOLD, (0, HUD_HEIGHT), (SCREEN_W, HUD_HEIGHT), 2)

        # زمان‌سنج وسط صفحه
        urgent = world.time_left <= 10 and world.state == logic.PLAYING
        color = config.RED if urgent and int(self.t * 3) % 2 == 0 else config.WHITE
        pill = pygame.Rect(0, 0, 190, 54)
        pill.center = (SCREEN_W // 2, 35)
        pygame.draw.rect(surf, (10, 22, 40), pill, border_radius=16)
        pygame.draw.rect(surf, config.GOLD, pill, 2, border_radius=16)
        text.draw(surf, format_time(world.time_left), 42, color, pill.center, bold=True, shadow=False)

        # دکمهٔ سه‌نقطه
        hover = DOTS_RECT.collidepoint(self.pointer)
        pygame.draw.rect(surf, (34, 70, 112) if hover or self.menu_open else (18, 38, 66),
                         DOTS_RECT, border_radius=12)
        pygame.draw.rect(surf, config.GOLD, DOTS_RECT, 2, border_radius=12)
        for i in range(3):
            pygame.draw.circle(surf, config.WHITE, (DOTS_RECT.centerx, DOTS_RECT.y + 11 + i * 12), 4)

        # تعداد هواپیماهای سرنگون‌شده
        text.draw(surf, f"سرنگون‌شده: {fa_number(world.downed)}", 24, config.WHITE, (100, 35),
                  anchor="midleft", shadow=False)

        # وضعیت شش مخزن (سبز سالم، نارنجی آسیب‌دیده، قرمز نابود)
        for tank in world.tanks:
            draw_tank_icon(surf, 935 + tank.index * 42, 36, tank.state)
        text.draw(surf, "مخازن", 24, config.WHITE, (SCREEN_W - 20, 35), anchor="midright", shadow=False)

    def _draw_hint(self, surf) -> None:
        """راهنمای کوتاه ابتدای مرحله؛ در آسمان نمایش داده می‌شود چون در ثانیه‌های اول هواپیمای کمی هست."""
        pill = pygame.Surface((720, 104), pygame.SRCALPHA)
        pygame.draw.rect(pill, (6, 16, 32, 190), pill.get_rect(), border_radius=20)
        pygame.draw.rect(pill, config.GOLD, pill.get_rect(), 2, border_radius=20)
        surf.blit(pill, (SCREEN_W // 2 - 360, 214))
        self.app.text.draw(surf, "روی هواپیماها بزنید تا سرنگون شوند\nهر مخزن با دو بمب نابود می‌شود",
                           28, config.WHITE, (SCREEN_W // 2, 266), shadow=False)

    def _draw_menu(self, surf) -> None:
        if not self.menu_open:
            return
        panel = pygame.Surface((304, 206), pygame.SRCALPHA)
        pygame.draw.rect(panel, (6, 14, 28, 235), panel.get_rect(), border_radius=18)
        pygame.draw.rect(panel, config.GOLD, panel.get_rect(), 3, border_radius=18)
        surf.blit(panel, (16, 68))
        self.menu.draw(surf, self.app.text)

    def _draw_reticle(self, surf) -> None:
        x, y = self.pointer
        if y < HUD_HEIGHT:
            return
        pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), 22, 2)
        pygame.draw.circle(surf, config.RED, (int(x), int(y)), 3)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(surf, (255, 255, 255), (x + dx * 14, y + dy * 14), (x + dx * 30, y + dy * 30), 2)
