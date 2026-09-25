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
#
# 为什么还有第二个显卡层（ops_over）：战斗区的内容是交错的 —— 地面 / 敌机 / 自机
# 在弹幕之下，符卡前景遮罩 / 自机判定点 / HUD 在弹幕之上。一张画布表达不了这种
# 顺序，所以弹幕走「画布之上、高分辨率图层之下」这一层（blit_gpu_over），由
# present() 在画布之后回放。界面类画面只用第一个层，行为与以前完全一致。

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


def _dest_scaled(dest, scale):
    """贴图指令的 dest（逻辑坐标，可带小数）-> 图层像素坐标

    顺序要紧：**先乘倍率、再取整**。取整如果落在逻辑坐标上（int(x) * scale），
    位置就只能落在 1 逻辑像素 = 倍率个物理像素的网格上 —— 3x 下就是 3 像素一级
    的台阶，斜着飞的弹幕会走成一级一级的锯齿。改到图层空间取整后，最小步进降到
    1 个图层像素（呈现到窗口时仍是 1 个物理像素），台阶随之消失。

    也不要改用 scale_rect()：那个函数的 _rect_tuple 会把坐标先 int 掉，小数部分
    在到这里之前就没了。
    """
    x, y = _dest_tuple(dest)
    return (int(round(x * scale)), int(round(y * scale)))


def _int_dest(dest):
    """整数版 dest：给画布 blit 用（Surface.blit 只吃整数坐标）"""
    x, y = _dest_tuple(dest)
    return (int(round(x)), int(round(y)))


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
        return self.put(key, surf)

    def peek(self, key):
        """只查缓存（命中返回表面，未命中返回 None）

        给「每帧每发子弹都要查一次」的调用点用：省掉每次调用都要新建的闭包。
        """
        return self._items.get(key)

    def put(self, key, surf):
        """把一张已经画好的图按 key 存进缓存（超出上限时先丢最早的一张）"""
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
        self.ops_fg = []        # 画布下半之上、高分辨率图层之下（战斗区前景：弹幕之上的符卡演出 / 遮挡 / 激光）
        self.ops_ui = []        # 1x 画布之上、高分辨率图层之下（HUD 面板底板）
        self.ops_entity = []    # 画布下半之上、弹幕之下（战斗区实体：敌机 / Boss / 自机 / 掉落物）
        self.ops_over = []      # 画布之上那一层（战斗区弹幕）
        self.ops_top = []       # 所有图层之上那一层（符卡宣言立绘：要压住 HUD）
        self.scale = 1
        self.enabled = False

    def begin(self, scale, enabled):
        del self.ops[:]
        del self.ops_fg[:]
        del self.ops_ui[:]
        del self.ops_entity[:]
        del self.ops_over[:]
        del self.ops_top[:]
        self.scale = max(1, int(scale))
        self.enabled = bool(enabled)

    def fill(self, color, rect, clip=None, ui=False, fg=False):
        op = ("fill", tuple(int(c) for c in color),
              scale_rect(rect, self.scale),
              None if clip is None else scale_rect(clip, self.scale))
        if fg:
            self.ops_fg.append(op)
        else:
            (self.ops_ui if ui else self.ops).append(op)

    def texture(self, surface, dest, over=False, entity=False, clip=None,
                alpha=255, add=False, fg=False):
        # clip：登记指令时画布上生效的裁剪框（逻辑坐标，None = 不裁）。和 op 里的
        # 矩形一样要换算到「图层空间」（逻辑坐标 x 渲染倍率），回放时才对得上。
        # 显卡指令是在画布之外回放的，画布的 set_clip 管不到它们，所以一起记下来，
        # 由 present() 用渲染视口复现 —— 战斗区弹幕飞出边框就是因为漏了这个。
        # entity=True：登记到「战斗区实体层」（画布下半之上、弹幕之下），回放顺序
        # 由 present() 决定（见 display.GpuPresenter.present）。
        # alpha < 255 / add=True 才升级成 texa 指令：整体透明度与加法混合都交给
        # 显卡（SDL 的 texture alpha / blend mode），CPU 不必为淡入淡出抠副本。
        rect = _dest_scaled(dest, self.scale)
        clip_rect = None if clip is None else scale_rect(clip, self.scale)
        if alpha < 255 or add:
            op = ("texa", surface, rect, clip_rect,
                  max(0, min(255, int(alpha))), 2 if add else 1)
        else:
            op = ("tex", surface, rect, clip_rect)
        if fg:
            self.ops_fg.append(op)
        elif over:
            self.ops_over.append(op)
        elif entity:
            self.ops_entity.append(op)
        else:
            self.ops.append(op)

    def texture_top(self, surface, dest, alpha=255, clip=None):
        """登记「压在所有图层之上」的贴图指令，可带整体透明度

        与 texture() 只差回放时机：present() 在 1x 画布与高分辨率图层之后才回放
        这一层，所以符卡宣言立绘能盖住 HUD，而不是被 HUD 盖住。alpha 交给显卡
        调制（SDL 的 texture alpha），CPU 不碰像素 —— 原先每帧给 1728x1728 的
        立绘贴进 2880x2160 的高分辨率图层要 5.3ms，现在只剩一条指令。
        """
        self.ops_top.append(
            ("texa", surface,
             _dest_scaled(dest, self.scale),
             None if clip is None else scale_rect(clip, self.scale),
             max(0, min(255, int(alpha)))))

    def __len__(self):
        return (len(self.ops) + len(self.ops_entity) + len(self.ops_over)
                + len(self.ops_top) + len(self.ops_fg))


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
                if getattr(surface, "hi_dynamic", False):
                    # 复用的面板（hires.scratch_panel）：还是那块表面，但像素每帧都变，
                    # 命中缓存也必须重传一次，否则显卡上留着的还是第一帧的内容。
                    entry[1].update(surface)
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
        # 「按别的渲染倍率准备好的表面」换算到当前倍率后的结果（见 _at_render_factor）
        self._factor_cache = {}

    @classmethod
    def create(cls, size):
        """按窗口像素格式建画布（保留 HiResCanvas 那套高分辨率图层字段）"""
        canvas = cls(size).convert_alpha()
        canvas.hires_factor = 1
        canvas.hi = None
        canvas._hi_prev = None
        canvas._hi_cur = None
        canvas._hi_frame = None
        canvas._hi_rects = []
        canvas._hi_prev_rects = []
        canvas.cache = SurfaceCache()
        canvas.gpu = GpuLayer()
        canvas._gpu_pending = False
        canvas._factor_cache = {}
        return canvas

    # --- 每帧开关 ---

    def begin_gpu_frame(self, scale, gpu_available):
        """帧首：重置本帧的显卡指令（scale=渲染倍率，gpu_available=显卡路径是否可用）

        指令坐标写的是「图层空间」（逻辑坐标 x 渲染倍率），回放时的 layer_size 则取自
        高分辨率图层，两者必须是同一个倍率，所以实际生效的以画布的高分辨率倍率为准。
        关掉高分辨率图层时它是 1（例如 TOUHOU_HIRES=0 的对比模式）：这时再按传入的
        渲染倍率记坐标，HUD 面板与弹幕就会被换算两次、整体错位到画面外。
        """
        self.gpu.begin(self.hires_factor, gpu_available and _enabled)
        # 帧首归还上一帧借出去的复用面板（hires.scratch_panel）
        hires.reset_scratch(self)
        if self.gpu.enabled:
            # 显卡层是叠在 1x 画布「下面」的，所以开了显卡路径以后画布不再是「整幅
            # 画面」，只是画在显卡层之上的一层。这样每帧就必须从干净状态开始 ——
            # 否则上一个界面留在画布上的像素（设置页的调节条 / 分段按钮等）会继续
            # 透出来（从可退出界面按 Esc 返回时的「图像残留」）。
            # 开销实测 0.06ms/帧。
            pygame.Surface.fill(self, (0, 0, 0, 0))

    def gpu_ops(self):
        return self.gpu.ops if self.gpu.enabled else ()

    def gpu_ui_ops(self):
        return self.gpu.ops_ui if self.gpu.enabled else ()

    def gpu_over_ops(self):
        """弹幕那一层（画布之上、高分辨率图层之下）的显卡指令"""
        return self.gpu.ops_over if self.gpu.enabled else ()

    def gpu_entity_ops(self):
        """战斗区实体那一层（画布下半之上、弹幕之下）的显卡指令"""
        return self.gpu.ops_entity if self.gpu.enabled else ()

    def gpu_top_ops(self):
        """最上层（压住 HUD 的高清贴图，如符卡宣言立绘）的显卡指令"""
        return self.gpu.ops_top if self.gpu.enabled else ()

    def gpu_fg_ops(self):
        """战斗区前景层（画布下半之上、高分辨率图层之下）的显卡指令

        弹幕之上的符卡演出 / 遮挡 / 激光（Livid 的黑幕、Storm 的蓄力压暗、贯穿大
        激光、日核弹）原本直接画在 1x 画布的「后半」上，和弹幕挤在同一个顺序里。
        转换后单独占一层：回放位置在画布下半之后、HUD 之前，既画得清楚，又不会压
        住 HUD。回放顺序见 display.GpuPresenter.present。
        """
        return self.gpu.ops_fg if self.gpu.enabled else ()

    # --- 显卡优先的绘制 ---

    def fill_gpu(self, color, rect=None):
        """铺底色：有显卡就交给显卡填矩形，否则落回画布"""
        if not self.gpu.enabled:
            return self.fill(color, rect)
        if rect is None:
            w, h = pygame.Surface.get_size(self)
            rect = (0, 0, w, h)
        self.gpu.fill(color, rect, clip=self._canvas_clip())
        return pygame.Rect(_rect_tuple(rect))

    def blit_gpu(self, source, dest, area=None, alpha=255):
        """贴一张「已经准备好的图」：背景 / 图标 / 预烤面板。

        没有显卡时退回画布 —— 带倍率标记的表面会进高分辨率图层，清晰度一致，
        只是合成仍在 CPU 上做。

        alpha < 255 时整层不透明度交给显卡调制（界面进场时的错位淡入用），
        CPU 端不再为淡入淡出抠半透明副本；默认 255 与原先的绘制完全一致。
        """
        return self._blit_gpu_layer(source, dest, area, over=False, alpha=alpha)

    def blit_gpu_bg(self, source, dest, hole):
        """贴一整幅背景，但把 hole 那块矩形让给下层（战斗区）。

        战斗区的底面由显卡画在更下面（present() 先画地面、再回放显卡指令），整幅
        不透明地贴上去会把地面整个盖掉。所以按 hole 的四条边把这一幅拆成「上 / 下 /
        左 / 右」四条带分别裁剪着画：覆盖范围与「整幅贴到 1x 画布、战斗区再被关卡
        底衬盖掉」完全一致（那片像素两条路径下都看不见），但这一幅再也不必经过 1x
        画布 —— 既不糊一次，也省掉每帧一次 960x720 的 CPU blit。

        没有显卡时原样落回画布；万一拿到的是倍率图（显卡不可用但高分辨率图层还开着），
        先按 1x 缩回来再贴，免得把 2880x2160 的一大块直接糊到画布左上角。
        """
        if not self.gpu.enabled:
            if getattr(source, "hi_scale", 1) != 1:
                source = hires.rescale(source, 1)
            return self.blit(source, _int_dest(dest))
        source = self._at_render_factor(source)
        w, h = pygame.Surface.get_size(self)
        hx, hy, hw, hh = _rect_tuple(hole)
        for band in ((0, 0, w, hy), (0, hy + hh, w, h - hy - hh),
                     (0, hy, hx, hh), (hx + hw, hy, w - hx - hw, hh)):
            if band[2] > 0 and band[3] > 0:
                self.gpu.texture(source, dest, clip=band)
        x, y = _dest_tuple(dest)
        return pygame.Rect(int(round(x)), int(round(y)), w, h)

    def blit_gpu_over(self, source, dest, area=None, alpha=255, add=False):
        """贴到「画布之上、高分辨率图层之下」那一层（战斗区弹幕用）。

        战斗内容是交错的（见文件头说明），弹幕必须压过敌机与自机、又要被符卡前景
        遮罩与 HUD 盖住，所以单独占一层。没有显卡路径时与 blit_gpu 一样落回画布，
        绘制顺序因此在两种路径下完全一致。
        """
        return self._blit_gpu_layer(source, dest, area, over=True,
                                    alpha=alpha, add=add)

    def blit_gpu_fg(self, source, dest, area=None, alpha=255, add=False):
        """贴到「战斗区前景」那一层（画布下半之上、高分辨率图层之下）

        和 blit_gpu_over 同源，只差回放位置：在画布下半（弹幕 / 自机判定点 / 自机
        C 技能 / 符卡演出）之后、HUD 之前。所以「弹幕之上的符卡遮挡 / 激光 / 压暗」
        贴在这里既能盖住弹幕，又不会压住 HUD，和它原来在画布后半里的顺序一模一样。
        没有显卡路径时和 blit_gpu 一样落回画布，绘制顺序与旧路径完全一致。
        """
        return self._blit_gpu_layer(source, dest, area, over=False, fg=True,
                                    alpha=alpha, add=add)

    def blit_gpu_entity(self, source, dest, area=None, alpha=255, add=False):
        """贴到「战斗区实体层」：画布下半之上、弹幕之下（敌机 / Boss / 自机 / 掉落物）。

        这些实体原先画在 1x 画布上、跟着整幅画面一起被放大（48px 的 Boss 贴图在
        2x 输出下就是 96 个模糊像素）。改由显卡按渲染倍率原生绘制后，与弹幕、文字
        是同一清晰度。层级顺序与旧版一致：实体都在这层里按绘制顺序排（敌机 -> Boss
        -> 掉落物 -> 自机），整层压在 1x 画布前半（关卡背景 / 符卡背景 / 关卡特效）
        之上、被弹幕与画布后半（判定点 / C技能 / 符卡前景 / HUD）盖住
        （回放顺序见 display.GpuPresenter.present）。
        没有显卡路径时落回画布 —— 那种情况下渲染倍率也是 1x，观感与旧版相同。
        """
        return self._blit_gpu_layer(source, dest, area, over=False, entity=True,
                                    alpha=alpha, add=add)

    def fill_gpu_ui(self, color, rect):
        """在「1x 画布之上、高分辨率图层之下」填一块纯色 —— HUD 面板底板用。

        这块底板是一整条 334x720 的恒定半透明色：原先画在高分辨率图层上，等于
        每帧都要把 2.2M 像素（8.8MB）重新传一遍显卡，而且它横跨整个屏幕高度，
        把其余标脏点的包围盒撑成整屏。改成显卡直接填矩形后既不用传，边缘也比
        1x 放大更干净（和原来「画在高分辨率图层上」的观感一致）。
        没有显卡路径时退回高分辨率图层，与旧行为完全相同。
        """
        if self.gpu.enabled:
            self.gpu.fill(color, rect, clip=self._canvas_clip(), ui=True)
            return pygame.Rect(_rect_tuple(rect))
        return self.hi_rect(color, rect)

    def fill_gpu_fg(self, color, rect):
        """在「战斗区前景」层铺一块纯色（黑幕 / 压暗 / 舞台色罩）

        纯色块和渲染倍率无关（放大后还是同一个颜色、没有边缘），所以它不需要按倍率
        出图 —— 需要的只是**顺序**：弹幕之上的遮挡要盖住弹幕、盖住同层的符卡演出，
        又不能压住 HUD。整屏面板每帧重建反而要几十 MB 的贴图，纯色走显卡的矩形填充
        最省。没有显卡路径时退回高分辨率图层的纯色（与 fill_gpu_ui 同一套路）。
        """
        if self.gpu.enabled:
            self.gpu.fill(color, rect, clip=self._canvas_clip(), fg=True)
            return pygame.Rect(_rect_tuple(rect))
        return self.hi_rect(color, rect)



    def blit_gpu_top(self, source, dest, alpha=255):
        """贴到「所有图层之上」那一层：符卡宣言整幅立绘这类要压住 HUD 的高清图。

        alpha 由显卡调制（0-255），所以逐帧淡入淡出不再需要 CPU 端复制一份半透明
        副本。没有显卡路径时退回画布 blit（此时用表面级 alpha 表现，画面一致）。
        """
        if self.gpu.enabled:
            source = self._at_render_factor(source)
            self.gpu.texture_top(source, dest, alpha, clip=self._canvas_clip())
            x, y = _dest_tuple(dest)
            k = max(1, self.hires_factor)
            return pygame.Rect(int(x), int(y),
                               pygame.Surface.get_width(source) // k,
                               pygame.Surface.get_height(source) // k)
        source.set_alpha(None if alpha >= 255 else alpha)
        return self.blit(source, _int_dest(dest))

    def _blit_gpu_layer(self, source, dest, area, over, entity=False,
                        alpha=255, add=False, fg=False):
        # 往上走显卡的两条路保留 dest 的小数部分（取整交给图层空间，见 _dest_scaled）；
        # 落回画布的几条路只吃整数坐标，所以在这里取整。
        if not self.gpu.enabled or area is not None:
            return self._blit_canvas(source, _int_dest(dest), area, alpha, add,
                                     downscale=entity)
        # 倍率对不齐的旧图（改渲染倍率前准备好的贴图 / 面板）在这里换算到当前倍率，
        # 仍然贴进它自己的那一层 —— 不能退回画布，见 _at_render_factor
        source = self._at_render_factor(source)
        self.gpu.texture(source, dest, over=over, entity=entity, fg=fg,
                         clip=self._canvas_clip(), alpha=alpha, add=add)
        k = max(1, int(self.hires_factor))
        return pygame.Rect(int(round(_dest_tuple(dest)[0])),
                           int(round(_dest_tuple(dest)[1])),
                           pygame.Surface.get_width(source) // k,
                           pygame.Surface.get_height(source) // k)

    def _blit_canvas(self, source, dest, area, alpha, add, downscale=False):
        """落回画布的 blit：alpha 用表面级透明度表现（用完还原，不动原表面）

        downscale：实体层专用的兜底。显卡层没开但高分辨率图层还开着时（对比模式
        TOUHOU_UI_GPU=0），实体贴图仍是倍率图，直接 blit 会被画布送进高分辨率图层
        —— 那一层在弹幕与 HUD 之上，实体就跑到弹幕前面去了。这类贴图先缩回 1x
        再贴，与旧版（贴图本来就是 1x）逐像素一致。
        """
        flags = pygame.BLEND_ADD if add else 0
        if downscale and getattr(source, "hi_scale", 1) != 1:
            source = hires.rescale(source, 1)
        if alpha >= 255:
            return self.blit(source, dest, area, flags)
        prev = source.get_alpha()
        source.set_alpha(alpha)
        try:
            return self.blit(source, dest, area, flags)
        finally:
            source.set_alpha(prev)

    def _at_render_factor(self, source):
        """把「按别的渲染倍率准备好的表面」换算到当前渲染倍率（换算结果缓存）

        改渲染倍率时，各处按倍率作键的贴图 / 预烤面板缓存里，旧倍率那一份都还留着
        （界面把整幅背景存在自己身上、子弹把旋转贴图存在实例上，改倍率时都不会从头
        重来）。拿旧倍率的图直接贴会整体错位，所以原先的做法是退回 1x 画布；可画布
        是画在显卡指令层「之上」的，退回画布等于把那一片整块盖掉 —— 文字 / 立绘 /
        面板都登记在指令层里，切完倍率就成片隐身（战斗区的实体层、弹幕层同理）。这里
        统一换算到当前倍率，仍旧贴回它自己那一层，层级与倍率就都对得上了。

        换算结果按（原表面, 倍率）缓存：一次倍率变更只多付一次缩放。
        """
        current = max(1, int(self.hires_factor))
        if getattr(source, "hi_scale", 1) == current:
            return source
        cache = self._factor_cache
        key = (id(source), current)
        entry = cache.get(key)
        if entry is not None and entry[0]() is source:
            return entry[1]
        converted = hires.rescale(source, current)
        if getattr(source, "hi_dynamic", False):
            # 复用面板（hires.scratch_panel）：还是那块表面，像素每帧都变，换算结果
            # 存下来下一帧就是旧内容，所以这类只换算不缓存。
            return converted
        if len(cache) > 2048:
            cache = {k: v for k, v in cache.items() if v[0]() is not None}
            self._factor_cache = cache
        cache[key] = (weakref.ref(source), converted)
        return converted

    def _canvas_clip(self):
        """当前生效的裁剪框（逻辑坐标）；整幅画布时返回 None

        显卡指令是在画布之外回放的，画布上的 set_clip 管不到它们，所以登记指令时
        顺手记下裁剪，由 present() 用渲染视口复现（见 display._draw_ops）。
        """
        clip = self.get_clip()
        if clip is None:
            return None
        w, h = pygame.Surface.get_size(self)
        if (clip.x, clip.y, clip.width, clip.height) == (0, 0, w, h):
            return None
        return (clip.x, clip.y, clip.width, clip.height)

    def clear_canvas(self):
        """把 1x 画布整块清成透明（忽略裁剪），供「画布切两半」用。

        战斗区在弹幕之前切一刀：前半已经交给显卡当「弹幕之下」那一层，画布要清干净
        再继续画上半层，否则前半的内容会重复叠在弹幕之上。
        """
        clip = self.get_clip()
        self.set_clip(None)
        pygame.Surface.fill(self, (0, 0, 0, 0))
        self.set_clip(clip)

    # --- 预烤面板 ---

    def blit_baked(self, key, dest, logical_size, build, alpha=255):
        """把一块面板按渲染倍率烤成图并贴到 dest（逻辑坐标）。

        build(target, k)：target 是这块面板的高分辨率表面，用上面的 bake_* 助手
        在它上面作画即可（key 必须包含所有会影响画面的参数，否则会取到旧图）。
        alpha < 255 时整块面板一起淡（界面进场用；预烤结果仍按原参数缓存复用）。
        """
        surf = self.baked(key, logical_size, build)
        if surf is None:
            return None
        x, y = _dest_tuple(dest)
        self.blit_gpu(surf, (int(x), int(y)), alpha=alpha)
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
