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

    def present(self, surface, dst_rect, floor=None, battle_rect=None,
                ui=None, ui_area=None, gpu_ops=None, layer_size=None):
        """上传逻辑画面并用显卡缩放到 dst_rect（renderer 内部完成 present）。

        给了 floor 时先在 battle_rect 处用显卡原生绘制地面（分辨率无关图层），
        再叠加 1x 画面：战斗区已在 CPU 帧上抠空，地面就从这层透出来。
        给了 ui 时最后叠加高分辨率图层（文字/立绘/面板），它按渲染倍率原生绘制，
        与 1x 画面共用同一个目标矩形，因此不会再有放大模糊。
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
        self.texture.update(surface)
        self.texture.draw(dstrect=dst_rect)
        # ui_area 为 None = 本帧高分辨率图层是空的（上一帧的残留已在 begin_frame 清掉），
        # 此时连上传都不必做
        if ui is not None and ui_area is not None:
            area = ui_area.clip(ui.get_rect())
            if area.width > 0 and area.height > 0:
                texture = self._ui_texture_for(ui.get_size())
                # 注意：Texture.update(surface, area) 会拿「源表面左上角」当区域原点，
                # 所以这里传与区域同尺寸的子表面，让源原点与区域原点对齐
                texture.update(ui.subsurface(area), area)
                # 注意：这里必须整幅叠加，不能只叠加脏区那一块——脏区对应的目标矩形
                # 只能取整，采样相位会跟着变，清晰文字会整体错开半个像素（实测可见）。
                texture.draw(dstrect=dst_rect)
        self.renderer.present()


    # --- 显卡指令回放 ---

    def _draw_ops(self, ops, dst_rect, layer_size):
        """在窗口上回放本帧登记的显卡指令。

        ops 里的坐标位于「高分辨率图层」空间（逻辑坐标 x 渲染倍率），dst_rect 是
        画面在窗口中的目标矩形，两者之间可能还有一次整体缩放（输出分辨率与渲染
        倍率不一定相等），因此按下式换算成窗口像素。
        """
        lw, lh = layer_size
        if lw <= 0 or lh <= 0:
            return
        fx = dst_rect.width / float(lw)
        fy = dst_rect.height / float(lh)
        for op in ops:
            if op[0] == "fill":
                _, color, rect = op
                if len(color) >= 4:
                    self.renderer.draw_color = (color[0], color[1], color[2], color[3])
                else:
                    self.renderer.draw_color = (color[0], color[1], color[2], 255)
                target = pygame.Rect(dst_rect.x + int(round(rect[0] * fx)),
                                     dst_rect.y + int(round(rect[1] * fy)),
                                     max(1, int(round(rect[2] * fx))),
                                     max(1, int(round(rect[3] * fy))))
                self.renderer.fill_rect(target)
            elif op[0] == "tex":
                _, surface, rect = op
                texture = self._tex_cache.get(surface)
                if texture is None:
                    continue
                # 表面的真实像素尺寸已经是「逻辑尺寸 x 渲染倍率」，
                # 与 rect 所在的图层空间一致，这里只需再做一次窗口换算
                sw = pygame.Surface.get_width(surface)
                sh = pygame.Surface.get_height(surface)
                target = pygame.Rect(dst_rect.x + int(round(rect[0] * fx)),
                                     dst_rect.y + int(round(rect[1] * fy)),
                                     max(1, int(round(sw * fx))),
                                     max(1, int(round(sh * fy))))
                texture.alpha = 255
                texture.draw(dstrect=target)
