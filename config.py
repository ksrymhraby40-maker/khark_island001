"""
تنظیمات و ثابت‌های کل بازی
---------------------------
همهٔ عددهایی که روی سختی، ظاهر و جای اشیاء اثر می‌گذارند اینجا جمع شده‌اند
تا برای تغییر آن‌ها لازم نباشد کل کد را بگردید.
"""

import os
from dataclasses import dataclass
from typing import Tuple

# ---------------------------------------------------------------- مسیرها
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONT_REGULAR = os.path.join(ASSETS_DIR, "fonts", "DejaVuSans.ttf")
FONT_BOLD = os.path.join(ASSETS_DIR, "fonts", "DejaVuSans-Bold.ttf")
# اگر فایل آرم گروه را با همین نام در پوشهٔ assets بگذارید، به‌جای آرم ساخته‌شده با کد نمایش داده می‌شود.
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")      # theme.wav و battle.wav (ساختهٔ tools/make_music.py)

# بلندی موسیقی (۰ تا ۱) در بخش‌های مختلف
MUSIC_VOLUME_MENU = 0.55
MUSIC_VOLUME_INTRO = 0.50
MUSIC_VOLUME_BATTLE = 0.50

# ---------------------------------------------------------------- صفحه
# بازی در یک بوم ثابت ۱۲۸۰×۷۲۰ رسم می‌شود و سپس متناسب با اندازهٔ پنجره/گوشی بزرگ یا کوچک می‌شود.
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

# ---------------------------------------------------------------- متن‌ها
GAME_TITLE = "دفاع از جزیره خارک"
GROUP_NAME = ""   # اگر نام گروه را اینجا بنویسید، زیر آرم نمایش داده می‌شود (خالی = نمایش داده نمی‌شود)

# ---------------------------------------------------------------- رنگ‌ها
GOLD = (240, 184, 64)
WHITE = (245, 247, 250)
NAVY = (14, 28, 48)
RED = (220, 70, 60)
GREEN = (90, 210, 120)
ORANGE = (244, 150, 40)

# ---------------------------------------------------------------- هواپیماها


@dataclass(frozen=True)
class PlaneKind:
    """مشخصات یک نوع هواپیما."""
    key: str            # نام داخلی (برای پیدا کردن تصویر)
    name: str           # نام فارسی
    hp: int             # تعداد ضربه‌ای که تا سرنگون شدن لازم است
    width: int
    height: int
    speed_min: float    # سرعت (پیکسل بر ثانیه)
    speed_max: float


F16 = PlaneKind("f16", "اف-۱۶", 1, 112, 40, 190.0, 270.0)   # سریع، یک ضربه
F35 = PlaneKind("f35", "اف-۳۵", 2, 128, 46, 125.0, 185.0)   # زره‌دار، دو ضربه

# ---------------------------------------------------------------- جزیره و مخزن‌ها
TANK_COUNT = 6
TANK_MAX_HITS = 2                      # مخزن با دومین بمب منفجر می‌شود
TANK_XS = (330, 450, 570, 690, 810, 930)
TANK_Y = 575                           # خط زمین زیر مخزن‌ها

# ---------------------------------------------------------------- پدافند
TURRET_X = 640
TURRET_Y = 626
TURRET_PIVOT_Y = TURRET_Y - 16         # مرکز چرخش لوله‌ها
BARREL_LENGTH = 104
FIRE_COOLDOWN = 0.16                   # فاصلهٔ حداقل بین دو شلیک (ثانیه)
HIT_MARGIN = 14                        # بخشش جا برای ضربه‌های کمی کج (پیکسل)
TURRET_TURN_SPEED = 11.0               # رادیان بر ثانیه

# ---------------------------------------------------------------- بمب و پرواز
BOMB_SPEED = 520.0
PLANE_MIN_Y = 112
PLANE_MAX_Y = 400
HUD_HEIGHT = 70

# ---------------------------------------------------------------- مرحله‌ها


@dataclass(frozen=True)
class Slide:
    """یک اسلاید از معرفی مرحله."""
    kind: str       # date | island | missile | text
    text: str
    seconds: float


@dataclass(frozen=True)
class LevelConfig:
    number: int
    name: str
    duration: float                 # مدت مرحله به ثانیه
    spawn_start: float              # فاصلهٔ ورود هواپیماها در ابتدا (ثانیه)
    spawn_end: float                # فاصلهٔ ورود هواپیماها در انتها
    f35_start: float                # احتمال اف-۳۵ در ابتدا
    f35_end: float                  # احتمال اف-۳۵ در انتها
    speed_scale: float              # ضریب سرعت هواپیماها
    burst_chance: float             # احتمال ورود دو هواپیما با هم در پایان مرحله
    intro: Tuple[Slide, ...]


LEVELS = (
    LevelConfig(
        number=1, name="مرحله ۱", duration=120.0,
        spawn_start=2.8, spawn_end=0.6,
        f35_start=0.20, f35_end=0.60,
        speed_scale=1.15, burst_chance=0.25,
        intro=(
            Slide("date", "۱۴۰۴/۱۲/۹", 3.6),
            Slide("island", "جزیره خارک", 4.2),
            Slide("missile", "", 5.4),
            Slide("text", "از جزیره دفاع کنید", 3.4),
        ),
    ),
    LevelConfig(
        number=2, name="مرحله ۲", duration=120.0,
        spawn_start=1.8, spawn_end=0.38,
        f35_start=0.45, f35_end=0.80,
        speed_scale=1.45, burst_chance=0.45,
        intro=(
            Slide("text", "موج دوم حمله آغاز شد", 2.6),
            Slide("text", "از جزیره دفاع کنید", 2.6),
        ),
    ),
)
