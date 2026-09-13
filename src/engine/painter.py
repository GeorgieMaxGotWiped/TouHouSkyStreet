# 东方天空街 ~ Touhou Sky Street
# 统一绘制入口：把「CPU 画布」与「显卡」两条路收敛到同一个对象上
#
# 背景：绘制原本散在各处的 screen.blit(...) / pygame.draw.*(screen, ...)，要换成显卡
# 绘制只能逐个改调用点，且没法分批验收。Painter 本身就是绘制画布（继承 HiResCanvas，
# 既有写法全部照旧可用），另外多出两个「显卡优先」的方法：
#   - fill_gpu(color, rect)    铺底色（整屏 / 整块）
#   - blit_gpu(source, dest)   贴一张已经准备好的图（背景 / 图标 / 预烤面板）
# 有 GPU 呈现时，它们被登记进本帧的显卡指令，由 present() 统一回放；没有 GPU 时原样
# 落回画布（带倍率标记的表面会自动进高分辨率图层），所以无 GPU 也不会退化。
#
# 为什么面板要「预烤」：显卡只会贴图，不会画圆 / 多边形 / 渐变。把一块面板先按渲染
# 倍率画成一张图并缓存起来，之后每帧就只剩一次贴图 —— 这就是把「每帧现算」变成
# 「静态贴图」的标准做法。
#
# 坐标约定：Painter 一律使用 960x720 的逻辑坐标；显卡层内部再按渲染倍率换算。

import os
import weakref

import pygame

from src.engine import hires

# 显卡优先绘制的总开关（调试 / 对比截图用；关掉后一切与旧版一致）
_enabled = os.environ.get("TOUHOU_UI_GPU", "1") != "0"


def enabled():
    return _enabled


def set_enabled(value):
    global _enabled
    _enabled = bool(value)


def _rect_tuple(rect):
    """把 Rect / (x, y) / (x, y, w, h) 统一成 (x, y, w, h)"""
    if isinstance(rect, pygame.Rect):
        return (rect.x, rect.y, rect.width, rect.height)
    if len(rect) >= 4:
        return (int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))
    return (int(rect[0]), int(rect[1]), 0, 0)


def _dest_tuple(dest):
    """blit 的 dest 可以是 Rect（取左上）或 (x, y)"""
    if isinstance(dest, pygame.Rect):
        return (float(dest.x), float(dest.y))
    return (float(dest[0]), float(dest[1]))


def scale_rect(rect, scale):
    """逻辑矩形 -> 图层像素矩形"""
    x, y, w, h = _rect_tuple(rect)
    return (int(round(x * scale)), int(round(y * scale)),
            int(round(w * scale)), int(round(h * scale)))


# --- 预烤面板用的小助手 ---
# 这些函数把「逻辑坐标」换算成高分辨率表面的真实像素：显卡只会贴图，不会画圆 /
# 多边形 / 渐变，所以把这些图元先画进一张图里，之后每帧就只剩一次贴图。


def bake_fill(target, color):
    """铺满整块高分辨率表面"""
    target.fill(color)


def bake_rect(target, k, color, rect, width=0, radius=0):
    return hires._scaled_rect(target, k, color, rect, width, radius)


def bake_line(target, k, color, start, end, width=1):
    return hires._scaled_line(target, k, color, start, end, width)


def bake_polygon(target, k, color, points, width=0):
    return hires._scaled_polygon(target, k, color, points, width)


def bake_circle(target, k, color, center, radius, width=0):
    return pygame.draw.circle(target, color,
                              (int(round(center[0] * k)), int(round(center[1] * k))),
                              max(1, int(round(radius * k))),
                              max(1, int(round(width * k))) if width else 0)


def bake_arc(target, k, color, rect, start_angle, stop_angle, width=1):
    return pygame.draw.arc(target, color,
                           (rect[0] * k, rect[1] * k, rect[2] * k, rect[3] * k),
                           start_angle, stop_angle, max(1, int(round(width * k))))


class SurfaceCache:
    """按 key 缓存「预先画好的一张图」：把每帧重画变成每帧贴图。

    key 必须包含所有会影响画面的参数（尺寸、配色、选中状态等）。
    """

    def __init__(self, limit=192):
        self._limit = max(8, int(limit))
        self._items = {}
        self._order = []

    def get(self, key, build):
        surf = self._items.get(key)
        if surf is not None:
            return surf
        try:
            surf = build()
        except Exception as e:
            print(f"[Painter] surface build failed for {key}: {e}")
            return None
        if surf is None:
            return None
        if len(self._order) >= self._limit:
            self._items.pop(self._order.pop(0), None)
        self._items[key] = surf
        self._order.append(key)
        return surf

    def clear(self):
        self._items.clear()
        del self._order[:]

    def __len__(self):
        return len(self._items)


class GpuLayer:
    """本帧登记给显卡的绘制指令（只记录，不回放）。

    回放放在 present()（见 display.GpuPresenter）：显卡绘制与 1x 画布、高分辨率图层
    的先后顺序才能在一个地方控制，而不是散在绘制代码里。
    """

    def __init__(self):
        self.ops = []
        self.scale = 1
        self.enabled = False

    def begin(self, scale, enabled):
        del self.ops[:]
        self.scale = max(1, int(scale))
        self.enabled = bool(enabled)

    def fill(self, color, rect):
        self.ops.append(("fill", tuple(int(c) for c in color),
                         scale_rect(rect, self.scale)))

    def texture(self, surface, dest):
        self.ops.append(("tex", surface,
                         scale_rect((_dest_tuple(dest)[0], _dest_tuple(dest)[1], 0, 0),
                                    self.scale)))

    def __len__(self):
        return len(self.ops)


class TextureCache:
    """按源 Surface 缓存 GPU 纹理（与伪3D 地面纹理同一套路）。

    纹理属于当前 renderer，换窗口 / 换渲染器时随 presenter 一起重建。
    """

    def __init__(self, renderer):
        self._renderer = renderer
        self._items = {}      # id(surface) -> (weakref, Texture)
        self.uploads = 0

    def get(self, surface):
        try:
            key = id(surface)
            entry = self._items.get(key)
            if entry is not None and entry[0]() is surface:
                return entry[1]
            from pygame._sdl2 import video as video_module
            tex = video_module.Texture.from_surface(self._renderer, surface)
            tex.blend_mode = 1     # 逐像素 alpha 混合
            if len(self._items) > 512:
                self._items = {k: v for k, v in self._items.items()
                               if v[0]() is not None}
            self._items[key] = (weakref.ref(surface), tex)
            self.uploads += 1
            return tex
        except Exception as e:
            print(f"[Painter] texture upload failed: {e}")
            return None

    def drop(self, surface):
        self._items.pop(id(surface), None)

    def clear(self):
        self._items.clear()


class Painter(hires.HiResCanvas):
    """统一绘制入口：逻辑坐标下的画布 + 显卡指令收集器。"""

    def __init__(self, size, flags=pygame.SRCALPHA):
        super().__init__(size, flags)
        self.cache = SurfaceCache()
        self.gpu = GpuLayer()
        self._gpu_pending = False

    @classmethod
    def create(cls, size):
        """按窗口像素格式建画布（保留 HiResCanvas 那套高分辨率图层字段）"""
        canvas = cls(size).convert_alpha()
        canvas.hires_factor = 1
        canvas.hi = None
        canvas._hi_prev = None
        canvas._hi_cur = None
        canvas._hi_frame = None
        canvas.cache = SurfaceCache()
        canvas.gpu = GpuLayer()
        canvas._gpu_pending = False
        return canvas

    # --- 每帧开关 ---

    def begin_gpu_frame(self, scale, gpu_available):
        """帧首：重置本帧的显卡指令（scale=渲染倍率，gpu_available=显卡路径是否可用）"""
        self.gpu.begin(scale, gpu_available and _enabled)

    def gpu_ops(self):
        return self.gpu.ops if self.gpu.enabled else ()

    # --- 显卡优先的绘制 ---

    def fill_gpu(self, color, rect=None):
        """铺底色：有显卡就交给显卡填矩形，否则落回画布"""
        if not self.gpu.enabled:
            return self.fill(color, rect)
        if rect is None:
            w, h = pygame.Surface.get_size(self)
            rect = (0, 0, w, h)
        self.gpu.fill(color, rect)
        return pygame.Rect(_rect_tuple(rect))

    def blit_gpu(self, source, dest, area=None):
        """贴一张「已经准备好的图」：背景 / 图标 / 预烤面板。

        没有显卡时退回画布 —— 带倍率标记的表面会进高分辨率图层，清晰度一致，
        只是合成仍在 CPU 上做。
        """
        if not self.gpu.enabled or area is not None:
            return self.blit(source, dest, area)
        factor = getattr(source, "hi_scale", 1)
        if factor > 1 and factor != self.hires_factor:
            # 倍率对不齐：交给画布走 hires.rescale 的兜底换算
            return self.blit(source, dest, area)
        self.gpu.texture(source, dest)
        return pygame.Rect(int(_dest_tuple(dest)[0]), int(_dest_tuple(dest)[1]),
                           pygame.Surface.get_width(source) // max(1, factor),
                           pygame.Surface.get_height(source) // max(1, factor))

    # --- 预烤面板 ---

    def blit_baked(self, key, dest, logical_size, build):
        """把一块面板按渲染倍率烤成图并贴到 dest（逻辑坐标）。

        build(target, k)：target 是这块面板的高分辨率表面，用上面的 bake_* 助手
        在它上面作画即可（key 必须包含所有会影响画面的参数，否则会取到旧图）。
        """
        surf = self.baked(key, logical_size, build)
        if surf is None:
            return None
        x, y = _dest_tuple(dest)
        self.blit_gpu(surf, (int(x), int(y)))
        return surf


    def bake_factor(self):
        """预烤面板使用的倍率。

        显卡路径关闭时退回 1x —— 这样「关掉开关」得到的就是旧版的画面，
        对比截图才有意义。
        """
        return max(1, int(self.hires_factor)) if _enabled else 1

    def baked(self, key, logical_size, build):
        """按渲染倍率预烤一张面板图并缓存。

        build(surface, factor)：在给定表面上用 hires 的缩放助手作画。
        返回带倍率标记的表面（无 GPU 时会自动走画布的高分辨率图层）。
        """
        factor = self.bake_factor()
        cache_key = (factor,) + tuple(key)

        def _build():
            surf = hires.panel(logical_size, factor)
            if build is not None:
                build(surf, factor)
            return surf

        return self.cache.get(cache_key, _build)