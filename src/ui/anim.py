# 界面进场动效：标题 / 面板 / 选项按次序错位淡入，并轻微上移。
#
# 用法（见 src/ui/menu.py 的 MenuState）：
#   __init__ 里建一个 self.intro = Entrance()
#   enter()  里 self.intro.reset()          —— 每次进场都从头播一遍
#   update() 里 self.intro.update(dt)
#   draw()   里 alpha, dy = self.intro.item(i) 然后 screen.blit_gpu(surf, (x, y - dy), alpha)
#
# 动画结束后 item() 一律返回 (255, 0)，绘制结果与「没有这套动效」时逐像素一致，
# 所以稳态不付任何代价：不需要在别处写 if 判断动画是否播完。

from src.engine import settings as cfg


def _ease_out(t):
    """缓出曲线：起步快、收尾稳（进场元素落到位置上不会「弹」）"""
    return 1.0 - (1.0 - t) ** 3


class Entrance:
    """一次进场动画。

    index 是元素的次序（可以是小数，用来让某一组插在两组之间）：
    第 index 项在 delay + index * stagger 秒后开始，用 duration 秒淡入，
    同时从上方 rise 像素处滑到位。
    """

    def __init__(self, duration=None, stagger=None, delay=None, rise=None):
        self.duration = cfg.UI_INTRO_DURATION if duration is None else float(duration)
        self.stagger = cfg.UI_INTRO_STAGGER if stagger is None else float(stagger)
        self.delay = cfg.UI_INTRO_DELAY if delay is None else float(delay)
        self.rise = cfg.UI_INTRO_RISE if rise is None else float(rise)
        self.time = 0.0
        self.settled = False

    def reset(self):
        """重新开始播（enter() 时调用：退出再进来也会重新错位淡入）"""
        self.time = 0.0
        self.settled = False

    def skip(self):
        """直接跳到落定状态（截图 / 冒烟工具用：它们只画帧、不推进时间）"""
        self.settled = True

    def update(self, dt):
        self.time += dt

    def item(self, index):
        """第 index 项当前的不透明度（0-255）与上移量（像素）"""
        if self.settled or self.duration <= 0.0:
            return 255, 0
        t = (self.time - self.delay - index * self.stagger) / self.duration
        if t <= 0.0:
            return 0, int(round(self.rise))
        if t >= 1.0:
            return 255, 0
        k = _ease_out(t)
        return int(round(255 * k)), int(round(self.rise * (1.0 - k)))
