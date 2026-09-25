# 伪3D洞穴地面+洞壁渲染
# - 地面：屏幕每行对应地面上一个固定深度，采样贴图对应行横向拉伸（横纹朝下）
# - 洞壁：屏幕每列对应洞壁上固定深度，采样墙纸（wall2.png）对应列纵向拉伸（竖纹朝侧），整体压暗
# - 尽头：墙壁与地面在远处保留一段宽度，中间留出远景开口，避免收束成一点/一线
# - 浓雾：远处雾饱和为纯背景色，遮断一切纹理与接缝
# - 无缝：贴图内容接缝在自然周期处（半图/换行），用窄带内容融合修复，滚动无跳变
# - 同步换行：地面与洞壁贴图周期不同，共享滚动统一在最小公倍数处换行，
#   避免换行瞬间某一侧因周期差产生瞬间“回退”

import pygame
import numpy as np
import math

# --- 可调参数 ---
HORIZON_RATIO = 0.39      # 地平线（灭点）在战斗区高度的比例
SCROLL_SPEED = 120.0      # 贴图向前滚动速度（贴图像素/秒）
FOG_START = 0.35          # 雾开始出现的距离（0=近 1=远）
FOG_FULL = 0.85           # 雾完全遮断的距离（到达后为纯背景色）
FOG_EXP = 1.6             # 雾随距离衰减的指数
PERSPECTIVE = 1.0         # 透视系数：1.0 = 底部贴图接近原始大小
WALL_DARK_ALPHA = 120     # 洞壁整体压暗程度（0 = 不暗，255 = 全黑）
TUNNEL_WIDTH = 1.6        # 通道宽度：1.0 = 与屏幕等宽，越大越宽
FAR_OPENING = 28          # 尽头开口大小（px 行距）：地面/洞壁在远处保留的宽度，越大开口越宽
FAR_DROP_GAIN = 1.5       # far-opening drop gain during view rise (0 = fixed, higher = more drop)
SEAM_BAND = 16            # 接缝修复带宽（px）：在内容接缝处做窄带融合，保留细节


# --- 本帧由显卡原生绘制的地面 ---
# 关卡绘制时登记（战斗区在 CPU 帧上抠空），呈现层绘制完当帧后取用并清空。
_gpu_floor_this_frame = None


def register_gpu_floor(floor):
    """登记本帧的地面改由显卡原生绘制"""
    global _gpu_floor_this_frame
    _gpu_floor_this_frame = floor


def take_gpu_floor():
    """取用并清空本帧登记的 GPU 地面（无则返回 None）"""
    global _gpu_floor_this_frame
    floor = _gpu_floor_this_frame
    _gpu_floor_this_frame = None
    return floor


class Pseudo3DFloor:
    """透视地面+洞壁渲染器，只负责战斗区域。"""

    # 引擎写入：新建地面默认采用的输出倍率（GPU 呈现时 = 设置的渲染倍率）
    default_scale = 1
    # 引擎写入：GPU 呈现可用（True 时地面改由显卡原生绘制，见 draw_gpu）
    gpu_active = False

    def __init__(self, texture_path, area_width, area_height, bg_color=(8, 12, 32),
                 horizon_ratio=HORIZON_RATIO, scroll_speed=SCROLL_SPEED,
                 wall_texture_path=None, floor_stretch=1.0, wall_stretch=1.0,
                 tunnel_width=TUNNEL_WIDTH, far_opening=FAR_OPENING,
                 far_drop_gain=FAR_DROP_GAIN, wall_align_to_floor=False,
                 scale=None):
        # scale = 输出像素相对「逻辑分辨率」的倍率。area_width/height 是逻辑尺寸，
        # 几何与贴图采样按逻辑尺寸计算，只有像素位置乘 scale（见 set_scale）。
        # 缺省取引擎写入的 default_scale：GPU 呈现时等于渲染倍率设置，否则 1。
        if scale is None:
            scale = Pseudo3DFloor.default_scale
        self.logical_w = int(area_width)
        self.logical_h = int(area_height)
        self.horizon_ratio = float(horizon_ratio)
        self.scale = max(1, int(scale))
        self.area_w = self.logical_w * self.scale
        self.area_h = self.logical_h * self.scale
        self.bg_color = bg_color
        self.scroll_speed = float(scroll_speed)
        # 视角高度：Boss开战等场景可让地平线上移，俯瞰战场。
        # view_rise / _base_horizon_L 一律用逻辑单位，输出像素量 = 逻辑量 * scale
        self._base_horizon_L = int(self.logical_h * horizon_ratio)
        self.horizon = self._base_horizon_L * self.scale
        self.cx = self.area_w / 2.0
        self.d_max = max(1, self.area_h - self.horizon)
        self.d_wall = self.d_max / tunnel_width   # 洞壁最近点对应的行距（越小通道越宽）
        self.scroll = 0.0
        self.base_speed = float(scroll_speed)
        self.speed_mult = 1.0
        self._ramp_from = 1.0
        self._ramp_target = 1.0
        self._ramp_t = 0.0
        self._ramp_dur = 0.0

        # 地面贴图：滚动换行方向（垂直）修复内容接缝，做成真正无缝
        floor_img = pygame.image.load(texture_path).convert_alpha()
        floor_period_src = Pseudo3DFloor._block_period(floor_img, "v")
        if floor_stretch and floor_stretch != 1.0:
            fw, fh = floor_img.get_size()
            # 朝远处（纵深方向）拉伸贴图，让地板不再显得扁
            floor_img = pygame.transform.smoothscale(
                floor_img, (fw, max(1, int(round(fh * floor_stretch)))))
        self.tile = self._make_tileable(floor_img, "v")
        self.tile_w, self.tile_h = self.tile.get_size()
        # 洞壁贴图：滚动换行方向（水平）修复内容接缝，做成真正无缝
        wall_path = wall_texture_path or texture_path
        wall_img = pygame.image.load(wall_path).convert_alpha()
        wall_period_src = Pseudo3DFloor._block_period(wall_img, "h")
        if wall_align_to_floor and floor_period_src and wall_period_src:
            # 令拉伸后的墙壁方块周期 = 地面方块周期（一一对应）
            wall_stretch = (floor_period_src * float(floor_stretch or 1.0)
                            / wall_period_src)
        if wall_stretch and wall_stretch != 1.0:
            ww, wh = wall_img.get_size()
            # 朝纵深方向拉伸洞壁贴图，让墙壁不再显得扁
            wall_img = pygame.transform.smoothscale(
                wall_img, (max(1, int(round(ww * wall_stretch))), wh))
        self.wall_tile = self._make_tileable(wall_img, "h")
        self.wall_w, self.wall_h = self.wall_tile.get_size()

        # 共享滚动换行周期：地面 tile_h 与洞壁 wall_w 不同，若在某一方的
        # 周期处换行，另一方会因周期差瞬间“回退”；统一在最小公倍数处
        # 换行，换行瞬间对双方都无缝。
        self._scroll_period = math.lcm(self.tile_h, self.wall_w)

        self._base_horizon = self.horizon
        self.view_rise = 0.0
        self.view_rise_from = 0.0
        self.view_rise_target = 0.0
        self.view_rise_t = 0.0
        self.view_rise_dur = 0.0
        self.tunnel_width = tunnel_width
        self.far_opening = far_opening
        self.far_drop_gain = far_drop_gain

        # 缩放目标面缓存：按尺寸复用同一张面。每帧的洞壁列/地面行条带
        # 尺寸固定，复用目标面既省下每帧上千张小 Surface 的分配，
        # 也大幅减少垃圾回收压力造成的掉帧毛刺
        self._wall_dst = {}
        self._row_dst = {}

        # wants_gpu_draw 由关卡绘制时写入：本帧确实要画地面
        # （Boss 符卡背景完全遮住时会跳过）。gpu_active 见类级开关。
        self.wants_gpu_draw = False
        self._geom_ver = 0          # 几何版本号，几何重建时自增

        # 几何待重建标记：地平线变了只置标记，等本帧确实要画地面时才重建
        # （符卡背景不透明时会完全遮住地面，此时关卡根本不画地面）
        self._geom_dirty = False
        self._rebuild_geometry()

    def _rebuild_geometry(self):
        """按当前地平线重建地面/洞壁几何与雾（视角抬升时随地平线更新）。

        几何与贴图采样一律在「逻辑分辨率」（area / scale）下计算，只有屏幕
        像素位置乘回 scale。这样同一相对屏幕位置对应的贴图坐标不随输出倍率
        变化：放大只是采样更细，构图与贴图密度保持不变。

        原实现把 K_floor = PERSPECTIVE*d_max² 直接建立在输出像素之上，而
        q = |x-cx|/cx 是归一化的，于是放大 F 倍会让贴图坐标同步推进 F 倍
        —— 洞壁重复周期数从 1x 的约 10 个变成 3x 的约 37 个，条纹明显变密。
        """
        F = float(self.scale)
        W_L = self.area_w / F
        H_L = self.area_h / F
        horizon_L = self.horizon / F
        cx_L = W_L / 2.0
        cx = int(self.cx)
        d_max = max(1.0, H_L - horizon_L)
        d_wall = d_max / self.tunnel_width   # 洞壁最近点对应的行距（越小通道越宽）
        d_far = min(self.far_opening, d_wall - 1)
        # View rise: far opening (end rectangle) drops with camera height,
        # keeping at least a strip of floor at the bottom (cap d_max - d_far - 2)
        drop = int(round(self.view_rise * self.far_drop_gain))
        drop = max(0, min(drop, int(d_max - d_far - 2)))
        self._exit_drop = drop
        exit_bottom_L = horizon_L + d_far + drop
        self.d_max = d_max
        self.d_wall = d_wall
        self.w_far = max(1, int(round(cx_L * d_far / d_wall)))   # 尽头开口半宽（逻辑 px）
        self._k_floor = PERSPECTIVE * d_max * d_max
        self._geom_ver += 1
        self._geom_dirty = False

        # 地面：每行预计算 深度 d、绘制半宽、贴图采样子段、透视采样系数 K_f/d
        # - 未满宽区域（d <= d_wall）取整张贴图行
        # - 满宽后（d > d_wall）取贴图行中央一段，随靠近不断放大并向外展开
        # v = K_f/d + scroll
        self.rows = []
        k_floor = self._k_floor
        half_tile = self.tile_w / 2.0
        for y in range(int(math.floor(exit_bottom_L * F)) + 1, self.area_h):
            d = y / F - horizon_L - drop
            if d <= 0:
                continue
            hw_virtual = cx_L * d / d_wall      # 未钳制的虚拟半宽（透视继续）
            half_w = max(1.0, min(cx_L, round(hw_virtual)))
            half_extent = min(half_tile, half_w * half_tile / max(hw_virtual, 1e-9))
            sub_x = max(0, int(round(half_tile - half_extent)))
            sub_w = max(1, min(self.tile_w, int(round(half_extent * 2))))
            if sub_x + sub_w > self.tile_w:
                sub_x = self.tile_w - sub_w
            self.rows.append((y, d, int(round(half_w * F)), k_floor / d, sub_x, sub_w))

        # 洞壁：每列预计算 列高度 H（该列洞壁延伸到地面线）、透视采样系数 K_w/q
        # q = |x - cx| / cx（0=正前方 1=屏幕边缘），K_w = K_f / d_wall
        # 中央开口宽度内不画洞壁（|x - cx| <= w_far 为远景开口）
        self.walls = []
        k_wall = k_floor / d_wall
        for x in range(self.area_w):
            q = abs(x / F - cx_L) / cx_L
            if q <= 0 or abs(x / F - cx_L) <= self.w_far:
                continue
            height = min(H_L, horizon_L + d_wall * q + drop)
            self.walls.append((x, int(round(height * F)), k_wall / q))

        # 左右镜像列合并：同一 |x-cx| 的两列，高度与采样系数完全相同，
        # 每帧只需缩放一次，再分别 blit 到左右两侧（省掉一半缩放与取列）
        self._wall_groups = []
        by_dist = {}
        for x, height, k_over_q in self.walls:
            entry = by_dist.get(abs(x - cx))
            if entry is None:
                entry = by_dist[abs(x - cx)] = ([], height, k_over_q)
            entry[0].append(x)
        self._wall_groups.extend(by_dist.values())

        # 洞壁压暗与距离雾都按「逻辑分辨率」构建：CPU 的实体层就是这个尺寸，
        # 每帧随实体层一起合成，既省内存也避免视角抬升时反复上传大贴图。
        # 输入为输出像素行/列，这里折回逻辑像素。
        self.overlay_w = int(round(W_L))
        self.overlay_h = int(round(H_L))
        cx_L_int = int(round(cx_L))

        self.wall_dark = pygame.Surface((self.overlay_w, self.overlay_h), pygame.SRCALPHA)
        self.wall_dark.fill((0, 0, 0, WALL_DARK_ALPHA))
        self.wall_dark.fill((0, 0, 0, 0),
                            (cx_L_int - self.w_far, 0, self.w_far * 2,
                             int(round(exit_bottom_L)) + 1))
        for y, d, half_w, _, _, _ in self.rows:
            hw = int(round(half_w / F))
            self.wall_dark.fill((0, 0, 0, 0),
                                (cx_L_int - hw, int(round(y / F)), hw * 2, 1))

        # 距离雾：洞壁按列（固定深度）、地面按行
        # 以洞壁最近点（行距 d_wall）为雾的零点；FOG_FULL 之后完全遮断
        self.fog = pygame.Surface((self.overlay_w, self.overlay_h), pygame.SRCALPHA)
        for x, height, _ in self.walls:
            q = abs(x / F - cx_L) / cx_L
            alpha = self._fog_alpha(1.0 - q)
            if alpha > 0:
                self.fog.fill((*self.bg_color, alpha),
                              (int(round(x / F)), 0, 1, max(1, int(round(height / F)))))
        for y, d, half_w, _, _, _ in self.rows:
            t = max(0.0, 1.0 - d / d_wall)
            alpha = self._fog_alpha(t)
            if alpha > 0:
                hw = int(round(half_w / F))
                self.fog.fill((*self.bg_color, alpha),
                              (cx_L_int - hw, int(round(y / F)), hw * 2, 1))

    @staticmethod
    def _make_tileable(surface, axis, band=SEAM_BAND):
        """把贴图沿滚动换行方向做成真正无缝。

        这些素材由两个近似相同的半幅拼成，真正的内容接缝在自然周期
        P、2P... 处（地面在半图行、洞壁在半图列），而不是图片最外缘。
        先检测自然周期 P，再对每一处接缝做窄带内容融合（保留细节，
        不做平均色涂抹），使滚动换行处无跳变。
        """
        w, h = surface.get_size()
        size = h if axis == "v" else w
        arr = np.asarray(pygame.surfarray.array3d(surface), dtype=np.float64).copy()
        period = Pseudo3DFloor._detect_period(surface, axis)
        Pseudo3DFloor._repair_seams(arr, axis, period, min(band, max(4, size // 4)))
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        px = pygame.surfarray.pixels3d(out)
        px[:, :, :] = arr.astype(np.uint8)
        pa = pygame.surfarray.pixels_alpha(out)
        pa[:, :] = 255
        del px, pa
        return out

    @staticmethod
    def _block_period(surface, axis, probe=32):
        """找贴图滚动方向上的最小方块周期（两个内容接缝之间即一个方块）：
        沿滚动轴做自相似扫描，取『局部谷值且明显低于中位水平』的最小周期，
        用于让墙壁与地面方块一一对应；找不到清晰周期时返回 None（不强行对齐）。"""
        w, h = surface.get_size()
        if axis == "v":
            small = pygame.transform.smoothscale(surface, (probe, h))
            a = np.asarray(pygame.surfarray.array3d(small), dtype=np.float64)
            size = h
        else:
            small = pygame.transform.smoothscale(surface, (w, probe))
            a = np.asarray(pygame.surfarray.array3d(small), dtype=np.float64)
            size = w
        lo, hi = 4, size // 2
        diffs = []
        for p in range(lo, hi + 1):
            if axis == "v":
                d = float(np.abs(a[:, :size - p, :] - a[:, p:, :]).mean())
            else:
                d = float(np.abs(a[:size - p, :, :] - a[p:, :, :]).mean())
            diffs.append((d, p))
        if len(diffs) < 3:
            return None
        med = sorted(d for d, _ in diffs)[len(diffs) // 2]
        for i in range(1, len(diffs) - 1):
            d, p = diffs[i]
            # 强谷值：明显低于两侧邻居，且显著低于整体中位水平（排除噪声小周期）
            if d <= 0.85 * min(diffs[i - 1][0], diffs[i + 1][0]) and d <= med * 0.75:
                return p
        return None

    @staticmethod
    def _detect_period(surface, axis, probe=8):
        """沿滚动轴降采样，找内容自相似的最佳重复周期（优先取较大周期）。"""
        w, h = surface.get_size()
        if axis == "v":
            small = pygame.transform.smoothscale(surface, (probe, h))
            a = np.asarray(pygame.surfarray.array3d(small), dtype=np.float64)
            size = h
        else:
            small = pygame.transform.smoothscale(surface, (w, probe))
            a = np.asarray(pygame.surfarray.array3d(small), dtype=np.float64)
            size = w
        lo = max(4, size // 4)
        hi = size // 2
        scores = []
        for p in range(lo, hi + 1):
            if axis == "v":
                d = float(np.abs(a[:, :size - p, :] - a[:, p:, :]).mean())
            else:
                d = float(np.abs(a[:size - p, :, :] - a[p:, :, :]).mean())
            scores.append((d, p))
        best_d = min(d for d, _ in scores)
        return max(p for d, p in scores if d <= best_d * 1.02)

    @staticmethod
    def _repair_seams(arr, axis, period, band):
        """修复 P、2P...（含末尾换行）每一处内容接缝。

        把接缝前 band 像素渐变到接缝后的内容，使换行处连续。
        只改接缝附近，不动整体纹理。
        """
        size = arr.shape[1] if axis == "v" else arr.shape[0]
        seams = list(range(period, size, period))
        if seams[-1] != size:
            seams.append(size)
        for s in seams:
            for j in range(band):
                w = (j + 1) / band
                idx = s - band + j
                if 0 <= idx < size:
                    if axis == "v":
                        arr[:, idx, :] = arr[:, idx, :] * (1 - w) + arr[:, s % size, :] * w
                    else:
                        arr[idx, :, :] = arr[idx, :, :] * (1 - w) + arr[s % size, :, :] * w

    @staticmethod
    def _fog_alpha(t):
        if t <= FOG_START:
            return 0
        u = min(1.0, (t - FOG_START) / (FOG_FULL - FOG_START))
        return min(255, int(255 * (u ** FOG_EXP)))

    def ramp_speed(self, multiplier, duration):
        # 将滚动速度平滑过渡到 multiplier 倍，duration 秒内完成（smoothstep 缓入缓出）
        if self._ramp_dur <= 0 and abs(self.speed_mult - multiplier) < 0.001:
            return
        self._ramp_from = self.speed_mult
        self._ramp_target = float(multiplier)
        self._ramp_t = 0.0
        self._ramp_dur = max(0.0, float(duration))

    def ramp_view_height(self, target, duration):
        """视角高度平滑过渡到 target（px，正值 = 地平线向上抬升，视野变高俯瞰战场）"""
        self.view_rise_from = self.view_rise
        self.view_rise_target = float(target)
        self.view_rise_t = 0.0
        self.view_rise_dur = max(0.0, float(duration))

    def update(self, dt):
        if self._ramp_dur > 0:
            self._ramp_t = min(self._ramp_t + dt, self._ramp_dur)
            u = self._ramp_t / self._ramp_dur
            u = u * u * (3.0 - 2.0 * u)      # smoothstep 缓入缓出
            self.speed_mult = self._ramp_from + (self._ramp_target - self._ramp_from) * u
            if self._ramp_t >= self._ramp_dur:
                self.speed_mult = self._ramp_target
                self._ramp_dur = 0.0
        ds = self.base_speed * self.speed_mult * dt
        # 在最小公倍数处换行：地面与洞壁各自周期均为其约数，换行瞬间双方都无缝
        self.scroll = (self.scroll + ds) % self._scroll_period
        # 视角抬升：地平线逐渐上移（俯瞰战场），逐帧重建几何
        if self.view_rise_dur > 0:
            self.view_rise_t = min(self.view_rise_t + dt, self.view_rise_dur)
            u = self.view_rise_t / self.view_rise_dur
            u = u * u * (3.0 - 2.0 * u)      # smoothstep 缓入缓出
            self.view_rise = self.view_rise_from + (self.view_rise_target - self.view_rise_from) * u
            if self.view_rise_t >= self.view_rise_dur:
                self.view_rise = self.view_rise_target
                self.view_rise_dur = 0.0
            new_horizon = int(round((self._base_horizon_L - self.view_rise)
                                    * self.scale))
            if new_horizon != self.horizon:
                self.horizon = new_horizon
            # 视角高度一变就要重建：几何里的远端下落量（drop）直接由 view_rise
            # 决定，只盯着地平线整数变化会漏掉「地平线没跨过整像素但视角在动」
            # 的那些帧，地面远端会滞后一两像素
            self._geom_dirty = True

    def ensure_geometry(self):
        """本帧真要画地面时才重建几何（重建与否由调用方决定）。

        视角抬升动画期间地平线每帧都在变，重建一次要按行/逐列重建表格并
        分配两张逻辑尺寸的压暗/雾面（约 6ms）。符卡背景不透明时会把地面
        完全遮住，关卡那一段根本不画地面——这段时间的重建纯粹是白烧。
        """
        if self._geom_dirty:
            self._rebuild_geometry()

    def set_scale(self, factor):
        """切换输出倍率：只改像素尺寸，几何与贴图采样仍是逻辑单位。

        几何本身与倍率无关，所以 1x 与 3x 的构图、贴图密度完全一致，放大只是
        采样更细。贴图与倍率无关，已上传的 GPU 纹理无需重传。
        """
        factor = max(1, int(factor))
        if factor == self.scale:
            return
        self.scale = factor
        self.area_w = self.logical_w * factor
        self.area_h = self.logical_h * factor
        self.cx = self.area_w / 2.0
        self.horizon = self._base_horizon_L * factor
        # 缩放目标面按尺寸缓存，倍率变了尺寸也变，整批作废
        self._wall_dst = {}
        self._row_dst = {}
        self._rebuild_geometry()

    def draw_gpu(self, renderer, dst_rect, tex_floor, tex_wall):
        """在 GPU 上原生绘制地面与洞壁（每条贴图条带提交一个四边形）。

        与 draw() 等价，只是把「每行/每列一次缩放 + blit」换成显卡的纹理四边形：
        CPU 只负责取列/取行与坐标计算，拉伸采样交给显卡，倍率提高后不再有
        CPU 侧的像素代价。压暗层与距离雾仍留在 CPU 侧（见 _rebuild_geometry）。

        这里**不做**「同源条带合并」：材质走的是线性采样（SDL_RENDER_SCALE_QUALITY=1），
        把一条 1 纹素宽的贴图拉到 N 像素宽时，采样点会落在纹素之间、边缘掺进相邻
        纹素的颜色（同一列拆成 3 条画是 90/90/90，合并成一条画变成 80/90/100），
        画面就不逐位一致了。而合并只在倍率 >1 时才可能少提交几条：实测本机 3x
        （k = 1.0）时洞壁 1529 列宽度全是 1、一条都并不起来，地板也只从 1238 行并到
        1069 行（省 6% 的提交），代价却是整片像素被改动 —— 不划算。
        """
        self.ensure_geometry()
        # 先用背景色铺满战斗区：CPU 路径下这里是那层 pygame.draw.rect 的底色，
        # 几何没覆盖到的像素（如视角抬升后的边角）不会露出呈现层的清屏色
        renderer.draw_color = (*self.bg_color, 255)
        renderer.fill_rect(dst_rect)
        k = dst_rect[2] / float(self.area_w)
        ox, oy = dst_rect[0], dst_rect[1]
        scroll = self.scroll
        cx = self.cx
        tile_h = self.tile_h
        wall_w = self.wall_w
        wall_h = self.wall_h
        draw_wall = tex_wall.draw
        draw_floor = tex_floor.draw
        if k == 1.0:
            # 常用情形（输出恰好是渲染倍率的整数倍）：坐标已是像素，省掉浮点运算
            for xs, height, k_wall_over_q in self._wall_groups:
                v = int((k_wall_over_q + scroll) % wall_w)
                for x in xs:
                    draw_wall(srcrect=(v, 0, 1, wall_h),
                              dstrect=(ox + x, oy, 1, height))
            for y, d, half_w, k_over_d, sub_x, sub_w in self.rows:
                v = int((k_over_d + scroll) % tile_h)
                draw_floor(srcrect=(sub_x, v, sub_w, 1),
                           dstrect=(ox + cx - half_w, oy + y, half_w * 2, 1))
            return
        for xs, height, k_wall_over_q in self._wall_groups:
            v = int((k_wall_over_q + scroll) % wall_w)
            h = max(1, int(round(height * k)))
            for x in xs:
                x0 = int(x * k)
                draw_wall(srcrect=(v, 0, 1, wall_h),
                          dstrect=(ox + x0, oy, max(1, int((x + 1) * k) - x0), h))
        for y, d, half_w, k_over_d, sub_x, sub_w in self.rows:
            v = int((k_over_d + scroll) % tile_h)
            y0 = int(y * k)
            draw_floor(srcrect=(sub_x, v, sub_w, 1),
                       dstrect=(ox + int((cx - half_w) * k), oy + y0,
                                max(1, int(half_w * 2 * k)),
                                max(1, int((y + 1) * k) - y0)))

    def draw(self, screen, offset_x=0, offset_y=0):
        """绘制战斗区背景：洞壁 → 地面 → 压暗层 → 距离雾。

        洞壁与地面都是「每列/每行取贴图一条、拉伸后贴一次」，每帧近千次
        缩放与 blit，是全局最大的绘制开销。这里做两件事：
        - 左右镜像的洞壁列共用一次缩放结果（两列高度、采样系数完全相同）
        - 缩放写入按尺寸复用的目标面，避免每帧新建大量小 Surface
        """
        self.ensure_geometry()
        scroll = self.scroll
        cx = int(self.cx)
        blit = screen.blit
        scale = pygame.transform.scale
        wall_tile = self.wall_tile
        wall_w = self.wall_w
        wall_h = self.wall_h
        wall_dst = self._wall_dst
        # 洞壁（逐列：竖纹理，向两侧掠过）
        for xs, height, k_wall_over_q in self._wall_groups:
            v = int((k_wall_over_q + scroll) % wall_w)
            target = wall_dst.get(height)
            if target is None:
                target = wall_dst[height] = pygame.Surface((1, height))
            scale(wall_tile.subsurface((v, 0, 1, wall_h)), (1, height), target)
            for x in xs:
                blit(target, (offset_x + x, offset_y))
        # 地面（逐行：横纹理，向镜头拉近；底部随靠近放大并向两侧展开）
        tile = self.tile
        tile_h = self.tile_h
        row_dst = self._row_dst
        for y, d, half_w, k_over_d, sub_x, sub_w in self.rows:
            v = int((k_over_d + scroll) % tile_h)
            width = half_w * 2
            target = row_dst.get(width)
            if target is None:
                target = row_dst[width] = pygame.Surface((width, 1))
            scale(tile.subsurface((sub_x, v, sub_w, 1)), (width, 1), target)
            blit(target, (offset_x + cx - half_w, offset_y + y))
        blit(self.wall_dark, (offset_x, offset_y))
        blit(self.fog, (offset_x, offset_y))
