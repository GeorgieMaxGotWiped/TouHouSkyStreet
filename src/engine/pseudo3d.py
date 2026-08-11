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


class Pseudo3DFloor:
    """透视地面+洞壁渲染器，只负责战斗区域。"""

    def __init__(self, texture_path, area_width, area_height, bg_color=(8, 12, 32),
                 horizon_ratio=HORIZON_RATIO, scroll_speed=SCROLL_SPEED,
                 wall_texture_path=None, floor_stretch=1.0, wall_stretch=1.0,
                 tunnel_width=TUNNEL_WIDTH, far_opening=FAR_OPENING,
                 far_drop_gain=FAR_DROP_GAIN, wall_align_to_floor=False):
        self.area_w = int(area_width)
        self.area_h = int(area_height)
        self.bg_color = bg_color
        self.scroll_speed = float(scroll_speed)
        self.horizon = int(self.area_h * horizon_ratio)
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

        # 视角高度：Boss开战等场景可让地平线上移，俯瞰战场
        self._base_horizon = self.horizon
        self.view_rise = 0.0
        self.view_rise_from = 0.0
        self.view_rise_target = 0.0
        self.view_rise_t = 0.0
        self.view_rise_dur = 0.0
        self.tunnel_width = tunnel_width
        self.far_opening = far_opening
        self.far_drop_gain = far_drop_gain

        self._rebuild_geometry()

    def _rebuild_geometry(self):
        """按当前地平线重建地面/洞壁几何与雾（视角抬升时随地平线更新）"""
        self.d_max = max(1, self.area_h - self.horizon)
        self.d_wall = self.d_max / self.tunnel_width   # 洞壁最近点对应的行距（越小通道越宽）
        cx = int(self.cx)
        d_far = min(self.far_opening, self.d_wall - 1)
        # View rise: far opening (end rectangle) drops with camera height,
        # keeping at least a strip of floor at the bottom (cap d_max - d_far - 2)
        drop = int(round(self.view_rise * self.far_drop_gain))
        drop = max(0, min(drop, int(self.d_max - d_far - 2)))
        self._exit_drop = drop
        exit_bottom = self.horizon + d_far + drop
        self.w_far = max(1, int(round(cx * d_far / self.d_wall)))   # 尽头开口半宽（px）
        self._k_floor = PERSPECTIVE * self.d_max * self.d_max

        # 地面：每行预计算 深度 d、绘制半宽、贴图采样子段、透视采样系数 K_f/d
        # - 未满宽区域（d <= d_wall）取整张贴图行
        # - 满宽后（d > d_wall）取贴图行中央一段，随靠近不断放大并向外展开
        # v = K_f/d + scroll
        self.rows = []
        k_floor = self._k_floor
        half_tile = self.tile_w / 2.0
        for y in range(exit_bottom + 1, self.area_h):
            d = y - self.horizon - drop
            hw_virtual = cx * d / self.d_wall      # 未钳制的虚拟半宽（透视继续）
            half_w = max(1, min(cx, int(round(hw_virtual))))
            half_extent = min(half_tile, half_w * half_tile / max(hw_virtual, 1e-9))
            sub_x = max(0, int(round(half_tile - half_extent)))
            sub_w = max(1, min(self.tile_w, int(round(half_extent * 2))))
            if sub_x + sub_w > self.tile_w:
                sub_x = self.tile_w - sub_w
            self.rows.append((y, d, half_w, k_floor / d, sub_x, sub_w))

        # 洞壁：每列预计算 列高度 H（该列洞壁延伸到地面线）、透视采样系数 K_w/q
        # q = |x - cx| / cx（0=正前方 1=屏幕边缘），K_w = K_f / d_wall
        # 中央开口宽度内不画洞壁（|x - cx| <= w_far 为远景开口）
        self.walls = []
        k_wall = k_floor / self.d_wall
        for x in range(self.area_w):
            q = abs(x - cx) / cx
            if q <= 0 or abs(x - cx) <= self.w_far:
                continue
            height = min(self.area_h, int(round(self.horizon + self.d_wall * q + drop)))
            self.walls.append((x, height, k_wall / q))

        # 洞壁压暗：整个区域压暗，再擦除地面梯形和尽头开口
        self.wall_dark = pygame.Surface((self.area_w, self.area_h), pygame.SRCALPHA)
        self.wall_dark.fill((0, 0, 0, WALL_DARK_ALPHA))
        self.wall_dark.fill((0, 0, 0, 0),
                            (cx - self.w_far, 0, self.w_far * 2, exit_bottom + 1))
        for y, d, half_w, _, _, _ in self.rows:
            self.wall_dark.fill((0, 0, 0, 0),
                                (cx - half_w, y, half_w * 2, 1))

        # 距离雾：洞壁按列（固定深度）、地面按行
        # 以洞壁最近点（行距 d_wall）为雾的零点；FOG_FULL 之后完全遮断
        self.fog = pygame.Surface((self.area_w, self.area_h), pygame.SRCALPHA)
        for x, height, _ in self.walls:
            q = abs(x - cx) / cx
            alpha = self._fog_alpha(1.0 - q)
            if alpha > 0:
                self.fog.fill((*self.bg_color, alpha), (x, 0, 1, height))
        for y, d, half_w, _, _, _ in self.rows:
            t = max(0.0, 1.0 - d / self.d_wall)
            alpha = self._fog_alpha(t)
            if alpha > 0:
                self.fog.fill((*self.bg_color, alpha),
                              (cx - half_w, y, half_w * 2, 1))

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
            new_horizon = int(round(self._base_horizon - self.view_rise))
            if new_horizon != self.horizon:
                self.horizon = new_horizon
                self._rebuild_geometry()

    def draw(self, screen, offset_x=0, offset_y=0):
        scroll = self.scroll
        cx = int(self.cx)
        # 洞壁（逐列：竖纹理，向两侧掠过）
        for x, height, k_wall_over_q in self.walls:
            v = int((k_wall_over_q + scroll) % self.wall_w)
            col = self.wall_tile.subsurface((v, 0, 1, self.wall_h))
            wall_col = pygame.transform.scale(col, (1, height))
            screen.blit(wall_col, (offset_x + x, offset_y))
        # 地面（逐行：横纹理，向镜头拉近；底部随靠近放大并向两侧展开）
        for y, d, half_w, k_over_d, sub_x, sub_w in self.rows:
            v = int((k_over_d + scroll) % self.tile_h)
            row = self.tile.subsurface((sub_x, v, sub_w, 1))
            strip = pygame.transform.scale(row, (half_w * 2, 1))
            screen.blit(strip, (offset_x + cx - half_w, offset_y + y))
        screen.blit(self.wall_dark, (offset_x, offset_y))
        screen.blit(self.fog, (offset_x, offset_y))