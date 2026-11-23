"""
نمایش درست متن فارسی در pygame
--------------------------------
pygame حروف فارسی را نه به هم می‌چسباند و نه از راست به چپ می‌نویسد. این ماژول
بدون هیچ کتابخانهٔ خارجی دو کار را انجام می‌دهد:

  ۱) شکل‌دهی (Shaping): انتخاب شکل درست هر حرف بر اساس جای آن در کلمه
     (جدا، آغازی، میانی، پایانی) و ساختن ترکیب «لا».
  ۲) ترتیب نمایش (Bidi): برعکس کردن متن برای نوشتن از راست به چپ، با این شرط که
     اعداد و تاریخ‌ها (مثل ۱۴۰۵/۱۲/۹ یا ۰۲:۰۰) از چپ به راست و سالم بمانند.

استفاده:  font.render(visual("سلام دنیا"), True, color)
"""

from functools import lru_cache
from typing import Dict, List, Optional, Tuple

ZWNJ = "‌"  # نیم‌فاصله؛ حروف را از هم جدا می‌کند ولی خودش دیده نمی‌شود

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def _forms(isolated: int, final: Optional[int] = None,
           initial: Optional[int] = None, medial: Optional[int] = None
           ) -> Tuple[Optional[str], ...]:
    """چهار شکل یک حرف را از کدهای یونیکد (Presentation Forms) می‌سازد."""
    return tuple(None if c is None else chr(c)
                 for c in (isolated, final, initial, medial))


# هر حرف: (جدا، پایانی، آغازی، میانی). حرف‌هایی که به بعد از خود نمی‌چسبند
# (ا د ذ ر ز ژ و ...) شکل آغازی و میانی ندارند.
_FORMS: Dict[str, Tuple[Optional[str], ...]] = {
    "ء": _forms(0xFE80),                                  # ء
    "آ": _forms(0xFE81, 0xFE82),                          # آ
    "أ": _forms(0xFE83, 0xFE84),                          # أ
    "ؤ": _forms(0xFE85, 0xFE86),                          # ؤ
    "إ": _forms(0xFE87, 0xFE88),                          # إ
    "ئ": _forms(0xFE89, 0xFE8A, 0xFE8B, 0xFE8C),          # ئ
    "ا": _forms(0xFE8D, 0xFE8E),                          # ا
    "ب": _forms(0xFE8F, 0xFE90, 0xFE91, 0xFE92),          # ب
    "پ": _forms(0xFB56, 0xFB57, 0xFB58, 0xFB59),          # پ
    "ت": _forms(0xFE95, 0xFE96, 0xFE97, 0xFE98),          # ت
    "ث": _forms(0xFE99, 0xFE9A, 0xFE9B, 0xFE9C),          # ث
    "ج": _forms(0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0),          # ج
    "چ": _forms(0xFB7A, 0xFB7B, 0xFB7C, 0xFB7D),          # چ
    "ح": _forms(0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4),          # ح
    "خ": _forms(0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8),          # خ
    "د": _forms(0xFEA9, 0xFEAA),                          # د
    "ذ": _forms(0xFEAB, 0xFEAC),                          # ذ
    "ر": _forms(0xFEAD, 0xFEAE),                          # ر
    "ز": _forms(0xFEAF, 0xFEB0),                          # ز
    "ژ": _forms(0xFB8A, 0xFB8B),                          # ژ
    "س": _forms(0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4),          # س
    "ش": _forms(0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8),          # ش
    "ص": _forms(0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC),          # ص
    "ض": _forms(0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0),          # ض
    "ط": _forms(0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4),          # ط
    "ظ": _forms(0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8),          # ظ
    "ع": _forms(0xFEC9, 0xFECA, 0xFECB, 0xFECC),          # ع
    "غ": _forms(0xFECD, 0xFECE, 0xFECF, 0xFED0),          # غ
    "ف": _forms(0xFED1, 0xFED2, 0xFED3, 0xFED4),          # ف
    "ق": _forms(0xFED5, 0xFED6, 0xFED7, 0xFED8),          # ق
    "ك": _forms(0xFED9, 0xFEDA, 0xFEDB, 0xFEDC),          # ك (عربی)
    "ک": _forms(0xFB8E, 0xFB8F, 0xFB90, 0xFB91),          # ک
    "گ": _forms(0xFB92, 0xFB93, 0xFB94, 0xFB95),          # گ
    "ل": _forms(0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0),          # ل
    "م": _forms(0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4),          # م
    "ن": _forms(0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8),          # ن
    "ه": _forms(0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC),          # ه
    "و": _forms(0xFEED, 0xFEEE),                          # و
    "ي": _forms(0xFEF1, 0xFEF2, 0xFEF3, 0xFEF4),          # ي (عربی)
    "ی": _forms(0xFBFC, 0xFBFD, 0xFBFE, 0xFBFF),          # ی
}

# ترکیب «لا» و هم‌خانواده‌هایش: (جدا، پایانی)
_LAM_ALEF = {
    "آ": (chr(0xFEF5), chr(0xFEF6)),
    "أ": (chr(0xFEF7), chr(0xFEF8)),
    "إ": (chr(0xFEF9), chr(0xFEFA)),
    "ا": (chr(0xFEFB), chr(0xFEFC)),
}

# اعراب (زبر، زیر، ...) در نمایش نادیده گرفته می‌شود
_DIACRITICS = {chr(c) for c in range(0x064B, 0x0653)}

# کاراکترهایی که در راست‌به‌چپ آینه می‌شوند
_MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "«": "»", "»": "«",
           "<": ">", ">": "<"}

# جداکننده‌هایی که داخل عدد معنی دارند (تاریخ، ساعت، اعشار)
_NUMBER_SEPARATORS = set("/:.,٫٬")


# ---------------------------------------------------------------- شکل‌دهی
def _joins_to_next(ch: str) -> bool:
    """آیا این حرف به حرف بعدی می‌چسبد؟ (فقط حرف‌های «دو طرف چسب»)"""
    forms = _FORMS.get(ch)
    return forms is not None and forms[2] is not None


def _can_connect_to_prev(ch: Optional[str]) -> bool:
    """آیا این حرف می‌تواند به حرف قبلی بچسبد؟ (شکل پایانی دارد)"""
    forms = _FORMS.get(ch) if ch else None
    return forms is not None and forms[1] is not None


def shape(text: str) -> str:
    """حروف را به شکل درستشان (آغازی/میانی/پایانی/جدا) تبدیل می‌کند. ترتیب هنوز منطقی است."""
    chars = [c for c in text if c not in _DIACRITICS]
    out: List[str] = []
    i, n = 0, len(chars)
    while i < n:
        ch = chars[i]
        forms = _FORMS.get(ch)
        if forms is None:                       # فاصله، عدد، علامت، نیم‌فاصله، ...
            out.append(ch)
            i += 1
            continue

        prev = chars[i - 1] if i > 0 else None
        nxt = chars[i + 1] if i + 1 < n else None
        connect_prev = prev is not None and _joins_to_next(prev) and forms[1] is not None

        # «لا» یک شکل ترکیبی مخصوص دارد
        if ch == "ل" and nxt in _LAM_ALEF:
            isolated, final = _LAM_ALEF[nxt]
            out.append(final if connect_prev else isolated)
            i += 2
            continue

        connect_next = forms[2] is not None and _can_connect_to_prev(nxt)
        if connect_prev and connect_next:
            index = 3       # میانی
        elif connect_prev:
            index = 1       # پایانی
        elif connect_next:
            index = 2       # آغازی
        else:
            index = 0       # جدا
        out.append(forms[index])
        i += 1

    return "".join(out).replace(ZWNJ, "")


# ---------------------------------------------------------------- ترتیب نمایش
def _is_ltr_char(ch: str) -> bool:
    return ch.isdigit() or (ch.isascii() and ch.isalpha())


def _split_runs(text: str) -> List[Tuple[bool, str]]:
    """متن را به تکه‌های «چپ‌به‌راست» (عدد/لاتین) و «راست‌به‌چپ» (بقیه) می‌شکند."""
    runs: List[Tuple[bool, str]] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if _is_ltr_char(ch):
            j = i
            while j < n:
                c = text[j]
                inside_number = (c in _NUMBER_SEPARATORS and j > i
                                 and text[j - 1].isdigit()
                                 and j + 1 < n and text[j + 1].isdigit())
                if _is_ltr_char(c) or inside_number:
                    j += 1
                else:
                    break
            runs.append((True, text[i:j]))
            i = j
        else:
            j = i
            while j < n and not _is_ltr_char(text[j]):
                j += 1
            runs.append((False, text[i:j]))
            i = j
    return runs


def _reorder_line(line: str) -> str:
    shaped = shape(line)
    pieces = []
    for is_ltr, run in reversed(_split_runs(shaped)):
        if is_ltr:
            pieces.append(run)                                  # عدد سالم می‌ماند
        else:
            pieces.append("".join(_MIRROR.get(c, c) for c in reversed(run)))
    return "".join(pieces)


# اگر موتور متن pygame (SDL_ttf نسخه‌های جدید) خودش حروف عربی/فارسی را از راست به چپ بچیند،
# باید رشته را برعکسِ حالت عادی به آن بدهیم. ui.Text.calibrate() هنگام شروع این را تشخیص می‌دهد.
_ENGINE_REORDERS = False


def set_engine_reorders(flag: bool) -> None:
    global _ENGINE_REORDERS
    _ENGINE_REORDERS = bool(flag)
    visual.cache_clear()


@lru_cache(maxsize=2048)
def visual(text: str) -> str:
    """متن منطقی فارسی را به رشته‌ای تبدیل می‌کند که pygame درست نمایش دهد."""
    lines = []
    for line in text.split("\n"):
        ordered = _reorder_line(line)                 # ترتیب چپ‌به‌راست روی صفحه
        lines.append(ordered[::-1] if _ENGINE_REORDERS else ordered)
    return "\n".join(lines)


# ---------------------------------------------------------------- اعداد
def to_persian_digits(text: str) -> str:
    """رقم‌های لاتین را به رقم فارسی تبدیل می‌کند."""
    return "".join(PERSIAN_DIGITS[int(c)] if c in "0123456789" else c for c in text)


def fa_number(value: int) -> str:
    """عدد صحیح را با رقم‌های فارسی برمی‌گرداند."""
    return to_persian_digits(str(int(value)))


def format_time(seconds: float) -> str:
    """زمان را به‌صورت «دقیقه:ثانیه» با رقم فارسی برمی‌گرداند؛ مثلاً ۰۱:۳۰."""
    total = max(0, int(seconds + 0.999))     # رو به بالا گرد می‌شود تا صفر فقط وقت پایان دیده شود
    minutes, secs = divmod(total, 60)
    return to_persian_digits(f"{minutes:02d}:{secs:02d}")
