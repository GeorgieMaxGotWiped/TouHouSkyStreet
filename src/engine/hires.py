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
# 地方改用画布提供的 hi_* 方法。
#
# 战斗区里的弹幕、贴图实体（敌机 / Boss / 自机 / 掉落物）与符卡召唤物 / 特效都已经
# 不走这张图层：前两者各有自己的显卡层（blit_gpu_over / blit_entity），层与弹幕、
# HUD 的先后关系见 display.GpuPresenter.present；特效里的向量图元（法阵、冲击环、
# 石柱、骷髅头…）由 entity_effect() 申请一块按倍率的离屏面板来画（见 EffectSurface），
# 画完 commit() 一次，仍然走在同一个实体层里。
# 仍留在 1x 本体上的是关卡背景 / 关卡特效 / 判定点 / HUD 这些「本来就不需要精细」的
# 部分（面板边框这类细线按需改用画布提供的 hi_* 方法）。

import math
import os

import pygame

# 逐块上传的脏区上限：超过就退回「包围盒整幅上传」。HUD / 面板的标脏点通常只有
# 几十块，撞上限说明这一帧真的画满了，整幅传反而更省事。
_HI_MAX_RECTS = 128

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


def pulse_color(color, steps=16):
    """菜单类界面「呼吸」高亮的颜色（带缓存友好的量化）

    相位量化成 steps 档：不量化的话每帧都是一个新颜色，文字渲染缓存与显卡纹理
    缓存都会每帧多出一张（永远命不中）。量化之后只剩 steps 种颜色，全部命中。
    """
    raw = math.sin(pygame.time.get_ticks() * 0.004) * 0.3 + 0.7     # 0.4 ~ 1.0
    level = int(round((raw - 0.4) / 0.6 * (steps - 1)))
    factor = 0.4 + 0.6 * level / float(max(1, steps - 1))
    return tuple(int(c * factor) for c in color)


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


def _scaled_lines(target, k, color, points, width=1, closed=False):
    return pygame.draw.lines(target, color, closed,
                             [(p[0] * k, p[1] * k) for p in points],
                             max(1, int(round(width * k))))


def _scaled_circle(target, k, color, center, radius, width=0):
    return pygame.draw.circle(target, color,
                              (center[0] * k, center[1] * k),
                              max(1, int(round(radius * k))),
                              max(1, int(round(width * k))) if width else 0)


def _scaled_ellipse(target, k, color, rect, width=0):
    return pygame.draw.ellipse(target, color,
                               (rect[0] * k, rect[1] * k, rect[2] * k, rect[3] * k),
                               max(1, int(round(width * k))) if width else 0)


def _scaled_arc(target, k, color, rect, start_angle, stop_angle, width=1):
    return pygame.draw.arc(target, color,
                           (rect[0] * k, rect[1] * k, rect[2] * k, rect[3] * k),
                           start_angle, stop_angle,
                           max(1, int(round(width * k))))


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

    def hi_lines(self, color, points, width=1, closed=False):
        return _scaled_lines(self, self.hi_scale, color, points, width, closed)

    def hi_circle(self, color, center, radius, width=0):
        return _scaled_circle(self, self.hi_scale, color, center, radius, width)

    def hi_ellipse(self, color, rect, width=0):
        return _scaled_ellipse(self, self.hi_scale, color, rect, width)

    def hi_arc(self, color, rect, start_angle, stop_angle, width=1):
        return _scaled_arc(self, self.hi_scale, color, rect,
                           start_angle, stop_angle, width)

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


def scratch_panel(screen, logical_size):
    """取一块「本帧专用」的可复用离屏面板（内容每帧清空重画）

    与 panel() 只差一件事：同一块表面会在相邻帧之间循环使用，不再每帧新建。战斗区尺寸
    的面板在 3x 下是 1728x2010（13MB），新建一次要 2ms 出头，第一次贴出去时还要再上传
    一次（同等量级）—— 符卡演出每帧一两块，这个开销直接压在帧时间上（实测开符的帧里
    5-9ms 花在这里）。复用之后只剩「清透明 + 一次重传」。

    因为复用的一定是同一个表面对象，而显卡纹理是按表面对象缓存的（TextureCache），
    这类面板要带 hi_dynamic 标记：回放时重新 upload 一次，否则显卡上留着的还是第一帧
    的内容。同一帧里取几块就发几个不同的槽位（本帧借出去的不再发），免得两块内容不同
    的面板撞在一起。没有显卡路径时它照样省下每帧的分配。
    """
    factor = entity_factor(screen)
    real = (max(1, int(logical_size[0] * factor)),
            max(1, int(logical_size[1] * factor)))
    pool = getattr(screen, "_hi_scratch", None)
    if pool is None:
        pool = {}
        try:
            screen._hi_scratch = pool
        except AttributeError:      # 拿到的是普通 Surface：退回每帧新建
            return panel(logical_size, factor)
    slot = pool.get(real)
    if slot is None:
        slot = {"live": [], "used": 0}
        pool[real] = slot
    if slot["used"] < len(slot["live"]):
        surf = slot["live"][slot["used"]]
    else:
        surf = HiresSurface(real, factor)
        surf.hi_dynamic = True
        slot["live"].append(surf)
    slot["used"] += 1
    surf.fill((0, 0, 0, 0))
    return surf


def reset_scratch(screen):
    """帧首归还上一帧借出的复用面板（由 Painter 每帧开始时调用）"""
    pool = getattr(screen, "_hi_scratch", None)
    if not pool:
        return
    for slot in pool.values():
        slot["used"] = 0


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


def entity_factor(screen):
    """战斗区实体 / 特效本帧该用的倍率（1 = 显卡层没开，贴图保持 1x 与旧版一致）

    判断与子弹那边的 bullet._render_factor 同一套：显卡指令层没开时（无 GPU 呈现、
    或 TOUHOU_UI_GPU=0 的对比模式）保持 1x、照旧画在 1x 画布上，关掉开关得到的
    就是旧版画面。
    """
    gpu = getattr(screen, "gpu", None)
    if gpu is not None and not getattr(gpu, "enabled", False):
        return 1
    return max(1, int(getattr(screen, "hires_factor", 1)))


class EffectSurface(HiresSurface):
    """战斗区特效面板：按渲染倍率在离屏表面上作画，画完一次性贴到实体层

    战斗区里的召唤物与符卡特效（石柱、法阵、冲击环、骷髅头、方框…）原先用
    pygame.draw.* 直接画在 960x720 的画布上，之后跟整幅画面一起被放大：细描边、
    圆弧、尖刺全糊成一片。这里给它们一块按倍率的面板 —— 图元仍按逻辑坐标写，由
    面板自己减掉 origin、乘上倍率，与画布上的 hi_* 方法同义，只是落点是自己。

    为什么不合并成「一整层向量图层」：特效与贴图是交替画的（柔光 -> 法阵 -> 贴图
    -> 灵魂火），只有让每块面板按调用顺序各自登记，才能待在原来的位置上，不会被
    整层压到贴图下面或上面。贴在哪儿由 display.GpuPresenter.present 决定
    （画布上半之上、弹幕之下，与敌机 / Boss 同一层）。

    倍率为 1 时它退化成一张普通的 1x 临时表面，绘制结果与旧版逐像素相同。
    """

    def __init__(self, logical_size, factor, origin, screen=None):
        factor = max(1, int(factor))
        super().__init__((max(1, int(round(logical_size[0] * factor))),
                          max(1, int(round(logical_size[1] * factor)))), factor)
        self._origin = (float(origin[0]), float(origin[1]))
        self._screen = screen
        self._layer = "entity"
        self._committed = False

    # --- 逻辑坐标 -> 面板内坐标 ---

    def local(self, point):
        return (point[0] - self._origin[0], point[1] - self._origin[1])

    def local_rect(self, rect):
        origin = self._origin
        return (rect[0] - origin[0], rect[1] - origin[1], rect[2], rect[3])

    # --- 图元：一律用逻辑坐标（与画布上的 hi_* 同义）---

    def rect(self, color, rect, width=0, radius=0):
        return _scaled_rect(self, self.hi_scale, color, self.local_rect(rect),
                            width, radius)

    def line(self, color, start, end, width=1):
        return _scaled_line(self, self.hi_scale, color,
                            self.local(start), self.local(end), width)

    def polygon(self, color, points, width=0):
        return _scaled_polygon(self, self.hi_scale, color,
                               [self.local(p) for p in points], width)

    def lines(self, color, points, width=1, closed=False):
        return _scaled_lines(self, self.hi_scale, color,
                             [self.local(p) for p in points], width, closed)

    def circle(self, color, center, radius, width=0):
        return _scaled_circle(self, self.hi_scale, color,
                              self.local(center), radius, width)

    def ellipse(self, color, rect, width=0):
        return _scaled_ellipse(self, self.hi_scale, color,
                               self.local_rect(rect), width)

    def arc(self, color, rect, start_angle, stop_angle, width=1):
        return _scaled_arc(self, self.hi_scale, color, self.local_rect(rect),
                           start_angle, stop_angle, width)

    def commit(self, alpha=255, add=False):
        """把这块面板贴到实体层：调用位置就是它与贴图 / 其他面板的先后顺序"""
        if self._committed:
            return None
        self._committed = True
        if self._layer == "fg":
            return _blit_fg(self._screen, self, self._origin, alpha, add)
        if self._layer == "over":
            return _blit_over(self._screen, self, self._origin, alpha, add)
        return blit_entity(self._screen, self, self._origin, alpha=alpha, add=add)


def entity_effect(screen, origin, logical_size, over=False, fg=False):
    """申请一块战斗区特效面板（按画布的渲染倍率；无倍率时等价于 1x 临时表面）

    origin 是面板左上角（逻辑坐标），logical_size 是面板的逻辑尺寸。面板上的图元
    仍按逻辑坐标写，记得画完调用 commit() 把它贴到实体层。

    over=True 时改成贴到「画布之上」那一层（弹幕层）：消弹动画这类必须与弹幕同层
    的图元用它 —— 否则会掉进实体层，被后画的弹幕整层盖住。

    fg=True 时贴到「战斗区前景」那一层（画布下半之上、HUD 之下）：弹幕之上的符卡
    遮挡 / 激光 / 压暗这类演出用它，顺序与它们原来画在画布后半时完全一致。
    """
    fx = EffectSurface(logical_size, entity_factor(screen), origin, screen)
    if fg:
        fx._layer = "fg"
    elif over:
        fx._layer = "over"
    return fx


def entity_line(screen, color, start, end, width=1, max_extent=128, over=False,
                fg=False):
    """按渲染倍率画一条长线段（自动切成若干块小面板，over 见 entity_effect）

    整条线画进一块面板的话，面板面积是长度的平方级 —— 战斗区里一条 900 逻辑像素的
    斜线，3x 下就是 20MB 的贴图，每帧重传一次。这里沿长边把线段切成若干段，每段一
    块小面板、各自仍按逻辑坐标画**整条**线（画到面板外的部分自然被裁掉），于是切段
    处的像素与「整条线一块面板」完全一致，而总开销只正比于线长。
    """
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    steps = max(1, int(math.ceil(max(abs(dx), abs(dy)) / max(1, int(max_extent)))))
    pad = int(width // 2) + 1        # 整数边距，理由见 _shape_panel
    for i in range(steps):
        t0 = i / float(steps)
        t1 = (i + 1) / float(steps)
        x0 = start[0] + dx * t0
        y0 = start[1] + dy * t0
        x1 = start[0] + dx * t1
        y1 = start[1] + dy * t1
        fx = entity_effect(screen, (min(x0, x1) - pad, min(y0, y1) - pad),
                           (abs(x1 - x0) + pad * 2, abs(y1 - y0) + pad * 2),
                           over=over, fg=fg)
        fx.line(color, start, end, width)
        fx.commit()


def baked_entity(screen, key, origin, logical_size, build, over=False, fg=False,
                 alpha=255):
    """预烤一块静态的实体层贴图并贴到 origin（逐帧不变的细线图形用）

    build(target, k) 在给定表面上按「逻辑坐标 x 渲染倍率」作画（用 painter 的
    bake_* 助手），只在第一次调用时执行一次，之后每帧就只剩一次贴图。走廊 / 圆环 /
    虚线这类逐帧不变、包围盒又很大的图形用它最合适：一块面板画满、清晰度一致，
    但不必每帧重传（见 entity_effect / entity_line 关于面板面积的取舍）。
    没有预烤缓存（纯 Surface、或关掉显卡路径的对比模式）时退回 1x 临时面板逐帧重画。
    """
    baked = getattr(screen, "baked", None)
    if baked is not None and entity_factor(screen) > 1:
        surf = baked(key, logical_size, build)
    else:
        surf = panel(logical_size, 1)
        build(surf, 1)
    if surf is None:
        return None
    if fg:
        return _blit_fg(screen, surf, origin, alpha, False)
    if over:
        return _blit_over(screen, surf, origin, alpha, False)
    return blit_entity(screen, surf, origin, alpha=alpha)


def rotate(surface, degrees):
    """旋转一张贴图 / 预烤面板（保留倍率标记）

    pygame.transform 返回的是普通表面，「倍率标记」会丢 —— 直接交给画布会被当成
    1x 贴图塞进高分辨率图层。旋转本身也应在倍率像素上做（在 1x 上转完再放大，
    斜边全是台阶），所以拿着倍率图转，转完把标记补回去。
    """
    rotated = pygame.transform.rotate(surface, degrees)
    factor = getattr(surface, "hi_scale", 1)
    return rotated if factor <= 1 else wrap(rotated, factor)


def flip(surface, flip_x=True, flip_y=False):
    """水平 / 垂直翻转（同样要补回倍率标记，见 rotate）"""
    flipped = pygame.transform.flip(surface, flip_x, flip_y)
    factor = getattr(surface, "hi_scale", 1)
    return flipped if factor <= 1 else wrap(flipped, factor)


def scale_to(surface, logical_size):
    """把一张贴图 / 预烤面板按逻辑尺寸缩放（在倍率像素上做，见 rotate）"""
    factor = getattr(surface, "hi_scale", 1)
    size = (max(1, int(round(logical_size[0] * factor))),
            max(1, int(round(logical_size[1] * factor))))
    scaled = pygame.transform.smoothscale(surface, size)
    return scaled if factor <= 1 else wrap(scaled, factor)


def _shape_panel(screen, x0, y0, x1, y1, ink=1.0, over=False, fg=False):
    """开一块贴合 (x0,y0)-(x1,y1) 的面板，并按描边宽度 ink 留出边距"""
    # 边距取整数：面板原点落在像素网格上，整数坐标的图元在倍率 1 时才能与
    # 「直接画在 1x 画布上」逐像素一致（否则半像素的原点会让整块图元错开 1 像素）
    pad = int(ink // 2) + 1
    return entity_effect(screen, (x0 - pad, y0 - pad),
                         (x1 - x0 + pad * 2, y1 - y0 + pad * 2), over=over,
                         fg=fg)


def entity_circle(screen, color, center, radius, width=0, over=False, alpha=255,
                  fg=False):
    """按渲染倍率画一个圆 / 圆环（面板自动贴合圆的包围盒，over 见 entity_effect）

    与 entity_line 同一套用法：把 pygame.draw.circle(screen, ...) 原样换成它即可 ——
    图元仍按逻辑坐标写，只有落点从 1x 画布换到了按倍率的实体层。
    """
    fx = _shape_panel(screen, center[0] - radius, center[1] - radius,
                      center[0] + radius, center[1] + radius,
                      width if width else 1, over, fg)
    fx.circle(color, center, radius, width)
    return fx.commit(alpha=alpha)


def entity_ellipse(screen, color, rect, width=0, over=False, alpha=255, fg=False):
    """按渲染倍率画一个椭圆 / 椭圆环（rect=（x, y, w, h），逻辑坐标）"""
    fx = _shape_panel(screen, rect[0], rect[1], rect[0] + rect[2],
                      rect[1] + rect[3], width if width else 1, over, fg)
    fx.ellipse(color, rect, width)
    return fx.commit(alpha=alpha)


def entity_rect(screen, color, rect, width=0, radius=0, over=False, alpha=255,
                fg=False):
    """按渲染倍率画一个矩形（圆角要按倍率画，否则圆角会被整体放大糊掉）"""
    fx = _shape_panel(screen, rect[0], rect[1], rect[0] + rect[2],
                      rect[1] + rect[3], width if width else 1, over, fg)
    fx.rect(color, rect, width, radius)
    return fx.commit(alpha=alpha)


def entity_polygon(screen, color, points, width=0, over=False, alpha=255,
                   fg=False):
    """按渲染倍率画一个多边形（斜边/斜线在 1x 上放大后是台阶）"""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fx = _shape_panel(screen, min(xs), min(ys), max(xs), max(ys),
                      width if width else 1, over, fg)
    fx.polygon(color, points, width)
    return fx.commit(alpha=alpha)


def entity_arc(screen, color, rect, start_angle, stop_angle, width=1,
               over=False, alpha=255, max_span=math.pi / 6, fg=False):
    """按渲染倍率画一段圆弧（自动切成若干块贴合弧线的面板，见 entity_line）

    整段弧一块面板的话，面板面积是半径的平方级 —— 半径 240 的一段弧，3x 下就是
    8MB 的贴图，每帧重传一次。pygame 的弧角是数学习惯（0 在右、逆时针、y 向上），
    所以按角度切段、每段只留该段的包围盒（端点 + 段内的四个极值角），切段处像素与
    「整段一块面板」一致，开销只正比于弧长。
    """
    cx = rect[0] + rect[2] * 0.5
    cy = rect[1] + rect[3] * 0.5
    rx = rect[2] * 0.5
    ry = rect[3] * 0.5
    span = float(stop_angle) - float(start_angle)
    if abs(span) < 1e-6:
        return None
    steps = max(1, int(math.ceil(abs(span) / max(1e-6, max_span))))
    step = span / steps
    for i in range(steps):
        a0 = start_angle + step * i
        a1 = a0 + step
        lo, hi = (a0, a1) if a0 <= a1 else (a1, a0)
        angles = [a0, a1]
        for k in range(4):
            cand = math.pi * 0.5 * k
            cand += math.pi * math.floor((lo - cand) / math.pi + 1.0)
            if lo <= cand <= hi:
                angles.append(cand)
        xs = [cx + rx * math.cos(t) for t in angles]
        ys = [cy - ry * math.sin(t) for t in angles]
        fx = _shape_panel(screen, min(xs), min(ys), max(xs), max(ys), width, over,
                          fg)
        fx.arc(color, rect, a0, a1, width)
        fx.commit(alpha=alpha)


def fg_rect(screen, color, rect):
    """在「战斗区前景」层铺一块纯色（黑幕 / 压暗 / 舞台色罩）

    纯色块与渲染倍率无关，缺的只是顺序：要盖住弹幕和同层的符卡演出，又不能压住
    HUD。所以这里走显卡的矩形填充，而不是按倍率烘一张整屏面板（那要几十 MB）。
    没有显卡路径时退回普通绘制，顺序与旧画面一致。
    """
    fill = getattr(screen, "fill_gpu_fg", None)
    if fill is None:
        return screen.fill(color, rect)
    return fill(color, rect)


def blit_fg(screen, source, dest, alpha=255, add=False):
    """把一张贴图 / 预烤面板贴到「战斗区前景」那一层（画布下半之上、HUD 之下）

    给弹幕之上的符卡演出用（遮挡 / 激光 / 压暗 / 分阶段光晕）：比 blit_entity 晚、
    比 HUD 早，顺序与它们原来画在 1x 画布后半时一致。没有显卡路径时退回画布 blit，
    逐像素与旧画面相同。
    """
    return _blit_fg(screen, source, dest, alpha, add)


def blit_entity(screen, source, dest, area=None, alpha=255, add=False):
    """贴战斗区实体 / 特效（敌机 / Boss / 自机 / 掉落物 / 召唤物）到实体层

    这一层由显卡按渲染倍率原生绘制，实体贴图因此不会先被拍到 960x720 的逻辑网格上
    再整幅放大。alpha 交给显卡调制（0-255，省掉 CPU 端逐帧抠一份半透明副本），
    add=True 走加法混合（亡灵展品、面具那类发光贴图）。
    画布没有这一层（无显卡路径）时落回普通 blit —— 那种情况下渲染倍率也是 1x，
    绘制结果与旧版逐像素相同。
    """
    blit = getattr(screen, "blit_gpu_entity", None)
    if blit is None:
        return _blit_plain(screen, source, dest, area, alpha, add)
    return blit(source, dest, area, alpha=alpha, add=add)


def _blit_plain(screen, source, dest, area, alpha, add):
    """没有显卡层时的后备：透明度用表面级 alpha 表现（用完还原，不动原表面）"""
    prev = source.get_alpha()
    if alpha < 255:
        source.set_alpha(alpha)
    try:
        return screen.blit(source, dest, area,
                           special_flags=pygame.BLEND_ADD if add else 0)
    finally:
        if alpha < 255:
            source.set_alpha(prev)


def _blit_over(screen, source, dest, alpha, add):
    """把特效面板贴到「画布之上」那一层（弹幕层），没有显卡路径时落回画布"""
    blit = getattr(screen, "blit_gpu_over", None)
    if blit is None:
        return _blit_plain(screen, source, dest, None, alpha, add)
    return blit(source, dest, alpha=alpha, add=add)


def _blit_fg(screen, source, dest, alpha, add):
    """战斗区前景层的落笔（画布下半之上、HUD 之下）；没有显卡路径时退回画布"""
    blit = getattr(screen, "blit_gpu_fg", None)
    if blit is None:
        return _blit_plain(screen, source, dest, None, alpha, add)
    return blit(source, dest, alpha=alpha, add=add)


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
        self._hi_rects = []         # 本帧标脏的矩形（逐块上传用）
        self._hi_prev_rects = []    # 上一帧标脏的矩形（逐块清、逐块传）

    @classmethod
    def create(cls, size):
        """按窗口像素格式建画布（blit 快路径）：convert_alpha 会返回同类实例"""
        canvas = cls(size).convert_alpha()
        canvas.hires_factor = 1
        canvas.hi = None
        canvas._hi_prev = None
        canvas._hi_cur = None
        canvas._hi_frame = None
        canvas._hi_rects = []
        canvas._hi_prev_rects = []
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
        del self._hi_rects[:]
        del self._hi_prev_rects[:]
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
        # 逐块清：标脏点散在四角（左侧血条、整条右栏、屏幕底行），拼成的包围盒
        # 几乎就是整屏，逐块清只碰真正画过的像素
        for rect in self._hi_prev_rects:
            self.hi.fill((0, 0, 0, 0), rect)
        # 这里刻意不删 _hi_prev_rects：清掉的像素本帧不一定再画一遍，如果不把
        # 这些矩形一起交给 end_frame 上传，显卡上那张纹理就还留着上一帧的内容
        # —— 平移 / 淡出的东西（对话立绘、关卡标题）会在原地留下「多余的一块」。
        # 列表在 end_frame 里换成「本帧标脏的矩形」，不会一直攒下去。
        del self._hi_rects[:]
        self._hi_prev = None
        self._hi_cur = None

    def end_frame(self):
        """每帧绘制后调用：返回本帧高分辨率图层需要上传给显卡的区域

        返回矩形列表（需要逐块上传）或 None（本帧图层是空的，连上传都不必做）。
        以前这里返回的是「本帧与上一帧脏区的并集」，成一个矩形 —— 而这批标脏点
        散在屏幕四角，并集直接等于整屏，等于每帧把 2880x2160 整幅重传一遍
        （实测 7.4ms，是开符帧里最大的一笔）。逐块传时每块几乎不要钱（0.003ms），
        只付真正画过的那些像素的带宽。
        """
        if self.hi is None:
            return None
        area = self._hi_upload_area()
        self._hi_prev_rects, self._hi_rects = self._hi_rects, []
        self._hi_prev = self._hi_cur
        return area

    def _hi_upload_area(self):
        """本帧要上传的脏区：上一帧 + 本帧去重后的矩形列表，块数过多时退成包围盒"""
        cur = self._hi_rects
        prev = self._hi_prev_rects
        if not cur:
            rects = list(prev)
        elif not prev:
            rects = list(cur)
        else:
            rects = []
            seen = set()
            for rect in prev:
                seen.add((rect.x, rect.y, rect.width, rect.height))
                rects.append(rect)
            for rect in cur:
                key = (rect.x, rect.y, rect.width, rect.height)
                if key not in seen:
                    seen.add(key)
                    rects.append(rect)
        if not rects:
            return None
        if len(rects) > _HI_MAX_RECTS:
            merged = rects[0].copy()
            for rect in rects[1:]:
                merged = merged.union(rect)
            return merged
        return rects

    def _mark_hi(self, rect):
        if rect is None:
            return
        rect = rect.inflate(2, 2).clip(self.hi.get_rect())
        self._hi_rects.append(rect)
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
