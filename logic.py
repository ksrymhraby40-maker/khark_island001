"""
منطق بازی (کاملاً مستقل از pygame)
------------------------------------
این ماژول قوانین بازی را اجرا می‌کند: ورود هواپیماها، شلیک پدافند، پرتاب بمب،
خرابی مخزن‌ها، برد و باخت. چون هیچ چیزی از نمایش در آن نیست، می‌شود بدون
باز کردن پنجره آن را آزمایش کرد (پوشهٔ tests و tools).

نمایش (گرافیک و صدا) رویدادهای تولیدشده را از World.pop_events() می‌خواند.
"""

import math
import random
from dataclasses import dataclass
from typing import List, NamedTuple, Optional

from . import config
from .config import LevelConfig, PlaneKind

# وضعیت‌های بازی
PLAYING, WON, LOST = "playing", "won", "lost"

# وضعیت‌های مخزن
TANK_HEALTHY, TANK_DAMAGED, TANK_DESTROYED = 0, 1, 2


class Event(NamedTuple):
    """یک اتفاق در بازی که نمایش باید به آن واکنش نشان دهد (صدا، انفجار، ...)."""
    name: str
    x: float = 0.0
    y: float = 0.0
    data: object = None


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass
class Tank:
    """یک مخزن نفت."""
    index: int
    x: float
    y: float
    hits: int = 0           # تعداد بمب‌هایی که به آن خورده
    reserved: int = 0       # تعداد هواپیماهایی که در راه‌اند و این مخزن را هدف گرفته‌اند

    @property
    def state(self) -> int:
        return min(self.hits, config.TANK_MAX_HITS)

    @property
    def destroyed(self) -> bool:
        return self.hits >= config.TANK_MAX_HITS

    @property
    def free_capacity(self) -> int:
        """چند بمب دیگر هنوز می‌تواند به این مخزن اختصاص یابد."""
        return config.TANK_MAX_HITS - self.hits - self.reserved


@dataclass
class Plane:
    """یک هواپیمای دشمن که از چپ وارد می‌شود و به‌سمت راست پرواز می‌کند."""
    kind: PlaneKind
    x: float
    base_y: float
    speed: float
    hp: int
    target: Tank            # مخزنی که این هواپیما بمب‌اش را روی آن می‌اندازد
    drop_x: float           # وقتی x به این عدد برسد بمب رها می‌شود
    phase: float = 0.0      # فاز کمی بالا و پایین رفتن هنگام پرواز
    age: float = 0.0
    bomb_dropped: bool = False

    @property
    def y(self) -> float:
        return self.base_y + math.sin(self.age * 2.2 + self.phase) * 5.0

    def contains(self, px: float, py: float, margin: float = 0.0) -> bool:
        """آیا نقطهٔ (px, py) داخل بدنهٔ هواپیما (با کمی بخشش) است؟"""
        return (abs(px - self.x) <= self.kind.width / 2 + margin
                and abs(py - self.y) <= self.kind.height / 2 + margin)


@dataclass
class Bomb:
    """بمبی که از هواپیما رها شده و به‌سمت مخزن می‌رود."""
    x: float
    y: float
    target: Tank
    angle: float = 0.0      # زاویهٔ حرکت (برای رسم)


class World:
    """وضعیت کامل یک دور بازی."""

    def __init__(self, level: LevelConfig, rng: Optional[random.Random] = None):
        self.level = level
        self.rng = rng or random.Random()
        self.state = PLAYING
        self.time_left = level.duration
        self.tanks: List[Tank] = [Tank(i, x, config.TANK_Y)
                                  for i, x in enumerate(config.TANK_XS)]
        self.planes: List[Plane] = []
        self.bombs: List[Bomb] = []
        self._events: List[Event] = []
        self._spawn_timer = 1.2             # اولین هواپیما کمی بعد از شروع می‌آید

        # پدافند
        self.turret_angle = -math.pi / 2    # رو به بالا
        self._aim_angle = self.turret_angle
        self.cooldown = 0.0
        self.since_shot = 99.0
        self._clock = 0.0

        # آمار برای صفحهٔ نتیجه
        self.shots = 0
        self.hits = 0
        self.downed = 0

    # ------------------------------------------------------------ اطلاعات
    @property
    def progress(self) -> float:
        """پیشرفت مرحله از ۰ تا ۱."""
        return min(1.0, max(0.0, 1.0 - self.time_left / self.level.duration))

    @property
    def accuracy(self) -> float:
        return self.hits / self.shots if self.shots else 0.0

    @property
    def tanks_alive(self) -> int:
        return sum(1 for t in self.tanks if not t.destroyed)

    def pop_events(self) -> List[Event]:
        """رویدادهای ثبت‌شده از آخرین فراخوانی را برمی‌گرداند و فهرست را خالی می‌کند."""
        events, self._events = self._events, []
        return events

    def _emit(self, name: str, x: float = 0.0, y: float = 0.0, data: object = None) -> None:
        self._events.append(Event(name, x, y, data))

    # ------------------------------------------------------------ به‌روزرسانی
    def update(self, dt: float) -> None:
        self._clock += dt
        self._update_turret(dt)
        if self.state == WON:                  # بعد از برد، هواپیماها بدون بمب‌اندازی از صفحه می‌روند
            self._update_planes(dt, allow_bombs=False)
            self._update_bombs(dt)
            return
        if self.state != PLAYING:
            return
        self.since_shot += dt
        self.cooldown = max(0.0, self.cooldown - dt)
        self.time_left -= dt

        self._update_spawner(dt)
        self._update_planes(dt)
        self._update_bombs(dt)

        if self.state == PLAYING and self.time_left <= 0:
            self.time_left = 0.0
            self.state = WON
            self._emit("game_won")

    # ---- ورود هواپیماها
    def _update_spawner(self, dt: float) -> None:
        self._spawn_timer -= dt
        if self._spawn_timer > 0:
            return
        self._spawn_plane()
        p = self.progress
        interval = lerp(self.level.spawn_start, self.level.spawn_end, p)
        self._spawn_timer = interval * self.rng.uniform(0.8, 1.2)
        # در دقیقهٔ آخر گاهی دو هواپیما با هم می‌آیند
        if self.rng.random() < self.level.burst_chance * p:
            self._spawn_plane()

    def _pick_target(self) -> Optional[Tank]:
        """اولین مخزنی که هنوز ظرفیت بمب خوردن دارد؛ پس ترتیب خرابی از مخزن ۱ به بعد است."""
        for tank in self.tanks:
            if tank.free_capacity > 0:
                return tank
        return None

    def _pick_lane(self) -> float:
        """ارتفاعی برای ورود که با هواپیماهای تازه‌وارد برخورد نکند."""
        best_y, best_gap = config.PLANE_MIN_Y, -1.0
        for _ in range(6):
            y = self.rng.uniform(config.PLANE_MIN_Y, config.PLANE_MAX_Y)
            near = [abs(y - p.base_y) for p in self.planes if p.x < 420]
            gap = min(near) if near else 999.0
            if gap > best_gap:
                best_y, best_gap = y, gap
        return best_y

    def _spawn_plane(self) -> bool:
        target = self._pick_target()
        if target is None:      # همهٔ بمب‌های ممکن قبلاً به هواپیماهای در راه اختصاص یافته
            return False
        p = self.progress
        f35_chance = lerp(self.level.f35_start, self.level.f35_end, p)
        kind = config.F35 if self.rng.random() < f35_chance else config.F16
        speed = self.rng.uniform(kind.speed_min, kind.speed_max)
        speed *= self.level.speed_scale * (1.0 + 0.15 * p)
        drop_x = max(90.0, target.x - self.rng.uniform(170.0, 260.0))
        plane = Plane(kind=kind, x=-kind.width / 2, base_y=self._pick_lane(),
                      speed=speed, hp=kind.hp, target=target, drop_x=drop_x,
                      phase=self.rng.uniform(0, math.tau))
        target.reserved += 1
        self.planes.append(plane)
        return True

    # ---- حرکت هواپیماها
    def _update_planes(self, dt: float, allow_bombs: bool = True) -> None:
        for plane in list(self.planes):
            plane.age += dt
            plane.x += plane.speed * dt
            if allow_bombs and not plane.bomb_dropped and plane.x >= plane.drop_x:
                self._drop_bomb(plane)
            if plane.x - plane.kind.width / 2 > config.SCREEN_W + 30:
                self.planes.remove(plane)

    def _drop_bomb(self, plane: Plane) -> None:
        plane.bomb_dropped = True
        bomb = Bomb(plane.x, plane.y + 12, plane.target)
        self._aim_bomb(bomb)
        self.bombs.append(bomb)
        self._emit("bomb_drop", bomb.x, bomb.y)

    @staticmethod
    def _bomb_goal(bomb: Bomb):
        return bomb.target.x, bomb.target.y - 36      # وسط بدنهٔ مخزن

    def _aim_bomb(self, bomb: Bomb) -> None:
        gx, gy = self._bomb_goal(bomb)
        bomb.angle = math.atan2(gy - bomb.y, gx - bomb.x)

    # ---- بمب‌ها
    def _update_bombs(self, dt: float) -> None:
        for bomb in list(self.bombs):
            gx, gy = self._bomb_goal(bomb)
            dx, dy = gx - bomb.x, gy - bomb.y
            dist = math.hypot(dx, dy)
            step = config.BOMB_SPEED * dt
            if dist <= step:
                self.bombs.remove(bomb)
                self._bomb_lands(bomb)
            else:
                bomb.x += dx / dist * step
                bomb.y += dy / dist * step
                bomb.angle = math.atan2(dy, dx)

    def _bomb_lands(self, bomb: Bomb) -> None:
        tank = bomb.target
        tank.hits += 1
        tank.reserved -= 1
        self._emit("bomb_hit", tank.x, tank.y - 36, tank)
        if tank.destroyed:
            self._emit("tank_destroyed", tank.x, tank.y - 30, tank)
        if self.state == PLAYING and all(t.destroyed for t in self.tanks):
            self.state = LOST
            self._emit("game_lost")

    # ------------------------------------------------------------ پدافند
    def _update_turret(self, dt: float) -> None:
        """لولهٔ پدافند به‌سمت آخرین هدف می‌چرخد و وقتی بیکار است آرام این‌سو و آن‌سو می‌رود."""
        if self.since_shot > 1.2 and self.state == PLAYING:
            self._aim_angle = -math.pi / 2 + 0.9 * math.sin(self._clock * 0.9)
        diff = (self._aim_angle - self.turret_angle + math.pi) % math.tau - math.pi
        max_step = config.TURRET_TURN_SPEED * dt
        self.turret_angle += max(-max_step, min(max_step, diff))

    def fire(self, x: float, y: float) -> str:
        """
        شلیک به نقطهٔ (x, y). خروجی یکی از این‌هاست:
        "cooldown" (هنوز آمادهٔ شلیک نیست)، "miss"، "hit" (هواپیما آسیب دید)، "down" (سرنگون شد).
        """
        if self.state != PLAYING or self.cooldown > 0:
            return "cooldown"
        self.cooldown = config.FIRE_COOLDOWN
        self.since_shot = 0.0
        self.shots += 1
        self._aim_angle = math.atan2(y - config.TURRET_PIVOT_Y, x - config.TURRET_X)
        self._emit("shot", x, y)

        # از میان هواپیماهایی که نقطه روی آن‌هاست، نزدیک‌ترین به مرکز انتخاب می‌شود
        candidates = [p for p in self.planes if p.contains(x, y, config.HIT_MARGIN)]
        if not candidates:
            self._emit("miss", x, y)
            return "miss"
        plane = min(candidates, key=lambda p: (p.x - x) ** 2 + (p.y - y) ** 2)
        plane.hp -= 1
        self.hits += 1
        if plane.hp > 0:
            self._emit("plane_hit", plane.x, plane.y, plane)
            return "hit"

        self.planes.remove(plane)
        if not plane.bomb_dropped:          # بمبی که هنوز رها نشده، دیگر رها نمی‌شود
            plane.target.reserved -= 1
        self.downed += 1
        self._emit("plane_down", plane.x, plane.y, plane)
        return "down"
