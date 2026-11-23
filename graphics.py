"""
گرافیک بازی
------------
همهٔ تصویرها (جزیره، مخزن‌ها، هواپیماها، پدافند، آرم) با دستورهای رسم pygame کشیده
می‌شوند و عکس آماده‌ای وجود ندارد. تصویرهای ثابت یک‌بار ساخته و نگه داشته می‌شوند
(کلاس‌های Backdrop و Sprites) تا بازی روان بماند.
"""

import math
import os
import random
from typing import List, Tuple

import pygame

from . import config
from .config import SCREEN_H, SCREEN_W

Color = Tuple[int, int, int]

# ---------------------------------------------------------------- رنگ‌ها
SKY_TOP = (36, 96, 168)
SKY_BOTTOM = (190, 224, 245)
SEA_TOP = (24, 128, 166)
SEA_BOTTOM = (6, 52, 94)
SAND = (214, 192, 138)
SAND_EDGE = (170, 146, 100)
HORIZON_Y = 470


# ---------------------------------------------------------------- ابزارهای کوچک
def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1, c2, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def vertical_gradient(width: int, height: int, top: Color, bottom: Color) -> "pygame.Surface":
    surf = pygame.Surface((width, height))
    for y in range(height):
        pygame.draw.line(surf, lerp_color(top, bottom, y / max(1, height - 1)), (0, y), (width, y))
    return surf


def alpha_circle(surf: "pygame.Surface", color, center, radius: float) -> None:
    """دایرهٔ نیمه‌شفاف (pygame روی صفحهٔ اصلی خودش شفافیت را اعمال نمی‌کند، پس از یک لایه استفاده می‌کنیم)."""
    r = max(1, int(radius))
    a = max(0, min(255, int(color[3])))
    if a == 0:
        return
    layer = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(layer, (color[0], color[1], color[2], a), (r, r), r)
    surf.blit(layer, (int(center[0]) - r, int(center[1]) - r))


def dim_overlay(surf: "pygame.Surface", alpha: int, color=(0, 0, 0)) -> None:
    """روی کل صفحه یک لایهٔ تیره/رنگی نیمه‌شفاف می‌کشد."""
    if alpha <= 0:
        return
    layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    layer.fill((color[0], color[1], color[2], min(255, int(alpha))))
    surf.blit(layer, (0, 0))


# ---------------------------------------------------------------- جزیرهٔ خارک (شکل ساده‌شدهٔ دو‌بعدی)
ISLAND_BASE: List[Tuple[int, int]] = [
    (196, 640), (246, 588), (326, 548), (448, 528), (562, 520), (700, 524),
    (830, 520), (942, 536), (1032, 566), (1086, 612), (1040, 656), (900, 674),
    (700, 682), (500, 678), (320, 672), (228, 664),
]
# پوشش گیاهی: (مرکز x، مرکز y، شعاع افقی، شعاع عمودی)
VEGETATION = [(300, 612, 44, 16), (980, 600, 52, 18), (520, 650, 70, 14),
              (800, 656, 64, 14), (380, 650, 40, 12), (1030, 628, 30, 12)]


def _centroid(points) -> Tuple[float, float]:
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


_BASE_CX, _BASE_CY = _centroid(ISLAND_BASE)


def island_transform(point, scale: float, cx: float, cy: float,
                     stretch_y: float = 1.0) -> Tuple[float, float]:
    """نقطه‌ای از جزیرهٔ پایه را با بزرگ‌نمایی دور مرکز به مرکز تازهٔ (cx, cy) می‌برد.
    stretch_y محور عمودی را اضافه‌تر می‌کشد (برای نقشه که جزیره پرتر دیده شود)."""
    return (cx + (point[0] - _BASE_CX) * scale,
            cy + (point[1] - _BASE_CY) * scale * stretch_y)


def island_points(scale: float = 1.0, cx: float = _BASE_CX, cy: float = _BASE_CY,
                  stretch_y: float = 1.0):
    return [island_transform(p, scale, cx, cy, stretch_y) for p in ISLAND_BASE]


def draw_island(layer: "pygame.Surface", scale: float, cx: float, cy: float,
                details: bool = True, stretch_y: float = 1.0) -> None:
    """جزیره را با ساحل کم‌عمق و پوشش گیاهی روی یک لایهٔ شفاف می‌کشد."""
    pygame.draw.polygon(layer, (96, 200, 210, 110), island_points(scale * 1.10, cx, cy, stretch_y))
    pygame.draw.polygon(layer, (146, 224, 226, 170), island_points(scale * 1.045, cx, cy, stretch_y))
    pts = island_points(scale, cx, cy, stretch_y)
    pygame.draw.polygon(layer, SAND, pts)
    pygame.draw.polygon(layer, SAND_EDGE, pts, max(2, int(4 * scale)))
    if details:
        for vx, vy, rx, ry in VEGETATION:
            x, y = island_transform((vx, vy), scale, cx, cy, stretch_y)
            rx, ry = rx * scale, ry * scale * stretch_y
            pygame.draw.ellipse(layer, (108, 152, 86), (x - rx, y - ry, rx * 2, ry * 2))
            pygame.draw.ellipse(layer, (84, 126, 70), (x - rx * 0.6, y - ry * 0.5, rx * 1.2, ry))


# ---------------------------------------------------------------- پس‌زمینهٔ بازی
class Backdrop:
    """
    پس‌زمینه: آسمان و دریا (ثابت، از قبل ساخته‌شده)، موج‌ها و ابرها (متحرک) و جزیره (ثابت).
    """

    def __init__(self, text) -> None:
        rng = random.Random(7)
        self.sky_sea = self._build_sky_sea(text)
        self.island = self._build_island()
        self.cloud_sprites = [self._make_cloud(rng) for _ in range(3)]
        # هر ابر: [x، y، شمارهٔ شکل، سرعت]
        self.clouds = [[rng.uniform(0, SCREEN_W), rng.uniform(46, 300),
                        rng.randrange(3), rng.uniform(6, 20)] for _ in range(7)]
        # هر موج: (x، y، طول، سرعت)
        self.waves = [(rng.uniform(0, SCREEN_W), rng.uniform(HORIZON_Y + 12, SCREEN_H - 4),
                       rng.uniform(16, 52), rng.uniform(6, 18)) for _ in range(70)]

    # ---- ساخت لایه‌های ثابت
    @staticmethod
    def _build_sky_sea(text) -> "pygame.Surface":
        surf = pygame.Surface((SCREEN_W, SCREEN_H))
        surf.blit(vertical_gradient(SCREEN_W, HORIZON_Y, SKY_TOP, SKY_BOTTOM), (0, 0))
        surf.blit(vertical_gradient(SCREEN_W, SCREEN_H - HORIZON_Y, SEA_TOP, SEA_BOTTOM), (0, HORIZON_Y))
        # خورشید با هالهٔ نرم
        for radius, alpha in ((120, 26), (84, 40), (56, 70), (36, 200)):
            alpha_circle(surf, (255, 244, 200, alpha), (1030, 150), radius)
        # بازتاب خورشید روی دریا
        for i in range(9):
            w = 150 - i * 12
            pygame.draw.line(surf, (150, 205, 220), (1030 - w // 2, HORIZON_Y + 10 + i * 12),
                             (1030 + w // 2, HORIZON_Y + 10 + i * 12), 2)
        pygame.draw.line(surf, (220, 240, 250), (0, HORIZON_Y), (SCREEN_W, HORIZON_Y), 2)
        text.draw(surf, "خلیج فارس", 34, (74, 156, 192), (118, 690), anchor="center",
                  bold=True, shadow=False)
        return surf

    @staticmethod
    def _build_island() -> "pygame.Surface":
        layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        draw_island(layer, 1.0, _BASE_CX, _BASE_CY)
        # لولهٔ نفت بین مخزن‌ها
        y = config.TANK_Y + 9
        pygame.draw.line(layer, (92, 96, 104), (config.TANK_XS[0] - 40, y), (config.TANK_XS[-1] + 40, y), 8)
        pygame.draw.line(layer, (150, 156, 166), (config.TANK_XS[0] - 40, y - 2), (config.TANK_XS[-1] + 40, y - 2), 2)
        for x in config.TANK_XS:
            pygame.draw.rect(layer, (120, 40, 34), (x - 7, y - 8, 14, 16), border_radius=3)
        # اسکله و کشتی نفت‌کش
        pygame.draw.rect(layer, (126, 94, 62), (52, 636, 190, 11))
        for x in range(60, 240, 30):
            pygame.draw.rect(layer, (84, 60, 40), (x, 646, 6, 18))
        hull = [(1062, 648), (1214, 648), (1190, 676), (1086, 676)]
        pygame.draw.polygon(layer, (64, 66, 78), hull)
        pygame.draw.polygon(layer, (170, 50, 44), [(1066, 654), (1210, 654), (1206, 660), (1070, 660)])
        pygame.draw.rect(layer, (232, 234, 238), (1160, 622, 34, 26))
        pygame.draw.rect(layer, (60, 140, 190), (1166, 628, 22, 8))
        pygame.draw.rect(layer, (200, 60, 50), (1100, 632, 18, 16))
        for x in (1124, 1138):
            pygame.draw.ellipse(layer, (210, 214, 220), (x - 9, 636, 18, 14))
        return layer

    @staticmethod
    def _make_cloud(rng: random.Random) -> "pygame.Surface":
        w, h = 240, 96
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(6):
            cw, ch = rng.uniform(70, 120), rng.uniform(34, 52)
            x, y = rng.uniform(10, w - cw - 10), rng.uniform(26, h - ch - 6)
            pygame.draw.ellipse(surf, (255, 255, 255, 215), (x, y, cw, ch))
        pygame.draw.ellipse(surf, (255, 255, 255, 215), (30, 52, 180, 34))
        return surf

    # ---- رسم هر فریم
    def draw_back(self, surf: "pygame.Surface", t: float) -> None:
        """آسمان، ابرها و موج‌ها (زیر جزیره)."""
        surf.blit(self.sky_sea, (0, 0))
        for x, y, shape, speed in self.clouds:
            cx = (x + t * speed) % (SCREEN_W + 260) - 250
            surf.blit(self.cloud_sprites[shape], (cx, y))
        for x, y, length, speed in self.waves:
            wx = (x + t * speed) % (SCREEN_W + length) - length
            wy = y + math.sin(t * 1.4 + x) * 1.5
            pygame.draw.line(surf, (112, 190, 214), (wx, wy), (wx + length, wy), 2)

    def draw_island(self, surf: "pygame.Surface") -> None:
        surf.blit(self.island, (0, 0))


# بزرگ‌نمایی، مرکز و کشیدگی جزیره در نقشه (برای جاگذاری مرحله‌ها و موشک هم استفاده می‌شود)
MAP_ISLAND = dict(scale=1.2, cx=640, cy=392, stretch_y=2.0)


def map_point(x: float, y: float) -> Tuple[float, float]:
    """نقطه‌ای از مختصات جزیرهٔ پایه را به مختصات نقشه برمی‌گرداند."""
    return island_transform((x, y), MAP_ISLAND["scale"], MAP_ISLAND["cx"],
                            MAP_ISLAND["cy"], MAP_ISLAND["stretch_y"])


def build_map_background(text) -> "pygame.Surface":
    """نقشهٔ دو‌بعدی جزیره (برای صفحهٔ انتخاب مرحله و اسلایدهای معرفی)."""
    surf = vertical_gradient(SCREEN_W, SCREEN_H, (8, 40, 68), (10, 72, 98))
    for x in range(0, SCREEN_W, 80):
        pygame.draw.line(surf, (20, 86, 114), (x, 0), (x, SCREEN_H), 1)
    for y in range(0, SCREEN_H, 80):
        pygame.draw.line(surf, (20, 86, 114), (0, y), (SCREEN_W, y), 1)
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    draw_island(layer, **MAP_ISLAND)
    surf.blit(layer, (0, 0))
    text.draw(surf, "خلیج فارس", 40, (52, 130, 168), (180, 672), bold=True, shadow=False)
    return surf




# ---------------------------------------------------------------- مخزن نفت
def draw_tank(surf: "pygame.Surface", x: float, base_y: float, state: int, t: float) -> None:
    """مخزن نفت؛ state: ۰ سالم، ۱ آسیب‌دیده، ۲ نابودشده."""
    w, h = 72, 54
    left = x - w / 2
    pygame.draw.ellipse(surf, (150, 128, 92), (left - 8, base_y - 9, w + 16, 20))   # سایه

    if state >= 2:                                                                   # نابود شده
        pygame.draw.polygon(surf, (52, 46, 46), [(left, base_y), (left, base_y - 20), (left + 12, base_y - 30),
                                                 (left + 24, base_y - 20), (left + 38, base_y - 34),
                                                 (left + 52, base_y - 22), (left + w, base_y - 28), (left + w, base_y)])
        pygame.draw.ellipse(surf, (30, 26, 26), (left, base_y - 12, w, 24))
        pygame.draw.ellipse(surf, (22, 18, 18), (left + 6, base_y - 38, w - 12, 18))
        glow = 150 + int(70 * math.sin(t * 9 + x))
        pygame.draw.ellipse(surf, (glow, 60, 18), (left + 14, base_y - 34, w - 28, 10))
        _flame(surf, x - 10, base_y - 32, 16, t, x)
        _flame(surf, x + 14, base_y - 30, 12, t + 1.3, x)
        return

    damaged = state == 1
    body = (196, 184, 170) if damaged else (232, 235, 240)
    shade = (150, 140, 128) if damaged else (186, 192, 204)
    pygame.draw.rect(surf, body, (left, base_y - h, w, h))
    pygame.draw.rect(surf, shade, (left + w * 0.66, base_y - h, w * 0.34, h))
    pygame.draw.rect(surf, (255, 255, 255) if not damaged else (214, 204, 190), (left + 6, base_y - h, 8, h))
    pygame.draw.rect(surf, (150, 46, 40) if damaged else (210, 58, 50), (left, base_y - h * 0.55, w, 9))
    pygame.draw.ellipse(surf, shade, (left, base_y - 12, w, 24))
    pygame.draw.ellipse(surf, body, (left, base_y - 12, w, 22))
    pygame.draw.ellipse(surf, (206, 210, 218) if not damaged else (170, 160, 148), (left, base_y - h - 12, w, 24))
    pygame.draw.ellipse(surf, (120, 126, 138), (left, base_y - h - 12, w, 24), 2)
    pygame.draw.ellipse(surf, (110, 114, 124), (x - 8, base_y - h - 5, 16, 9))
    if damaged:
        pygame.draw.polygon(surf, (40, 36, 36), [(x + 4, base_y - h - 10), (x + 30, base_y - h - 6),
                                                 (x + 34, base_y - h + 18), (x + 16, base_y - h + 10)])
        pygame.draw.lines(surf, (60, 54, 52), False, [(x - 20, base_y - h), (x - 12, base_y - h + 16),
                                                      (x - 22, base_y - h + 28), (x - 14, base_y - h + 42)], 3)
        pygame.draw.lines(surf, (60, 54, 52), False, [(x + 8, base_y - h + 24), (x + 18, base_y - h + 34),
                                                      (x + 10, base_y - h + 46)], 2)
        _flame(surf, x + 18, base_y - h - 4, 14, t, x)


def _flame(surf, x: float, y: float, height: float, t: float, seed: float) -> None:
    """شعلهٔ سوسوزن (دو مثلث تودرتو)."""
    flick = 0.75 + 0.25 * math.sin(t * 14 + seed)
    h = height * flick
    pygame.draw.polygon(surf, (240, 110, 30), [(x - height * 0.45, y), (x, y - h * 1.5), (x + height * 0.45, y)])
    pygame.draw.polygon(surf, (255, 214, 80), [(x - height * 0.22, y), (x, y - h * 0.9), (x + height * 0.22, y)])


def draw_tank_icon(surf: "pygame.Surface", cx: float, cy: float, state: int) -> None:
    """مخزن کوچک برای نوار وضعیت بالای صفحه؛ رنگ آن حالت مخزن را نشان می‌دهد."""
    color = (config.GREEN, config.ORANGE, config.RED)[min(state, 2)]
    dark = lerp_color(color, (0, 0, 0), 0.45)
    w, h = 28, 24
    if state >= 2:
        h = 12
    pygame.draw.rect(surf, color, (cx - w / 2, cy - h / 2 + 4, w, h))
    pygame.draw.ellipse(surf, dark, (cx - w / 2, cy + h / 2 - 3, w, 10))
    pygame.draw.ellipse(surf, color, (cx - w / 2, cy - h / 2 - 2, w, 12))
    pygame.draw.ellipse(surf, dark, (cx - w / 2, cy - h / 2 - 2, w, 12), 2)
    if state == 1:
        pygame.draw.line(surf, dark, (cx - 6, cy - 6), (cx + 4, cy + 8), 2)
    if state >= 2:
        pygame.draw.line(surf, (255, 255, 255), (cx - 9, cy - 6), (cx + 9, cy + 10), 3)
        pygame.draw.line(surf, (255, 255, 255), (cx + 9, cy - 6), (cx - 9, cy + 10), 3)


# ---------------------------------------------------------------- هواپیماها
def _make_f16() -> "pygame.Surface":
    k = config.F16
    s = pygame.Surface((k.width, k.height), pygame.SRCALPHA)
    cy = 23
    body, dark, line = (156, 166, 178), (100, 110, 122), (52, 60, 70)
    pygame.draw.polygon(s, dark, [(8, cy - 2), (20, 3), (36, 3), (44, cy - 2)])               # دم عمودی
    pygame.draw.polygon(s, dark, [(4, cy + 1), (24, cy + 1), (14, cy + 9)])                   # دم افقی
    fus = [(2, cy), (10, cy - 4), (58, cy - 7), (92, cy - 5), (k.width - 2, cy + 1),
           (92, cy + 4), (58, cy + 6), (10, cy + 4)]
    pygame.draw.polygon(s, body, fus)
    pygame.draw.polygon(s, line, fus, 1)
    wing = [(46, cy + 2), (80, cy + 2), (58, k.height - 2), (34, k.height - 2)]
    pygame.draw.polygon(s, dark, wing)
    pygame.draw.polygon(s, line, wing, 1)
    pygame.draw.polygon(s, (90, 192, 232), [(74, cy - 6), (82, cy - 12), (92, cy - 9), (96, cy - 4)])  # کابین
    pygame.draw.polygon(s, line, [(74, cy - 6), (82, cy - 12), (92, cy - 9), (96, cy - 4)], 1)
    pygame.draw.ellipse(s, (255, 150, 40), (0, cy - 4, 8, 8))                                 # موتور
    pygame.draw.ellipse(s, (255, 230, 120), (2, cy - 2, 4, 4))
    pygame.draw.line(s, (206, 70, 60), (62, cy - 1), (78, cy - 1), 2)                         # نوار رنگی
    return s


def _make_f35() -> "pygame.Surface":
    k = config.F35
    s = pygame.Surface((k.width, k.height), pygame.SRCALPHA)
    cy = 26
    body, dark, line = (96, 106, 118), (62, 70, 82), (30, 36, 44)
    pygame.draw.polygon(s, dark, [(14, cy - 2), (22, 4), (36, 4), (40, cy - 2)])              # دم‌های کج
    pygame.draw.polygon(s, (74, 82, 94), [(22, cy - 2), (30, 8), (44, 8), (48, cy - 2)])
    fus = [(3, cy), (14, cy - 5), (70, cy - 8), (108, cy - 5), (k.width - 2, cy + 1),
           (108, cy + 5), (70, cy + 8), (14, cy + 5)]
    pygame.draw.polygon(s, body, fus)
    pygame.draw.polygon(s, line, fus, 1)
    wing = [(44, cy + 3), (92, cy + 3), (70, k.height - 2), (36, k.height - 2)]
    pygame.draw.polygon(s, dark, wing)
    pygame.draw.polygon(s, line, wing, 1)
    cockpit = [(88, cy - 6), (98, cy - 12), (110, cy - 8), (114, cy - 3)]
    pygame.draw.polygon(s, (50, 62, 78), cockpit)
    pygame.draw.polygon(s, (110, 150, 186), [(94, cy - 8), (100, cy - 11), (106, cy - 8)])
    pygame.draw.polygon(s, line, cockpit, 1)
    pygame.draw.ellipse(s, (255, 140, 40), (0, cy - 4, 9, 8))
    pygame.draw.ellipse(s, (255, 226, 120), (2, cy - 2, 4, 4))
    pygame.draw.line(s, (70, 78, 92), (50, cy), (90, cy), 1)
    return s


def _make_bomb() -> "pygame.Surface":
    s = pygame.Surface((36, 14), pygame.SRCALPHA)
    pygame.draw.polygon(s, (46, 50, 56), [(0, 1), (8, 5), (8, 9), (0, 13)])                   # دُم
    pygame.draw.ellipse(s, (66, 72, 80), (4, 2, 28, 10))
    pygame.draw.ellipse(s, (210, 70, 56), (26, 3, 9, 8))
    pygame.draw.line(s, (120, 130, 142), (10, 4), (24, 4), 1)
    return s


def _make_missile() -> "pygame.Surface":
    s = pygame.Surface((150, 34), pygame.SRCALPHA)
    pygame.draw.polygon(s, (120, 126, 136), [(8, 17), (30, 3), (42, 3), (44, 17)])            # بال بالا
    pygame.draw.polygon(s, (120, 126, 136), [(8, 17), (30, 31), (42, 31), (44, 17)])          # بال پایین
    pygame.draw.rect(s, (214, 216, 222), (20, 9, 92, 16), border_radius=7)
    pygame.draw.polygon(s, (200, 62, 52), [(108, 9), (140, 17), (108, 25)])                   # دماغه
    pygame.draw.rect(s, (60, 66, 76), (60, 9, 6, 16))
    pygame.draw.rect(s, (60, 66, 76), (84, 9, 6, 16))
    return s


def _make_turret() -> "pygame.Surface":
    """لوله‌های دوقلوی پدافند؛ مرکز چرخش وسط تصویر است و لوله‌ها رو به راست‌اند."""
    size = 240
    c = size // 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    for off in (-9, 4):
        pygame.draw.rect(s, (52, 58, 60), (c, c + off, config.BARREL_LENGTH, 8))
        pygame.draw.rect(s, (96, 104, 106), (c, c + off, config.BARREL_LENGTH, 3))
        pygame.draw.rect(s, (30, 34, 36), (c + config.BARREL_LENGTH - 12, c + off - 2, 12, 12))
    pygame.draw.polygon(s, (88, 108, 90), [(c - 10, c - 24), (c + 22, c - 20), (c + 34, c), (c + 22, c + 20), (c - 10, c + 24)])
    pygame.draw.circle(s, (70, 88, 72), (c, c), 24)
    pygame.draw.circle(s, (34, 44, 36), (c, c), 24, 3)
    pygame.draw.circle(s, (120, 140, 122), (c, c), 8)
    return s


def make_default_logo(size: int = 440) -> "pygame.Surface":
    """آرم پیش‌فرض (سپر و ستاره) تا وقتی که فایل assets/logo.png را نگذاشته‌اید."""
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    pygame.draw.circle(s, (16, 30, 54), (c, c), c - 4)
    pygame.draw.circle(s, config.GOLD, (c, c), c - 4, 8)
    pygame.draw.circle(s, (200, 140, 40), (c, c), c - 24, 3)
    star = []
    for i in range(10):
        r = (c - 56) if i % 2 == 0 else (c - 56) * 0.42
        a = -math.pi / 2 + i * math.pi / 5
        star.append((c + r * math.cos(a), c + r * math.sin(a)))
    pygame.draw.polygon(s, config.GOLD, star)
    pygame.draw.polygon(s, (255, 230, 150), star, 3)
    return s


def load_logo(size: int = 440) -> "pygame.Surface":
    """اگر فایل آرم گروه وجود داشته باشد همان را می‌خواند، وگرنه آرم پیش‌فرض را می‌سازد."""
    if os.path.exists(config.LOGO_PATH):
        try:
            img = pygame.image.load(config.LOGO_PATH).convert_alpha()
            w, h = img.get_size()
            k = size / max(w, h)
            return pygame.transform.smoothscale(img, (max(1, int(w * k)), max(1, int(h * k))))
        except pygame.error:
            pass
    return make_default_logo(size)


def make_vignette() -> "pygame.Surface":
    """سایهٔ نرم گوشه‌های صفحه (حالت سینمایی). تصویر کوچک ساخته و بزرگ می‌شود تا هم نرم و هم سریع باشد."""
    w, h = 64, 36
    small = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            dx, dy = (x + 0.5) / w * 2 - 1, (y + 0.5) / h * 2 - 1
            d = math.hypot(dx, dy) / 1.414
            a = max(0.0, (d - 0.38) / 0.62) ** 1.6
            small.set_at((x, y), (0, 0, 0, int(215 * min(1.0, a))))
    return pygame.transform.smoothscale(small, (SCREEN_W, SCREEN_H))


def make_scanlines() -> "pygame.Surface":
    """خط‌های افقی ریز مثل نمایشگر قدیمی (فقط ظاهر)."""
    surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for y in range(0, SCREEN_H, 3):
        pygame.draw.line(surf, (0, 0, 0, 46), (0, y), (SCREEN_W, y))
    return surf


def corner_brackets(surf: "pygame.Surface", rect, length: int, color, width: int = 3) -> None:
    """چهار گوشهٔ کروشه دور یک مستطیل (قاب نشانه‌روی/نمایشگر)."""
    r = pygame.Rect(rect)
    for x, sx in ((r.left, 1), (r.right, -1)):
        for y, sy in ((r.top, 1), (r.bottom, -1)):
            pygame.draw.line(surf, color, (x, y), (x + sx * length, y), width)
            pygame.draw.line(surf, color, (x, y), (x, y + sy * length), width)


class Sprites:
    """همهٔ تصویرهای از پیش ساخته‌شده؛ در ابتدای برنامه فقط یک بار ساخته می‌شوند."""

    def __init__(self) -> None:
        self.planes = {config.F16.key: _make_f16(), config.F35.key: _make_f35()}
        self.bomb = _make_bomb()
        self.missile = _make_missile()
        self.turret = _make_turret()
        self.logo = load_logo()
        self.vignette = make_vignette()
        self.scanlines = make_scanlines()


# ---------------------------------------------------------------- پدافند
def draw_turret(surf: "pygame.Surface", sprites: Sprites, angle: float, flash: bool) -> None:
    """پدافند: پایه، لوله‌های چرخان، کیسه‌های شن و جرقهٔ دهانه."""
    x, y = config.TURRET_X, config.TURRET_Y
    pygame.draw.ellipse(surf, (60, 64, 62), (x - 62, y - 4, 124, 34))
    pygame.draw.ellipse(surf, (108, 112, 108), (x - 56, y - 12, 112, 30))
    pygame.draw.ellipse(surf, (80, 84, 80), (x - 56, y - 12, 112, 30), 3)

    rotated = pygame.transform.rotate(sprites.turret, -math.degrees(angle))
    surf.blit(rotated, rotated.get_rect(center=(x, config.TURRET_PIVOT_Y)))

    if flash:
        tx = x + math.cos(angle) * (config.BARREL_LENGTH + 6)
        ty = config.TURRET_PIVOT_Y + math.sin(angle) * (config.BARREL_LENGTH + 6)
        pts = []
        for i in range(8):
            r = 20 if i % 2 == 0 else 8
            a = angle + i * math.pi / 4
            pts.append((tx + math.cos(a) * r, ty + math.sin(a) * r))
        pygame.draw.polygon(surf, (255, 190, 70), pts)
        pygame.draw.circle(surf, (255, 248, 200), (int(tx), int(ty)), 7)

    for i in range(-4, 5):                                       # کیسه‌های شن جلوی پدافند
        pygame.draw.ellipse(surf, (176, 146, 96), (x + i * 14 - 9, y + 10, 20, 12))
        pygame.draw.ellipse(surf, (120, 96, 60), (x + i * 14 - 9, y + 10, 20, 12), 1)


def muzzle_position(angle: float) -> Tuple[float, float]:
    """نقطهٔ دهانهٔ لوله‌ها (برای شروع رد گلوله)."""
    return (config.TURRET_X + math.cos(angle) * (config.BARREL_LENGTH + 4),
            config.TURRET_PIVOT_Y + math.sin(angle) * (config.BARREL_LENGTH + 4))


def draw_rotated(surf: "pygame.Surface", sprite: "pygame.Surface", x: float, y: float, angle: float) -> None:
    """تصویری که رو به راست کشیده شده را با زاویهٔ داده‌شده (رادیان) می‌چرخاند و می‌کشد."""
    rotated = pygame.transform.rotate(sprite, -math.degrees(angle))
    surf.blit(rotated, rotated.get_rect(center=(int(x), int(y))))
