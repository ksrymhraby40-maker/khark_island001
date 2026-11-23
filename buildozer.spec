[app]

# --- مشخصات برنامه (نام روی گوشی فارسی است؛ شناسهٔ بسته باید لاتین باشد) ---
title = دفاع از جزیره خارک
package.name = khargdefense
package.domain = org.kharg
version = 1.0

# --- فایل‌های برنامه ---
source.dir = .
source.include_exts = py,png,ttf,wav,txt
source.exclude_dirs = tests,tools,bin,.github,.buildozer,__pycache__
# فایل شروع باید main.py باشد

# --- کتابخانه‌ها ---
# اگر ساخت روی pygame خطا داد، راهنمای README (بخش «اگر ساخت خطا داد») را ببینید.
requirements = python3,pygame

# --- نمایش ---
orientation = landscape
fullscreen = 1
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #0a1322

# --- اندروید ---
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.wakelock = True
android.allow_backup = False
# بازی به هیچ مجوزی (اینترنت، حافظه و ...) نیاز ندارد
android.permissions =

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
