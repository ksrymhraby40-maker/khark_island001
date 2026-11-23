"""
جلوه‌های ویژه: انفجار، دود، جرقه، رد گلوله و لرزش صفحه
---------------------------------------------------------
هیچ‌کدام از این‌ها روی قوانین بازی اثر ندارند؛ فقط زیبایی می‌سازند.
"""

import math
import random
from typing import List, Tuple

import pygame

from .graphics import alpha_circle, lerp_color


class Explosion:
    __slots__ = ("x", "y", "size", "age", "duration")

    def __init__(self, x: float, y: float, size: float, duration: float):
        self.x, self.y, self.size = x, y, size
        self.age, self.duration = 0.0, duration


class Particle:
    """ذره‌ای با موقعیت، سرعت و عمر (برای جرقه، دود و قطعات هواپیما)."""
    __slots__ = ("x", "y", "vx", "vy", "age", "life", "size", "dark", "spin", "angle")

    def __init__(self, x, y, vx, vy, life, size, dark=False, spin=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.age, self.life, self.size = 0.0, life, size
        self.dark, self.spin, self.angle = dark, spin, random.uniform(0, math.tau)


class Tracer:
    __slots__ = ("x0", "y0", "x1", "y1", "age")

    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1, self.age = x0, y0, x1, y1, 0.0


class Effects:
    """مجموعهٔ همهٔ جلوه‌های در حال نمایش."""

    TRACER_LIFE = 0.11

    def __init__(self, rng: random.Random = None):
        self.rng = rng or random.Random()
        self.explosions: List[Explosion] = []
        self.sparks: List[Particle] = []
        self.smoke: List[Particle] = []
        self.debris: List[Particle] = []
        self.tracers: List[Tracer] = []
        self.shake = 0.0            # شدت لرزش فعلی (پیکسل)

    # ------------------------------------------------------------ ساختن جلوه‌ها
    def explode(self, x: float, y: float, size: float = 70, sparks: int = 18,
                shake: float = 0.0) -> None:
        self.explosions.append(Explosion(x, y, size, 0.35 + size / 250))
        for _ in range(sparks):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(100, 130 + size * 3.2)
            self.sparks.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v - 40,
                                        self.rng.uniform(0.35, 0.9), self.rng.uniform(2, 4)))
        for _ in range(int(3 + size / 25)):
            self.add_smoke(x + self.rng.uniform(-size / 3, size / 3),
                           y + self.rng.uniform(-size / 4, size / 4),
                           size=self.rng.uniform(size / 4, size / 2.2), dark=True,
                           life=self.rng.uniform(1.0, 1.8))
        self.shake = max(self.shake, shake)

    def plane_explosion(self, x: float, y: float) -> None:
        """سرنگون شدن هواپیما: انفجار کوچک و چند تکهٔ فلز."""
        self.explode(x, y, size=52, sparks=14, shake=3)
        for _ in range(8):
            a = self.rng.uniform(math.pi, math.tau)
            v = self.rng.uniform(60, 220)
            self.debris.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v,
                                        self.rng.uniform(0.8, 1.5), self.rng.uniform(5, 10),
                                        spin=self.rng.uniform(-9, 9)))

    def hit_sparks(self, x: float, y: float) -> None:
        """هواپیما ضربه خورده ولی هنوز سرنگون نشده."""
        for _ in range(10):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(80, 240)
            self.sparks.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v,
                                        self.rng.uniform(0.2, 0.5), self.rng.uniform(2, 3)))
        self.add_smoke(x, y, size=14, dark=True, life=1.0)

    def add_smoke(self, x: float, y: float, size: float = 14, dark: bool = False,
                  life: float = 1.4, vx: float = 0.0, vy: float = -28.0) -> None:
        self.smoke.append(Particle(x, y, vx + self.rng.uniform(-8, 8),
                                   vy + self.rng.uniform(-8, 8), life, size, dark))

    def tracer(self, x0: float, y0: float, x1: float, y1: float) -> None:
        self.tracers.append(Tracer(x0, y0, x1, y1))

    # ------------------------------------------------------------ به‌روزرسانی
    def update(self, dt: float) -> None:
        for e in self.explosions:
            e.age += dt
        self.explosions = [e for e in self.explosions if e.age < e.duration]

        for p in self.sparks:
            p.age += dt
            p.vy += 380 * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
        self.sparks = [p for p in self.sparks if p.age < p.life]

        for p in self.debris:
            p.age += dt
            p.vy += 520 * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.angle += p.spin * dt
        self.debris = [p for p in self.debris if p.age < p.life]

        for p in self.smoke:
            p.age += dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.size += 9 * dt
        self.smoke = [p for p in self.smoke if p.age < p.life]

        for t in self.tracers:
            t.age += dt
        self.tracers = [t for t in self.tracers if t.age < self.TRACER_LIFE]

        self.shake = max(0.0, self.shake - 22 * dt)

    def shake_offset(self) -> Tuple[int, int]:
        if self.shake <= 0.2:
            return 0, 0
        return (int(self.rng.uniform(-self.shake, self.shake)),
                int(self.rng.uniform(-self.shake, self.shake)))

    # ------------------------------------------------------------ رسم
    def draw(self, surf: "pygame.Surface") -> None:
        for p in self.smoke:
            k = p.age / p.life
            base = (58, 54, 54) if p.dark else (178, 178, 184)
            alpha = int(150 * (1 - k) * min(1.0, k * 6 + 0.25))
            alpha_circle(surf, (*base, alpha), (int(p.x), int(p.y)), p.size)

        for e in self.explosions:
            self._draw_explosion(surf, e)

        for p in self.sparks:
            k = p.age / p.life
            color = lerp_color((255, 240, 160), (230, 90, 30), k)
            pygame.draw.circle(surf, color, (int(p.x), int(p.y)), max(1, int(p.size * (1 - k * 0.6))))

        for p in self.debris:
            dx, dy = math.cos(p.angle) * p.size, math.sin(p.angle) * p.size
            pygame.draw.line(surf, (60, 66, 76), (p.x - dx, p.y - dy), (p.x + dx, p.y + dy), 3)

        for t in self.tracers:
            k = t.age / self.TRACER_LIFE
            color = lerp_color((255, 250, 200), (255, 150, 50), k)
            pygame.draw.line(surf, color, (t.x0, t.y0), (t.x1, t.y1), 3 if k < 0.5 else 2)

    @staticmethod
    def _draw_explosion(surf: "pygame.Surface", e: Explosion) -> None:
        k = e.age / e.duration
        c = (int(e.x), int(e.y))
        alpha_circle(surf, (50, 46, 46, int(130 * (1 - k))), c, e.size * (0.55 + 1.0 * k))
        alpha_circle(surf, (255, 150, 30, int(230 * (1 - k * 0.8))), c, e.size * (0.35 + 0.7 * k))
        alpha_circle(surf, (255, 90, 20, int(240 * (1 - k))), c, e.size * (0.22 + 0.45 * k))
        if k < 0.55:
            alpha_circle(surf, (255, 255, 215, int(255 * (1 - k / 0.55))), c, e.size * (0.15 + 0.5 * k))
        if k < 0.7:
            pygame.draw.circle(surf, (255, 235, 190), c, int(e.size * (0.5 + 1.6 * k)), 2)
