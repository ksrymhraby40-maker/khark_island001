"""انتخاب مرحله: نقشهٔ دو‌بعدی جزیرهٔ خارک با خط دفاعی که مرحله‌ها روی آن قرار دارند."""

import math

import pygame

from .. import config
from ..config import SCREEN_W
from ..graphics import alpha_circle, lerp_color
from ..persian import fa_number
from ..ui import Button, ButtonGroup
from .base import Scene

# نقطه‌های خط دفاعی روی نقشه (مختصات صفحه)
DEFENSE_LINE = [(80, 470), (250, 424), (430, 440), (610, 396), (790, 412), (960, 362), (1200, 330)]
# جای دایرهٔ هر مرحله (به‌ترتیب شمارهٔ مرحله)
LEVEL_NODES = [(430, 440), (960, 362)]
NODE_RADIUS = 46


def _walk_polyline(points, step):
    """از روی چندخطی هر step پیکسل یک نقطه همراه با جهت حرکت می‌دهد."""
    carry = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        d = step - carry
        while d <= length:
            yield x0 + ux * d, y0 + uy * d, ux, uy
            d += step
        carry = length - (d - step)


class LevelSelectScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.t = 0.0
        self.pointer = (-1, -1)
        self.pressed_node = None
        self.back = ButtonGroup([Button((500, 628, 280, 66), "بازگشت", self.go_back, 32)],
                                play_click=lambda: app.sounds.play("click"))

    def on_enter(self) -> None:
        self.app.sounds.play_music("theme", config.MUSIC_VOLUME_MENU)

    # ---- کارها
    def go_back(self) -> None:
        from .menu import MenuScene
        self.app.change_scene(MenuScene(self.app))

    def start_level(self, index: int) -> None:
        from .intro import IntroScene
        self.app.sounds.play("click")
        self.app.change_scene(IntroScene(self.app, config.LEVELS[index]))

    def _node_at(self, pos):
        for i, (x, y) in enumerate(LEVEL_NODES):
            if math.hypot(pos[0] - x, pos[1] - y) <= NODE_RADIUS + 8:
                return i
        return None

    # ---- رویدادها
    def on_press(self, pos) -> None:
        self.pointer = pos
        self.pressed_node = self._node_at(pos)
        self.back.press(pos)

    def on_release(self, pos) -> None:
        node, self.pressed_node = self.pressed_node, None
        if node is not None and self._node_at(pos) == node:
            self.start_level(node)
        self.back.release(pos)

    def on_move(self, pos) -> None:
        self.pointer = pos
        self.back.move(pos)

    def on_back(self) -> None:
        self.go_back()

    def update(self, dt: float) -> None:
        self.t += dt

    # ---- رسم
    def draw(self, surf) -> None:
        text = self.app.text
        surf.blit(self.app.map_bg, (0, 0))
        self._draw_defense_line(surf)
        for i, (x, y) in enumerate(LEVEL_NODES):
            self._draw_node(surf, i, x, y)

        banner = pygame.Surface((760, 84), pygame.SRCALPHA)
        pygame.draw.rect(banner, (0, 0, 0, 130), banner.get_rect(), border_radius=20)
        surf.blit(banner, (SCREEN_W // 2 - 380, 28))
        text.draw(surf, "مرحله را انتخاب کنید", 52, config.WHITE, (SCREEN_W // 2, 70), bold=True)
        self.back.draw(surf, text)

    def _draw_defense_line(self, surf) -> None:
        # خط چین
        carry_on = True
        for x, y, ux, uy in _walk_polyline(DEFENSE_LINE, 30):
            if carry_on:
                pygame.draw.line(surf, (250, 96, 72), (x - ux * 9, y - uy * 9), (x + ux * 9, y + uy * 9), 6)
            carry_on = not carry_on
        # مثلث‌های سنگر روی خط (نماد متداول خط مقدم روی نقشه)
        for x, y, ux, uy in _walk_polyline(DEFENSE_LINE, 74):
            nx, ny = uy, -ux                                    # عمود رو به بالا
            if ny > 0:
                nx, ny = -nx, -ny
            tip = (x + nx * 20, y + ny * 20)
            pygame.draw.polygon(surf, (250, 96, 72), [(x - ux * 11, y - uy * 11), (x + ux * 11, y + uy * 11), tip])
            pygame.draw.polygon(surf, (120, 30, 24), [(x - ux * 11, y - uy * 11), (x + ux * 11, y + uy * 11), tip], 2)

    def _draw_node(self, surf, index: int, x: int, y: int) -> None:
        text = self.app.text
        hover = self._node_at(self.pointer) == index
        pressed = self.pressed_node == index
        radius = NODE_RADIUS + (4 if hover else 0) - (3 if pressed else 0)

        # حلقهٔ نبض‌دار برای جلب توجه
        k = (self.t * 0.9 + index * 0.4) % 1.0
        ring = lerp_color(config.GOLD, (10, 70, 100), k)
        pygame.draw.circle(surf, ring, (x, y), int(NODE_RADIUS + 6 + 22 * k), 3)

        alpha_circle(surf, (0, 0, 0, 110), (x + 3, y + 6), radius)
        pygame.draw.circle(surf, (18, 38, 66) if not hover else (34, 70, 112), (x, y), radius)
        pygame.draw.circle(surf, config.GOLD, (x, y), radius, 4)
        text.draw(surf, fa_number(config.LEVELS[index].number), 56, config.WHITE, (x, y - 2), bold=True)

        label = config.LEVELS[index].name
        w = text.width(label, 28, True) + 40
        pill = pygame.Rect(0, 0, w, 44)
        pill.center = (x, y + radius + 40)
        pygame.draw.rect(surf, (10, 22, 40), pill, border_radius=14)
        pygame.draw.rect(surf, config.GOLD, pill, 2, border_radius=14)
        text.draw(surf, label, 28, config.WHITE, pill.center, bold=True, shadow=False)
