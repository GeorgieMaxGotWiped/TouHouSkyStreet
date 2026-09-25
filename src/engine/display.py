# 东方天空街 ~ Touhou Sky Street
# 显示管理：DPI 感知、输出分辨率与缩放模式、GPU 呈现
#
# 游戏内部逻辑分辨率固定为 960x720（所有绘制代码与素材尺寸都按它写死）。
# 本模块只解决「把这张 960x720 的画面以多大尺寸、什么方式放到窗口上」：
#   1) 声明 DPI 感知，避免 Windows 在高 DPI 缩放下把已有画面再拉伸一次（二次模糊）；
#   2) 借用 SCALED 窗口背后的 SDL renderer，让显卡完成放大，替代 CPU 的
#      smoothscale（实测 3 倍放大 CPU 约 15ms/帧，GPU 路径约 1ms/帧）。
# 另有一类「分辨率无关」图层（目前是伪3D 地面）不走这条路径：它们按渲染倍率
# 直接在窗口上原生绘制，再由 1x 画面叠加在上层（战斗区在 CPU 帧上抠空）。
# 这样地面是真实的高分辨率，UI/文字与实体仍是 960x720 放大。

import os
import sys
import weakref

import pygame

from src.engine import painter


# --- 环境（必须在 pygame.init() 之前设置）---

def configure_environment():
    """设置 SDL 环境变量：需在 SDL 初始化之前调用（见 game.py 顶部）。"""
    if sys.platform == "win32":
        # per-monitor-v2 DPI 感知：桌面分辨率按物理像素上报（3840x2160）
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
    # 渲染缩放过滤：0=最近邻 1=线性 2=各向异性；放大用线性
    os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")


def enable_dpi_awareness():
    """直接调用 Win32 API 声明 DPI 感知（与上面的环境变量互为保险）。"""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return True
    except Exception:
        pass
    try:
        import ctypes
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return True
    except Exception:
        pass
    try:
        import ctypes
        return bool(ctypes.windll.user32.SetProcessDPIAware())
    except Exception:
        return False


# --- 尺寸计算 ---

def get_desktop_size():
    """主显示器的物理分辨率；失败时返回 (0, 0)"""
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes:
            return int(sizes[0][0]), int(sizes[0][1])
    except Exception:
        pass
    try:
        info = pygame.display.Info()
        return int(info.current_w), int(info.current_h)
    except Exception:
        return 0, 0


def fit_scale(avail_w, avail_h, logical_size, mode):
    """可用区域 -> 画面缩放倍数。integer 模式只按整数倍放大（可能留更大黑边）。"""
    lw, lh = logical_size
    if avail_w <= 0 or avail_h <= 0 or lw <= 0 or lh <= 0:
        return 1.0
    fit = min(avail_w / float(lw), avail_h / float(lh))
    if mode == "integer" and fit >= 1.0:
        nearest = int(round(fit))
        # 容差：桌面尺寸带零头时（如 3839x2159）仍按最近的整数倍处理
        if nearest >= 1 and abs(fit - nearest) <= 0.02:
            return float(nearest)
        return float(int(fit))
    return fit


def present_rect(window_size, logical_size, mode):
    """计算画面在窗口中的目标矩形（窗口物理像素）与缩放倍数。

    返回 (pygame.Rect, scale)：画面等比缩放后居中，四周由调用方填黑边。
    """
    win_w = max(1, int(window_size[0]))
    win_h = max(1, int(window_size[1]))
    scale = fit_scale(win_w, win_h, logical_size, mode)
    w = max(1, int(round(logical_size[0] * scale)))
    h = max(1, int(round(logical_size[1] * scale)))
    return pygame.Rect((win_w - w) // 2, (win_h - h) // 2, w, h), scale


# --- GPU 呈现 ---

class GpuPresenter:
    """通过 SCALED 窗口背后的 SDL renderer 做 GPU 缩放呈现。

    ok=False 表示当前后端不支持（例如 dummy 视频驱动），调用方回退到 CPU 缩放。
    """

    def __init__(self, logical_size):
        self.logical_size = (int(logical_size[0]), int(logical_size[1]))
        self.ok = False
        self.renderer = None
        self.texture = None
        # 高分辨率图层纹理（文字/立绘/面板）与它的尺寸
        self._ui_texture = None
        self._ui_size = None
        # 「弹幕之下」那一层：战斗区在弹幕之前切一刀，前半张画布先收到这里
        self._lower_texture = None
        self._lower_size = None
        self._lower_ready = False
        # 地面/洞壁贴图纹理：id(地面) -> (weakref, 地面纹理, 洞壁纹理)。
        # 这些纹理属于当前 renderer，随 presenter 一起重建，因此不必单独失效。
        self._floor_tex = {}
        try:
            from pygame._sdl2 import video as video_module
            window = video_module.Window.from_display_module()
            renderer = video_module.Renderer.from_window(window)
            # 关闭 SDL 自带的逻辑分辨率缩放：目标矩形由 present_rect 精确计算，
            # 这样「整数倍 / 填充」两种模式才能得到完全可控的结果。
            renderer.logical_size = (0, 0)
            texture = video_module.Texture(renderer, self.logical_size, streaming=True)
            # 逐像素 alpha 混合：战斗区抠空后，下层显卡直绘的地面才能透出来
            texture.blend_mode = 1
            self.renderer = renderer
            self.texture = texture
            # 静态图（背景 / 图标 / 预烤面板）的 GPU 纹理缓存
            self._tex_cache = painter.TextureCache(renderer)
            self.ok = True
        except Exception as e:
            print(f"[Display] GPU present unavailable, fallback to CPU scaling: {e}")

    def _floor_textures(self, floor):
        """地面/洞壁贴图上传为 GPU 纹理（与几何无关，每张地面只需上传一次）"""
        key = id(floor)
        entry = self._floor_tex.get(key)
        if entry is not None and entry[0]() is floor:
            return entry[1], entry[2]
        from pygame._sdl2 import video as video_module
        tex_floor = video_module.Texture.from_surface(self.renderer, floor.tile)
        tex_wall = video_module.Texture.from_surface(self.renderer, floor.wall_tile)
        tex_floor.blend_mode = 1
        tex_wall.blend_mode = 1
        if len(self._floor_tex) > 16:
            # 丢掉已释放的地面，避免访问过的关卡一直占着显存
            self._floor_tex = {k: v for k, v in self._floor_tex.items()
                               if v[0]() is not None}
        self._floor_tex[key] = (weakref.ref(floor), tex_floor, tex_wall)
        return tex_floor, tex_wall

    def _clear(self):
        """清屏（四周黑边）：地面绘制会改 draw_color，所以这里显式指定"""
        self.renderer.draw_color = (0, 0, 0, 255)
        self.renderer.clear()

    def _ui_texture_for(self, size):
        """高分辨率图层纹理（与 1x 画面同宽高比，只是像素更多）"""
        if self._ui_texture is not None and self._ui_size == size:
            return self._ui_texture
        from pygame._sdl2 import video as video_module
        texture = video_module.Texture(self.renderer, size, streaming=True)
        texture.blend_mode = 1
        self._ui_texture = texture
        self._ui_size = size
        return texture

    def warm_texture(self, surface):
        """提前把一张静态贴图传成显卡纹理（载入界面预热用）

        符卡宣言立绘有 1728x1728（11.9MB），第一次上屏时 Texture.from_surface
        要花 3.5ms，正好落在开符那一帧上。纹理缓存按表面对象认人，载入界面与
        战斗用同一份 renderer，所以在这里先传一次就够了。
        """
        cache = getattr(self, "_tex_cache", None)
        if cache is None or surface is None:
            return False
        return cache.get(surface) is not None

    def capture_lower(self, surface):
        """把当前 1x 画布收成「弹幕之下」那一层（随后调用方会清空画布继续画上层）

        做成「上传即收下」而不是「复制一张留到帧末」：少一次整幅 memcpy，画布上的
        像素直接进纹理。没有显卡呈现时不会被调用。
        """
        size = surface.get_size()
        if self._lower_texture is None or self._lower_size != size:
            from pygame._sdl2 import video as video_module
            texture = video_module.Texture(self.renderer, size, streaming=True)
            texture.blend_mode = 1
            self._lower_texture = texture
            self._lower_size = size
        self._lower_texture.update(surface)
        self._lower_ready = True

    def present(self, surface, dst_rect, floor=None, battle_rect=None,
                ui=None, ui_area=None, gpu_ops=None, layer_size=None,
                gpu_over_ops=None, gpu_top_ops=None, gpu_ui_ops=None,
                gpu_entity_ops=None, gpu_fg_ops=None):
        """上传逻辑画面并用显卡缩放到 dst_rect（renderer 内部完成 present）。

        给了 floor 时先在 battle_rect 处用显卡原生绘制地面（分辨率无关图层），
        再叠加 1x 画面：战斗区已在 CPU 帧上抠空，地面就从这层透出来。
        给了 ui 时最后叠加高分辨率图层（文字/立绘/面板），它按渲染倍率原生绘制，
        与 1x 画面共用同一个目标矩形，因此不会再有放大模糊。

        给了 gpu_ui_ops 时在 1x 画面与高分辨率图层之间再叠一层：HUD 面板底板这类
        恒定的大色块，画在高分辨率图层上等于每帧重传一遍，交给显卡填更省。

        给了 gpu_over_ops 时在「1x 画面」与「高分辨率图层」之间再叠一层：战斗区
        的弹幕（画布前半 = 地面/敌机/自机，画布后半 = 符卡前景/HUD，弹幕夹在中间）。

        给了 gpu_entity_ops 时在「画布前半」与弹幕之间再叠一层：战斗区的实体（敌机 /
        Boss / 自机 / 掉落物）按渲染倍率原生绘制。它们原先画在 1x 画布前半上，与
        弹幕、文字之间有清晰度落差；这一层的位置保证旧版的先后关系不变——整层压在
        画布前半（关卡背景 / 符卡背景 / 关卡特效）之上，被弹幕与画布后半（判定点 /
        C技能 / 符卡前景 / HUD）盖住。

        给了 gpu_top_ops 时最后再叠一层：压在所有内容之上的贴图（符卡宣言立绘），
        带逐指令 alpha 调制，所以淡入淡出不用在 CPU 上做。
        """
        if floor is not None and battle_rect is not None:
            tex_floor, tex_wall = self._floor_textures(floor)
            self._clear()
            floor.draw_gpu(self.renderer, battle_rect, tex_floor, tex_wall)
        else:
            self._clear()
        # 显卡原生绘制层（Painter 登记的本帧指令）：在 1x 画面之前，
        # 于高分辨率图层坐标系里按渲染倍率原样绘制
        if gpu_ops and layer_size:
            self._draw_ops(gpu_ops, dst_rect, layer_size)
        # 画布前半（弹幕之下）：地面 / 敌机 / 自机 / 掉落物
        if self._lower_ready:
            self._lower_texture.draw(dstrect=dst_rect)
            self._lower_ready = False
        # 战斗区实体（敌机 / Boss / 自机 / 掉落物）：显卡按渲染倍率原生绘制
        if gpu_entity_ops and layer_size:
            self._draw_ops(gpu_entity_ops, dst_rect, layer_size)
        # 弹幕
        if gpu_over_ops and layer_size:
            self._draw_ops(gpu_over_ops, dst_rect, layer_size)
        self.texture.update(surface)
        self.texture.draw(dstrect=dst_rect)
        # 战斗区前景（弹幕之上的符卡遮挡 / 激光 / 压暗）：画布下半之后、HUD 之前
        if gpu_fg_ops and layer_size:
            self._draw_ops(gpu_fg_ops, dst_rect, layer_size)
        # 高分辨率图层之下的常驻色块（HUD 面板底板）
        if gpu_ui_ops and layer_size:
            self._draw_ops(gpu_ui_ops, dst_rect, layer_size)
        # ui_area 为 None = 本帧高分辨率图层是空的（上一帧的残留已在 begin_frame 清掉），
        # 此时连上传都不必做
        if ui is not None and ui_area is not None:
            # ui_area 可能是矩形（整体上传）或矩形列表（逐块上传）：标脏点散在
            # 屏幕四角时，包围盒等于整屏，逐块传才只付真正画过的像素
            areas = ui_area if isinstance(ui_area, list) else (ui_area,)
            full = ui.get_rect()
            texture = None
            for area in areas:
                area = area.clip(full)
                if area.width <= 0 or area.height <= 0:
                    continue
                if texture is None:
                    texture = self._ui_texture_for(ui.get_size())
                # 注意：Texture.update(surface, area) 会拿「源表面左上角」当区域原点，
                # 所以这里传与区域同尺寸的子表面，让源原点与区域原点对齐
                texture.update(ui.subsurface(area), area)
            if texture is not None:
                # 注意：这里必须整幅叠加，不能只叠加脏区那一块——脏区对应的目标矩形
                # 只能取整，采样相位会跟着变，清晰文字会整体错开半个像素（实测可见）。
                texture.draw(dstrect=dst_rect)
        # 最上层：符卡宣言立绘这类要压住 HUD 的高清贴图（带显卡端 alpha 调制）
        if gpu_top_ops and layer_size:
            self._draw_ops(gpu_top_ops, dst_rect, layer_size)
        self.renderer.present()


    # --- 显卡指令回放 ---

    def _draw_ops(self, ops, dst_rect, layer_size):
        """在窗口上回放本帧登记的显卡指令。

        ops 里的坐标位于「高分辨率图层」空间（逻辑坐标 x 渲染倍率），dst_rect 是
        画面在窗口中的目标矩形，两者之间可能还有一次整体缩放（输出分辨率与渲染
        倍率不一定相等），因此按下式换算成窗口像素。

        指令若带裁剪框（登记时画布上生效的 set_clip，例如战斗区那个框），改用渲染
        视口来裁：SDL 的视口既是裁剪框、又是坐标系原点，所以设好视口以后，后续坐标
        都要减去视口原点（见 _use_clip）。
        """
        lw, lh = layer_size
        if lw <= 0 or lh <= 0:
            return
        fx = dst_rect.width / float(lw)
        fy = dst_rect.height / float(lh)
        active = None          # 当前已经设好的裁剪（None = 整窗视口，视口原点 0,0）
        ox = oy = 0
        blend = False          # 是否已把渲染器切到 alpha 混合（用完必须还原）
        # 混合模式是纹理自己的属性：同一张纹理可能这帧走普通混合、下帧走加法混合
        # （亡灵展品的发光贴图），所以按「纹理 + 模式」记，变了才写回去。
        blend_tex = None
        blend_mode = 1
        for op in ops:
            clip = op[3] if len(op) > 3 else None
            if clip != active:
                active = clip
                ox, oy = self._use_clip(clip, dst_rect, fx, fy)
            if op[0] == "fill":
                color, rect = op[1], op[2]
                alpha = color[3] if len(color) >= 4 else 255
                # 半透明填充得显式打开混合：渲染器的 draw_blend_mode 默认是 NONE，
                # 这时 fill_rect 会把 (r,g,b,a) 当成不透明色盖上去，a 被整个丢掉
                # （HUD 面板底板那种 128 的底色就会糊成纯色）。
                want_blend = alpha < 255
                if want_blend != blend:
                    blend = want_blend
                    self.renderer.draw_blend_mode = 1 if want_blend else 0
                self.renderer.draw_color = (color[0], color[1], color[2], alpha)
                target = pygame.Rect(dst_rect.x + int(round(rect[0] * fx)) - ox,
                                     dst_rect.y + int(round(rect[1] * fy)) - oy,
                                     max(1, int(round(rect[2] * fx))),
                                     max(1, int(round(rect[3] * fy))))
                self.renderer.fill_rect(target)
            elif op[0] in ("tex", "texa"):
                surface, rect = op[1], op[2]
                texture = self._tex_cache.get(surface)
                if texture is None:
                    continue
                # 表面的真实像素尺寸已经是「逻辑尺寸 x 渲染倍率」，
                # 与 rect 所在的图层空间一致，这里只需再做一次窗口换算
                sw = pygame.Surface.get_width(surface)
                sh = pygame.Surface.get_height(surface)
                target = pygame.Rect(dst_rect.x + int(round(rect[0] * fx)) - ox,
                                     dst_rect.y + int(round(rect[1] * fy)) - oy,
                                     max(1, int(round(sw * fx))),
                                     max(1, int(round(sh * fy))))
                # texa 带整体透明度（符卡宣言立绘的淡入淡出、召唤物的淡入淡出）：
                # 直接交给显卡调制，省掉 CPU 端逐帧抠半透明副本。tex 明确写回 255，
                # 免得同一张纹理被上一条 texa 指令留下的 alpha 影响。
                # op[5] 是混合模式（1 = 逐像素 alpha，2 = 加法），缺省按 alpha 混合。
                mode = op[5] if len(op) > 5 else 1
                if mode != blend_mode or texture is not blend_tex:
                    texture.blend_mode = mode
                    blend_tex, blend_mode = texture, mode
                texture.alpha = op[4] if len(op) > 4 else 255
                texture.draw(dstrect=target)
        if blend:
            self.renderer.draw_blend_mode = 0
        if active is not None:
            self._use_clip(None, dst_rect, fx, fy)

    def _use_clip(self, clip, dst_rect, fx, fy):
        """把「图层空间的裁剪框」设成渲染视口，返回视口原点（窗口像素）

        没有裁剪时还原成整窗视口。SDL 的视口同时是裁剪框与坐标原点：设了它以后
        texture.draw / fill_rect 的坐标都相对视口左上角，所以调用方要减去返回的
        原点（否则整层会被平移出画面）。
        """
        if clip is None:
            self.renderer.set_viewport(None)
            return 0, 0
        rect = pygame.Rect(dst_rect.x + int(round(clip[0] * fx)),
                           dst_rect.y + int(round(clip[1] * fy)),
                           max(1, int(round(clip[2] * fx))),
                           max(1, int(round(clip[3] * fy))))
        rect = rect.clip(dst_rect)
        self.renderer.set_viewport(rect)
        return rect.x, rect.y
