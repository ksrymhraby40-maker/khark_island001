"""کلاس پایهٔ همهٔ صفحه‌ها."""


class Scene:
    """
    رابطی که App از هر صفحه انتظار دارد. مختصات ماوس/لمس همیشه در بوم ۱۲۸۰×۷۲۰
    داده می‌شود، پس صفحه‌ها نگران اندازهٔ واقعی پنجره یا گوشی نیستند.
    """

    def __init__(self, app) -> None:
        self.app = app

    def on_enter(self) -> None:           # لحظه‌ای که صفحه فعال می‌شود (مثلاً برای شروع موسیقی)
        pass

    def on_press(self, pos) -> None:      # شروع کلیک / لمس
        pass

    def on_release(self, pos) -> None:    # پایان کلیک / لمس
        pass

    def on_move(self, pos) -> None:       # حرکت ماوس
        pass

    def on_back(self) -> None:            # کلید Esc یا دکمهٔ برگشت اندروید
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surf) -> None:
        pass
