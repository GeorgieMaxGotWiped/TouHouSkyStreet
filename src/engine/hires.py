# 高分辨率图层：文字 / 立绘 / 面板按「渲染倍率」原生绘制，避开 1x 画面整体放大的模糊
#
# 背景：伪3D 地面已经按渲染倍率在显卡上原生绘制（见 display.py / pseudo3d.py），
# 但文字与立绘仍画在 960x720 的逻辑画布上，被整幅放大后发虚。本模块给它们单独开
# 一张「倍率倍」的图层：
#   - FallbackFont 按「逻辑字号 x 倍率」渲染，并在表面打上 hi_scale 标记；
#   - 画布 HiResCanvas 发现来源带标记，就把这次 blit 改投到高分辨率图层，位置按
#     逻辑坐标 x 倍率换算；没带标记的（战斗实体、背景、向量图元）仍画 1x 本体；
#   - 呈现时先铺 1x 画面（战斗区可能已抠空露出显卡直绘的地面），再叠加高分辨率图层。
# 关键约定：高分辨率表面把 get_width/get_height/get_size/get_rect 回报为「逻辑尺寸」，
# 于是既有的排版代码（居中、右对齐、按文字宽度做底板、按宽度换行）不用改也仍然正确。
#
# 已知取舍：pygame.draw.* 直接落在 1x 本体上（C 层调用无法按倍率换算），所以面板
# 边框、分隔线这类细线仍是 1x 放大；纯色块与深色底上的模糊基本不可见，需要精确的
# 地方改用画布提供的 hi_* 方法。战斗区实体（弹幕 / 敌机 / 玩家 / 特效）同理仍走
# 1x 本体，与地面 / 文字 / 立绘之间有清晰度落差；把它们也交给显卡按倍率原生绘制
# 属于后续计划。

import os

import pygame

_scale = 1
_ver = 0
_enabled = os.environ.get("TOUHOU_HIRES", "1") != "0"


def enabled():
    return _enabled


def set_enabled(value):
    """开关高分辨率图层（调试/对比用；关闭后一切与旧版一致）"""
    global _enabled
    _enabled = bool(value)
    if not _enabled:
        set_scale(1)


def scale():
    """当前高分辨率图层倍率（1 = 关闭，全部走 1x 本体）"""
    return _scale


def version():
    """倍率版本号：切倍率时自增，供各处缓存做键（切换后旧缓存自动失效）"""
    return _ver


def set_scale(factor):
    """设置高分辨率图层倍率；返回实际生效值"""
    global _scale, _ver
    factor = max(1, int(factor))
    if not _enabled:
        factor = 1
    if factor != _scale:
        _scale = factor
        _ver += 1
    return _scale


def _scaled_rect(target, k, color, rect, width=0, radius=0):
    return pygame.draw.rect(target, color,
                            (rect[0] * k, rect[1] * k, rect[2] * k, rect[3] * k),
                            max(1, int(round(width * k))) if width else 0,
                            border_radius=max(1, int(round(radius * k))) if radius else 0)


def _scaled_line(target, k, color, start, end, width=1):
    return pygame.draw.line(target, color,
                            (start[0] * k, start[1] * k),
                            (end[0] * k, end[1] * k),
                            max(1, int(round(width * k))))


def _scaled_polygon(target, k, color, points, width=0):
    return pygame.draw.polygon(target, color,
                               [(p[0] * k, p[1] * k) for p in points],
                               max(1, int(round(width * k))) if width else 0)


class HiresSurface(pygame.Surface):
    """带倍率标记的表面：真实像素是「逻辑尺寸 x 倍率」，度量接口回报逻辑尺寸"""

    def __init__(self, size, factor=1, owner=None, key=None):
        real_w = max(1, int(size[0]))
        real_h = max(1, int(size[1]))
        super().__init__((real_w, real_h), pygame.SRCALPHA)
        factor = max(1, int(factor))
        self.hi_scale = factor
        self._logical = (max(1, int(round(real_w / float(factor)))),
                         max(1, int(round(real_h / float(factor)))))
        self._owner = owner
        self._key = key

    # --- 逻辑度量（真实像素是逻辑尺寸的 hi_scale 倍）---

    def _logical_size(self):
        logical = getattr(self, "_logical", None)
        if logical is None:
            return pygame.Surface.get_size(self)
        return logical

    def get_size(self):
        return self._logical_size()

    def get_width(self):
        return self._logical_size()[0]

    def get_height(self):
        return self._logical_size()[1]

    def get_rect(self, **kwargs):
        w, h = self._logical_size()
        rect = pygame.Rect(0, 0, w, h)
        for name, value in kwargs.items():
            setattr(rect, name, value)
        return rect

    def copy(self):
        surf = pygame.Surface.copy(self)
        surf.hi_scale = getattr(self, "hi_scale", 1)
        surf._logical = self._logical_size()
        return surf

    def convert_alpha(self, *args):
        surf = pygame.Surface.convert_alpha(self, *args)
        surf.hi_scale = getattr(self, "hi_scale", 1)
        surf._logical = self._logical_size()
        return surf

    # --- 被就地改写（改 alpha / 铺底色）即从缓存里摘掉，避免污染其他调用方 ---

    def _evict(self):
        owner = getattr(self, "_owner", None)
        key = getattr(self, "_key", None)
        if owner is not None and key is not None:
            try:
                if owner._text_cache.get(key) is self:
                    del owner._text_cache[key]
            except Exception:
                pass

    def set_alpha(self, value, flags=0):
        self._evict()
        return pygame.Surface.set_alpha(self, value, flags)

    def set_colorkey(self, color, flags=0):
        self._evict()
        return pygame.Surface.set_colorkey(self, color, flags)

    def fill(self, color, rect=None, special_flags=0):
        self._evict()
        return pygame.Surface.fill(self, color, rect, special_flags)

    # --- 逻辑坐标的绘制（与画布上的 hi_* 同义，只是目标就是自己）---

    def new_panel(self, logical_size):
        return panel(logical_size, self.hi_scale)

    def hi_rect(self, color, rect, width=0, radius=0):
        return _scaled_rect(self, self.hi_scale, color, rect, width, radius)

    def hi_line(self, color, start, end, width=1):
        return _scaled_line(self, self.hi_scale, color, start, end, width)

    def hi_polygon(self, color, points, width=0):
        return _scaled_polygon(self, self.hi_scale, color, points, width)

    def blit(self, source, dest, area=None, special_flags=0):
        """目标/来源都是逻辑坐标：来源按本面倍率贴到对应真实像素位置"""
        k = self.hi_scale
        factor = getattr(source, "hi_scale", 1)
        if k <= 1:
            return pygame.Surface.blit(self, source, dest, area, special_flags)
        if factor != k:
            source = rescale(source, k)
        if isinstance(dest, pygame.Rect):
            x, y = dest.x, dest.y
        else:
            x, y = dest[0], dest[1]
        src_area = area
        if src_area is not None:
            if not isinstance(src_area, pygame.Rect):
                src_area = pygame.Rect(src_area)
            src_area = pygame.Rect(int(round(src_area.x * k)), int(round(src_area.y * k)),
                                   int(round(src_area.width * k)),
                                   int(round(src_area.height * k)))
        return pygame.Surface.blit(self, source, (int(round(x * k)), int(round(y * k))),
                                   src_area, special_flags)


def wrap(surface, factor=None):
    """把已有表面包成带倍率标记的高分辨率表面（像素复制一次）"""
    factor = scale() if factor is None else max(1, int(factor))
    if factor <= 1 or surface is None:
        return surface
    out = HiresSurface(pygame.Surface.get_size(surface), factor)
    pygame.Surface.blit(out, surface, (0, 0))
    return out


def panel(logical_size, factor=None):
    """按逻辑尺寸建一张高分辨率面板底（文字背后的框、整屏遮罩等）"""
    factor = scale() if factor is None else max(1, int(factor))
    return HiresSurface((max(1, int(logical_size[0] * factor)),
                         max(1, int(logical_size[1] * factor))), factor)


def _scale_into(image, real, dest):
    """把 image 缩放到 real 并写进 dest。

    注意：三参数的 smoothscale 会直接往目标缓冲区里写，源与目标的像素格式
    （位深 / 通道顺序）不一致时会把画面写坏 —— 例如 24 位 BGR 的 PNG 写进 32 位
    RGBA 表面，通道会整体错位、alpha 变成噪声。只有格式一致时才走这条快路径，
    否则先缩放成新表面再整幅贴过去。
    """
    try:
        same_format = (image.get_bitsize() == dest.get_bitsize()
                       and image.get_masks() == dest.get_masks())
    except Exception:
        same_format = False
    if same_format:
        pygame.transform.smoothscale(image, real, dest)
    else:
        pygame.Surface.blit(dest, pygame.transform.smoothscale(image, real), (0, 0))


def scaled_image(image, logical_size, factor=None):
    """把图片缩放到目标逻辑尺寸，并写进高分辨率表面"""
    factor = scale() if factor is None else max(1, int(factor))
    real = (max(1, int(round(logical_size[0] * factor))),
            max(1, int(round(logical_size[1] * factor))))
    if factor <= 1:
        return pygame.transform.smoothscale(image, real)
    out = HiresSurface(real, factor)
    _scale_into(image, real, out)
    return out


def rescale(surface, factor):
    """把带倍率标记的表面换算到目标倍率（正常情况下倍率一致，这里是保险）"""
    cur = getattr(surface, "hi_scale", 1)
    factor = max(1, int(factor))
    if cur == factor:
        return surface
    w, h = pygame.Surface.get_size(surface)
    real = (max(1, int(round(w * factor / float(cur)))),
            max(1, int(round(h * factor / float(cur)))))
    small = pygame.transform.smoothscale(surface, real)
    # 变换函数不保留表面级 alpha 调制，手动带上（否则横幅淡出会失效）
    surf_alpha = surface.get_alpha()
    if surf_alpha is not None:
        small.set_alpha(surf_alpha)
    if factor <= 1:
        return small
    return wrap(small, factor)


# --- 给绘制代码用的小包装：画布支持高分辨率图层就走它，否则退回普通绘制 ---

def ui_line(screen, color, start, end, width=1):
    """UI 细线（分隔线、指示条）：走高分辨率图层才不会被放大成糊线"""
    draw = getattr(screen, "hi_line", None)
    if draw is None:
        return pygame.draw.line(screen, color, start, end, width)
    return draw(color, start, end, width)


def ui_rect(screen, color, rect, width=0, radius=0):
    draw = getattr(screen, "hi_rect", None)
    if draw is None:
        # 普通表面：半透明色块要混合（draw.rect 是覆写），先画到临时表面再贴
        if len(color) > 3 and color[3] < 255 and width == 0:
            surf = pygame.Surface((max(1, int(rect[2])), max(1, int(rect[3]))),
                                  pygame.SRCALPHA)
            surf.fill(color)
            return screen.blit(surf, (rect[0], rect[1]))
        if radius:
            return pygame.draw.rect(screen, color, rect, width, border_radius=radius)
        return pygame.draw.rect(screen, color, rect, width)
    return draw(color, rect, width, radius)


def ui_polygon(screen, color, points, width=0):
    draw = getattr(screen, "hi_polygon", None)
    if draw is None:
        return pygame.draw.polygon(screen, color, points, width)
    return draw(color, points, width)


def ui_panel(screen, logical_size):
    """文字 / 图形背后的底板：按逻辑尺寸给，实际像素乘倍率"""
    make = getattr(screen, "new_panel", None)
    if make is None:
        return pygame.Surface((max(1, int(logical_size[0])),
                               max(1, int(logical_size[1]))), pygame.SRCALPHA)
    return make(logical_size)


# 整屏遮罩缓存：3x 下这块有 24MB，每帧重建要 4ms（分配 + 逐行清空），而内容恒定
_OVERLAY_CACHE = {}


def overlay_surface(logical_size, factor, color, alpha):
    """整屏遮罩表面（按尺寸 / 倍率 / 颜色缓存；内容恒定，可以安全复用）"""
    key = (int(logical_size[0]), int(logical_size[1]), int(factor),
           tuple(color[:3]), int(alpha))
    surf = _OVERLAY_CACHE.get(key)
    if surf is None:
        if len(_OVERLAY_CACHE) > 8:
            _OVERLAY_CACHE.clear()
        surf = panel(logical_size, factor)
        surf.fill((color[0], color[1], color[2], alpha))
        _OVERLAY_CACHE[key] = surf
    return surf


def ui_overlay(screen, color=(0, 0, 0), alpha=160):
    """整屏遮罩：高分辨率图层上才能盖住已经画上去的文字与面板"""
    return overlay_surface(pygame.Surface.get_size(screen),
                           getattr(screen, "hires_factor", 1), color, alpha)


class HiResCanvas(pygame.Surface):
    """逻辑画布：本体是 1x 像素，另有一张倍率倍图层承接文字 / 立绘 / 面板

    带 hi_scale 标记的来源自动改投高分辨率图层（位置按逻辑坐标 x 倍率换算），
    其余绘制原样落在 1x 本体上。这样分层是「按来源」的，绘制代码基本不用改。
    """

    def __init__(self, size, flags=pygame.SRCALPHA):
        super().__init__(size, flags)
        self.hires_factor = 1
        self.hi = None
        self._hi_prev = None
        self._hi_cur = None
        self._hi_frame = None

    @classmethod
    def create(cls, size):
        """按窗口像素格式建画布（blit 快路径）：convert_alpha 会返回同类实例"""
        canvas = cls(size).convert_alpha()
        canvas.hires_factor = 1
        canvas.hi = None
        canvas._hi_prev = None
        canvas._hi_cur = None
        canvas._hi_frame = None
        return canvas

    # --- 倍率 ---

    def hires_size(self):
        width, height = pygame.Surface.get_size(self)
        return (width * self.hires_factor, height * self.hires_factor)

    def set_hires_factor(self, factor):
        """切换高分辨率图层倍率（1 = 关闭，只画 1x 本体）"""
        factor = max(1, int(factor))
        if factor == self.hires_factor:
            return
        self.hires_factor = factor
        self._hi_prev = None
        self._hi_cur = None
        self._hi_frame = None
        if factor <= 1:
            self.hi = None
        else:
            width, height = pygame.Surface.get_size(self)
            self.hi = pygame.Surface((width * factor, height * factor),
                                     pygame.SRCALPHA).convert_alpha()

    # --- 帧管理（脏矩形：只清 / 只传本帧真正画过的区域）---

    def begin_frame(self, frame_id=None):
        """每帧绘制前调用：清掉上一帧高分辨率图层占用的区域"""
        if frame_id is not None:
            if self._hi_frame == frame_id:
                return
            self._hi_frame = frame_id
        if self.hi is None:
            return
        if self._hi_prev is not None:
            self.hi.fill((0, 0, 0, 0), self._hi_prev)
        self._hi_cur = None

    def end_frame(self):
        """每帧绘制后调用：返回本帧高分辨率图层需要上传给显卡的矩形"""
        if self.hi is None:
            return None
        area = self._hi_cur
        if self._hi_prev is not None:
            area = self._hi_prev.copy() if area is None else area.union(self._hi_prev)
        self._hi_prev = self._hi_cur
        return area

    def _mark_hi(self, rect):
        if rect is None:
            return
        rect = rect.inflate(2, 2).clip(self.hi.get_rect())
        if self._hi_cur is None:
            self._hi_cur = rect
        else:
            self._hi_cur = self._hi_cur.union(rect)

    # --- 绘制 ---

    def hi_clip(self):
        """高分辨率图层当前应使用的裁剪矩形（跟随画布裁剪，按倍率换算）"""
        if self.hi is None:
            return None
        clip = self.get_clip()
        if clip == pygame.Rect(0, 0, pygame.Surface.get_width(self),
                               pygame.Surface.get_height(self)):
            return None
        k = self.hires_factor
        return pygame.Rect(int(clip.x * k), int(clip.y * k),
                           int(clip.width * k), int(clip.height * k))

    def blit(self, source, dest, area=None, special_flags=0):
        factor = getattr(source, "hi_scale", 1)
        if factor > 1:
            if self.hi is None or factor != self.hires_factor:
                source = rescale(source, self.hires_factor)
                if self.hi is None:
                    return pygame.Surface.blit(self, source, dest, area, special_flags)
            k = self.hires_factor
            if isinstance(dest, pygame.Rect):
                x, y = dest.x, dest.y
            else:
                x, y = dest[0], dest[1]
            src_area = area
            if src_area is not None:
                if not isinstance(src_area, pygame.Rect):
                    src_area = pygame.Rect(src_area)
                src_area = pygame.Rect(int(round(src_area.x * k)), int(round(src_area.y * k)),
                                       int(round(src_area.width * k)),
                                       int(round(src_area.height * k)))
            clip = self.hi_clip()
            if clip is None:
                rect = pygame.Surface.blit(self.hi, source,
                                           (int(round(x * k)), int(round(y * k))),
                                           src_area, special_flags)
            else:
                old_clip = self.hi.get_clip()
                self.hi.set_clip(clip)
                try:
                    rect = pygame.Surface.blit(self.hi, source,
                                               (int(round(x * k)), int(round(y * k))),
                                               src_area, special_flags)
                finally:
                    self.hi.set_clip(old_clip)
            self._mark_hi(rect)
            return rect
        return pygame.Surface.blit(self, source, dest, area, special_flags)

    def overlay(self, color=(0, 0, 0), alpha=160):
        """整屏遮罩：走高分辨率图层时才能盖住已经画上去的文字 / 面板"""
        return overlay_surface(pygame.Surface.get_size(self), self.hires_factor,
                               color, alpha)

    def new_panel(self, logical_size):
        """按逻辑尺寸建一张高分辨率面板底（可 fill / 画框 / 再 blit 文字）"""
        return panel(logical_size, self.hires_factor)

    # 以下方法用于「必须精确」的细线 / 边框：直接画在高分辨率图层上

    def hi_rect(self, color, rect, width=0, radius=0):
        if self.hi is None:
            # 没有高分辨率图层时退回 1x 画布：pygame.draw.rect 是「覆写」而不是
            # 「混合」，所以半透明色块不能直接画（会把底下的背景抹掉），
            # 改成先画在临时表面上再贴过去，按正常混合落笔。
            if len(color) > 3 and color[3] < 255:
                surf = pygame.Surface((max(1, int(rect[2])), max(1, int(rect[3]))),
                                      pygame.SRCALPHA)
                pygame.draw.rect(surf, color,
                                 (0, 0, surf.get_width(), surf.get_height()),
                                 width, border_radius=radius or 0)
                return self.blit(surf, (rect[0], rect[1]))
            if radius:
                return pygame.draw.rect(self, color, rect, width, border_radius=radius)
            return pygame.draw.rect(self, color, rect, width)
        out = _scaled_rect(self.hi, self.hires_factor, color, rect, width, radius)
        self._mark_hi(out)
        return out

    def hi_line(self, color, start, end, width=1):
        if self.hi is None:
            return pygame.draw.line(self, color, start, end, width)
        out = _scaled_line(self.hi, self.hires_factor, color, start, end, width)
        self._mark_hi(out)
        return out

    def hi_polygon(self, color, points, width=0):
        if self.hi is None:
            return pygame.draw.polygon(self, color, points, width)
        out = _scaled_polygon(self.hi, self.hires_factor, color, points, width)
        self._mark_hi(out)
        return out
