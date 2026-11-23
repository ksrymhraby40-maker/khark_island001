"""
معرفی سینمایی مرحله
--------------------
مرحلهٔ ۱ چهار اسلاید دارد:
  ۱) صفحهٔ سیاه؛ تاریخ حرف‌به‌حرف تایپ می‌شود (با صدای ماشین‌تحریر)
  ۲) نقشهٔ جزیره با زوم آرام، رادار، قفل هدف و نام «جزیره خارک»
  ۳) هشدار و آژیر؛ موشک می‌آید، به جزیره می‌خورد و منفجر می‌شود
  ۴) «از جزیره دفاع کنید» و شروع بازی
همهٔ اسلایدها نوار سینمایی، خط‌های نمایشگر و سایهٔ گوشه‌ها دارند.
با کلیک یا لمس می‌توان از هر اسلاید رد شد (Esc: رفتن مستقیم به بازی).
"""

import math
import random

import pygame

from .. import config
from ..config import LevelConfig, SCREEN_H, SCREEN_W
from ..effects import Effects
from ..graphics import MAP_ISLAND, alpha_circle, corner_brackets, dim_overlay, draw_rotated
from ..persian import fa_number
from .base import Scene

BAR_H = 62                        # ارتفاع نوار سیاه سینمایی بالا و پایین
FADE = 0.55                       # مدت محو شدن ابتدا و انتهای هر اسلاید
CX, CY = SCREEN_W // 2, SCREEN_H // 2
MISSILE_START = (150, -60)        # جایی که موشک وارد می‌شود
MISSILE_TARGET = (660, 400)       # جای برخورد روی جزیره
MISSILE_FLY_FROM, MISSILE_FLY_TO = 0.6, 2.7
TYPE_START, DATE_STEP, TITLE_STEP = 0.7, 0.16, 0.09
GOLD_DIM = (176, 134, 52)
RADAR = (90, 255, 205)
ALERT = (255, 84, 70)


def clamp01(k: float) -> float:
    return max(0.0, min(1.0, k))


def ease_out(k: float) -> float:
    return 1.0 - (1.0 - clamp01(k)) ** 3


class IntroScene(Scene):
    def __init__(self, app, level: LevelConfig) -> None:
        super().__init__(app)
        self.level = level
        self.index = 0
        self.rng = random.Random()
        self.layer = pygame.Surface((SCREEN_W, SCREEN_H))                # برای لرزش صفحه
        self.fx_layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)   # رادار و نشانه‌ها
        self.total_t = 0.0
        self.done = False                # بعد از آخرین اسلاید true می‌شود (هنگام محو شدن به بازی)
        self._enter_slide()

    def on_enter(self) -> None:
        self.app.sounds.play_music("battle", config.MUSIC_VOLUME_INTRO)

    # ------------------------------------------------------------ مدیریت اسلاید
    @property
    def slide(self):
        return self.level.intro[self.index]

    def _enter_slide(self) -> None:
        self.t = 0.0
        self.fx = Effects(self.rng)
        self.flash = 0.0
        self.shock = None                # زمان از لحظهٔ برخورد (برای موج انفجار)
        self.impact_done = False
        self.typed = 0                   # تعداد حرف‌های تایپ‌شده
        self._played = set()
        self._trail_timer = 0.0
        self._fire_timer = 0.0

    def _once(self, key: str, sound: str, volume: float = 1.0) -> None:
        if key not in self._played:
            self._played.add(key)
            self.app.sounds.play(sound, volume)

    def _next_slide(self) -> None:
        if self.done:
            return
        self.app.sounds.stop("siren")
        if self.index + 1 >= len(self.level.intro):
            self._start_game()
        else:
            self.index += 1
            self._enter_slide()

    def _start_game(self) -> None:
        if self.done:
            return
        self.done = True                 # اسلاید آخر همان‌طور می‌ماند تا محو شدن تمام شود
        from .play import PlayScene
        self.app.change_scene(PlayScene(self.app, self.level))

    # ------------------------------------------------------------ رویدادها
    def on_press(self, pos) -> None:
        self._next_slide()

    def on_back(self) -> None:
        self.app.sounds.stop("siren")
        self._start_game()

    # ------------------------------------------------------------ به‌روزرسانی
    def update(self, dt: float) -> None:
        self.total_t += dt
        self.t = min(self.t + dt, self.slide.seconds + 1.0)
        self.fx.update(dt)
        self.flash = max(0.0, self.flash - dt * 1.6)
        if self.shock is not None:
            self.shock += dt

        kind = self.slide.kind
        if kind == "date":
            self._update_typing(self.slide.text, DATE_STEP, TYPE_START)
        elif kind == "island":
            self._update_typing(self.slide.text, TITLE_STEP, 0.9)
        elif kind == "missile":
            self._update_missile(dt)
        elif kind == "text" and self.t > 0.05:
            self._once("stinger", "stinger", 0.7)

        if self.t >= self.slide.seconds:
            self._next_slide()

    def _update_typing(self, text: str, step: float, start: float) -> None:
        count = min(len(text), int((self.t - start) / step) + 1) if self.t >= start else 0
        if count > self.typed:
            self.typed = count
            self.app.sounds.play("tick", 0.5)

    def _missile_position(self):
        k = clamp01((self.t - MISSILE_FLY_FROM) / (MISSILE_FLY_TO - MISSILE_FLY_FROM))
        k = k * k                                           # موشک رو به پایین تندتر می‌شود
        sx, sy = MISSILE_START
        tx, ty = MISSILE_TARGET
        return sx + (tx - sx) * k, sy + (ty - sy) * k

    def _update_missile(self, dt: float) -> None:
        if self.t >= 0.1 and not self.impact_done:
            self._once("siren", "siren", 0.8)
        if self.t >= MISSILE_FLY_FROM:
            self._once("whistle", "whistle", 0.6)
        if MISSILE_FLY_FROM <= self.t < MISSILE_FLY_TO:
            self._trail_timer -= dt
            if self._trail_timer <= 0:
                x, y = self._missile_position()
                self.fx.add_smoke(x - 60, y - 24, size=12, dark=False, life=1.1)
                self._trail_timer = 0.03
        if self.t >= MISSILE_FLY_TO and not self.impact_done:
            self.impact_done = True
            self.shock = 0.0
            tx, ty = MISSILE_TARGET
            self.fx.explode(tx, ty, size=170, sparks=50, shake=20)
            self.flash = 1.0
            self.app.sounds.stop("siren")
            self.app.sounds.play("boom")
        if self.impact_done:                                # بعد از برخورد، دود و آتش می‌ماند
            self._fire_timer -= dt
            if self._fire_timer <= 0:
                tx, ty = MISSILE_TARGET
                self.fx.add_smoke(tx + self.rng.uniform(-60, 60), ty + self.rng.uniform(-20, 20),
                                  size=self.rng.uniform(18, 30), dark=True, life=2.2)
                self._fire_timer = 0.12

    # ------------------------------------------------------------ رسم
    def draw(self, surf) -> None:
        kind = self.slide.kind
        if kind == "date":
            self._draw_date(surf)
        elif kind == "island":
            self._draw_island(surf)
        elif kind == "missile":
            self._draw_missile(surf)
        else:
            self._draw_text(surf)

        # جلوهٔ سینمایی مشترک
        surf.blit(self.app.sprites.scanlines, (0, 0))
        surf.blit(self.app.sprites.vignette, (0, 0))
        self._draw_letterbox(surf)

        # محو شدن از/به سیاه در ابتدا و انتهای اسلاید
        fade_in = 1.0 - self.t / FADE
        fade_out = 1.0 - (self.slide.seconds - self.t) / FADE
        dim_overlay(surf, int(255 * max(0.0, fade_in, fade_out)))

    def _draw_letterbox(self, surf) -> None:
        h = int(BAR_H * ease_out(self.total_t / 0.8))
        pygame.draw.rect(surf, (0, 0, 0), (0, 0, SCREEN_W, h))
        pygame.draw.rect(surf, (0, 0, 0), (0, SCREEN_H - h, SCREEN_W, h))
        if self.total_t > 1.2:
            self.app.text.draw(surf, "برای رد شدن لمس کنید", 20, (150, 160, 176),
                               (SCREEN_W - 28, SCREEN_H - BAR_H // 2), anchor="midright", shadow=False)

    @staticmethod
    def _reveal(surf, image, edge_x: float, cy: float, fraction: float, from_right: bool) -> None:
        """
        تصویر کامل یک متن را تدریجی آشکار می‌کند (به‌جای چیدن تکه‌های ناقص متن که شکل حروف
        را عوض می‌کند). تاریخ از چپ و متن فارسی از راست آشکار می‌شود؛ edge_x لبهٔ ثابت متن است.
        """
        w, h = image.get_size()
        shown = int(w * clamp01(fraction))
        if shown <= 0:
            return
        if from_right:
            surf.blit(image, (edge_x - shown, cy - h // 2), pygame.Rect(w - shown, 0, shown, h))
        else:
            surf.blit(image, (edge_x, cy - h // 2), pygame.Rect(0, 0, shown, h))

    # ---- اسلاید ۱: تاریخ
    def _draw_date(self, surf) -> None:
        text = self.app.text
        surf.fill((0, 0, 0))
        k = ease_out((self.t - 0.1) / 0.8)
        frame = pygame.Rect(0, 0, int(820 * k), int(250 * k))
        frame.center = (CX, CY)
        if k > 0.02:
            corner_brackets(surf, frame, 34, GOLD_DIM, 3)

        full = self.slide.text
        frac = self.typed / len(full)
        image = text.render(full, 128, config.WHITE, True)
        left = CX - image.get_width() // 2
        glitch = self.typed == len(full) and self.t < TYPE_START + DATE_STEP * len(full) + 0.45
        if glitch and self.rng.random() < 0.5:                                 # لرزش رنگی کوتاه بعد از تایپ
            self._reveal(surf, text.render(full, 128, (255, 60, 60), True), left - 5, CY, frac, False)
            self._reveal(surf, text.render(full, 128, (60, 230, 255), True), left + 5, CY, frac, False)
        self._reveal(surf, text.render(full, 128, (0, 0, 0), True), left + 2, CY + 3, frac, False)   # سایه
        self._reveal(surf, image, left, CY, frac, False)

        if self.typed < len(full) and int(self.t * 3) % 2 == 0:                # مکان‌نما
            pygame.draw.rect(surf, config.GOLD, (left + int(image.get_width() * frac) + 8, CY - 54, 8, 108))
        if self.typed == len(full):                                           # خط زیر تاریخ باز می‌شود
            line = ease_out((self.t - (TYPE_START + DATE_STEP * len(full))) / 0.6)
            pygame.draw.line(surf, config.GOLD, (CX - 330 * line, CY + 92), (CX + 330 * line, CY + 92), 3)

    # ---- اسلاید ۲: نقشه، رادار، قفل هدف
    def _draw_island(self, surf) -> None:
        text = self.app.text
        progress = clamp01(self.t / self.slide.seconds)
        zoom = 1.0 + 0.16 * progress                                           # زوم آرام روی نقشه
        view = pygame.Rect(int(CX - CX / zoom), int(CY - CY / zoom), int(SCREEN_W / zoom), int(SCREEN_H / zoom))
        surf.blit(pygame.transform.scale(self.app.map_bg.subsurface(view), (SCREEN_W, SCREEN_H)), (0, 0))

        cx = (MAP_ISLAND["cx"] - view.x) * zoom
        cy = (MAP_ISLAND["cy"] - view.y) * zoom
        self._draw_radar(surf, cx, cy, zoom)

        # قفل هدف: کروشه‌ها کوچک می‌شوند و روی جزیره می‌نشینند
        lock = ease_out((self.t - 0.5) / 1.3)
        half = int((210 - 120 * lock) * zoom)
        box = pygame.Rect(int(cx) - half, int(cy) - half // 2, half * 2, half)
        corner_brackets(surf, box, 30, ALERT if int(self.t * 4) % 2 == 0 or lock < 1 else (255, 170, 90), 4)
        pygame.draw.line(surf, ALERT, (cx - 16, cy), (cx + 16, cy), 2)
        pygame.draw.line(surf, ALERT, (cx, cy - 16), (cx, cy + 16), 2)

        # نام جزیره با تایپ، و مختصات
        title = self.slide.text
        image = text.render(title, 84, config.WHITE, True)
        right = CX + image.get_width() // 2
        frac = self.typed / len(title)
        band = pygame.Surface((SCREEN_W, 170), pygame.SRCALPHA)
        band.fill((0, 0, 0, 150))
        surf.blit(band, (0, 476))
        self._reveal(surf, text.render(title, 84, (0, 0, 0), True), right + 2, 551, frac, True)    # سایه
        self._reveal(surf, image, right, 548, frac, True)
        if self.typed >= len(title):
            k = ease_out((self.t - (0.9 + TITLE_STEP * len(title))) / 0.6)
            pygame.draw.line(surf, config.GOLD, (CX - 250 * k, 598), (CX + 250 * k, 598), 3)
            text.draw(surf, "۲۹.۲۳ شمالی   ۵۰.۳۲ شرقی", 26, GOLD_DIM, (CX, 626), shadow=False)

    def _draw_radar(self, surf, cx: float, cy: float, zoom: float) -> None:
        layer = self.fx_layer
        layer.fill((0, 0, 0, 0))
        for radius, alpha in ((110, 70), (210, 56), (320, 44)):
            pygame.draw.circle(layer, (*RADAR, alpha), (int(cx), int(cy)), int(radius * zoom), 2)
        reach = 340 * zoom
        angle = self.t * 2.4
        for i in range(26):                                                    # دُم محو شوندهٔ پرتو
            a0, a1 = angle - i * 0.045, angle - (i + 1) * 0.045
            pts = [(cx, cy), (cx + reach * math.cos(a0), cy + reach * math.sin(a0)),
                   (cx + reach * math.cos(a1), cy + reach * math.sin(a1))]
            pygame.draw.polygon(layer, (*RADAR, int(125 * (1 - i / 26))), pts)
        pygame.draw.line(layer, (170, 255, 225, 210), (cx, cy),
                         (cx + reach * math.cos(angle), cy + reach * math.sin(angle)), 2)
        surf.blit(layer, (0, 0))

    # ---- اسلاید ۳: هشدار و موشک
    def _draw_missile(self, surf) -> None:
        text = self.app.text
        shake = self.fx.shake_offset()
        layer = self.layer
        layer.blit(self.app.map_bg, (0, 0))
        tx, ty = MISSILE_TARGET
        approaching = self.t < MISSILE_FLY_TO

        if approaching:
            dim_overlay(layer, int(60 * (0.5 + 0.5 * math.sin(self.t * 9))), (190, 0, 0))     # سرخی نبض‌دار
            x, y = self._missile_position()
            self._draw_dashes(layer, (x, y), (tx, ty))
            pulse = 1.0 + 0.2 * math.sin(self.t * 10)
            pygame.draw.circle(layer, ALERT, (tx, ty), int(44 * pulse), 3)
            pygame.draw.circle(layer, ALERT, (tx, ty), int(22 * pulse), 2)
            pygame.draw.line(layer, ALERT, (tx - 60, ty), (tx + 60, ty), 2)
            pygame.draw.line(layer, ALERT, (tx, ty - 60), (tx, ty + 60), 2)
        if self.impact_done:                                # جای سوختگی روی جزیره
            alpha_circle(layer, (24, 18, 14, 190), (tx, ty), 84)
            alpha_circle(layer, (70, 30, 14, 200), (tx, ty), 46)
        if approaching and self.t >= MISSILE_FLY_FROM:
            x, y = self._missile_position()
            angle = math.atan2(ty - MISSILE_START[1], tx - MISSILE_START[0])
            alpha_circle(layer, (255, 170, 60, 200), (int(x - 78 * math.cos(angle)), int(y - 78 * math.sin(angle))), 18)
            draw_rotated(layer, self.app.sprites.missile, x, y, angle)
        self.fx.draw(layer)
        if self.shock is not None:                          # موج انفجار: حلقه‌های روشن که محو می‌شوند
            rings = self.fx_layer
            rings.fill((0, 0, 0, 0))
            for delay, width in ((0.0, 6), (0.16, 4), (0.32, 3)):
                age = self.shock - delay
                if 0 < age < 0.9:
                    pygame.draw.circle(rings, (255, 228, 176, int(230 * (1.0 - age / 0.9))),
                                       (tx, ty), int(30 + age * 620), width)
            layer.blit(rings, (0, 0))

        surf.fill((0, 0, 0))
        surf.blit(layer, shake)
        dim_overlay(surf, int(210 * self.flash), (255, 244, 220))

        if approaching:                                     # بنر هشدار و شمارش معکوس
            banner = pygame.Surface((SCREEN_W, 64), pygame.SRCALPHA)
            banner.fill((150, 10, 10, 205))
            surf.blit(banner, (0, 84))
            if int(self.t * 3) % 2 == 0:
                text.draw(surf, "هشدار! موشک در حال نزدیک شدن", 42, config.WHITE, (CX, 116), bold=True)
            left = max(0, math.ceil(MISSILE_FLY_TO - self.t))
            text.draw(surf, f"برخورد تا {fa_number(left)} ثانیه", 30, (255, 190, 120), (CX, 184))

    @staticmethod
    def _draw_dashes(layer, start, end) -> None:
        """خط‌چین مسیر موشک از جای فعلی تا هدف."""
        x0, y0 = start
        x1, y1 = end
        length = math.hypot(x1 - x0, y1 - y0)
        if length < 1:
            return
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        d = 0.0
        while d < length:
            e = min(length, d + 14)
            pygame.draw.line(layer, (255, 120, 96), (x0 + ux * d, y0 + uy * d), (x0 + ux * e, y0 + uy * e), 3)
            d += 28

    # ---- اسلاید ۴: متن بزرگ
    def _draw_text(self, surf) -> None:
        text = self.app.text
        surf.fill((0, 0, 0))
        k = ease_out(self.t / 0.6)
        base = text.render(self.slide.text, 88, config.WHITE, True)
        scale = 1.35 - 0.35 * k                                                # از درشت به اندازهٔ اصلی می‌نشیند
        size = (max(2, int(base.get_width() * scale)), max(2, int(base.get_height() * scale)))
        image = pygame.transform.smoothscale(base, size)
        image.set_alpha(int(255 * clamp01(self.t / 0.4)))
        surf.blit(image, image.get_rect(center=(CX, CY - 14)))

        line = ease_out((self.t - 0.3) / 0.7)
        half = int(base.get_width() * 0.62 * line)
        for y in (CY - 96, CY + 64):
            pygame.draw.line(surf, config.GOLD, (CX - half, y), (CX + half, y), 3)
        if self.t > 1.0 and int(self.t * 2.5) % 2 == 0:
            text.draw(surf, "آماده باشید", 30, (255, 190, 120), (CX, CY + 130), shadow=False)
