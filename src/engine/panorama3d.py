# -*- coding: utf-8 -*-
# 伪3D圆柱投影全景背景：把左右无缝的 2D 全景图当作贴在垂直圆柱内壁上的纹理。
#
# 算法（真正的圆柱投影，不是简单 UV.x 平移 / 改图片宽度）：
#   1. 屏幕坐标 -> 摄像机射线方向：
#        射线 d = ((x-cx)/f, (y-cy)/f, 1)，f 为焦距（由水平视场角 fov 决定）。
#   2. 射线与圆柱内壁求交（圆柱 x^2+z^2=R^2，轴为 Y，半径 R，相机在圆心）：
#        交点参数 t = R / sqrt(dx^2+dz^2) = R*cos(phi)，其中 phi = atan(dx/dz)。
#   3. 由交点计算圆柱展开纹理坐标：
#        u = 交点方位角 phi（贴图水平环绕 360°）-> u = (yaw + phi) / 2pi
#        v = 交点在圆柱上的高度 / 圆柱高 -> v = 0.5 + (y-cy)*cos(phi)/(f*(H/R))
#
# 效果：
#   - 屏幕中心正对圆柱正面（phi=0，看到正前方纹理）。
#   - 越靠屏幕左右边缘，视线越偏：水平方向按 atan 分布产生透视，垂直方向随
#     cos(phi) 真实投影（边缘可见的贴图高度范围收窄、上移）。
#   - 相机旋转 = 对 u 整体加减 yaw，纹理绕玩家旋转；yaw 取模 2pi，无限循环。
#
# 性能与平滑（不逐帧生成新贴图）：
#   1) 加载时把源图垂直预缩放并切成"预缩放列缓存"，渲染时逐列 scale+blit；
#   2) 每屏幕列的 atan/arcsin 角偏移与垂直参数在初始化时预计算成查找表；
#   3) 旋转时每帧重建保证丝滑（避免角度分桶缓存导致的"停顿跳变"低帧感）；
#      静止（speed==0）时才复用缓存帧；
#   4) col_step=2：每 2 列合并采样一次（fov<=约115° 时贴图中心已放大>=1x，
#      2px 组不损失可见细节），把每帧 blit/scale 次数减半。

import math
import os

import numpy as np
import pygame

DEFAULT_FOV = 60.0           # 默认水平视场角（度）：越大看到的圆柱面越宽、边缘放大越强
DEFAULT_PROJECTION = "cylinder"  # "cylinder"=射线-圆柱求交（内视）/ "banner"=外贴圆柱
DEFAULT_SPEED = 24.0         # 默认环绕速度（度/秒）
CACHE_STEP = 1.0             # 静止缓存角度步长（度）：仅在 speed==0 时生效
CACHE_MAX = 4                # 帧缓存最多保留桶数（超出后清空重建）
SEAM_BAND = 12               # 首尾接缝修复带宽度（px）；0 = 不修复
X_UPSCALE = 1                # 水平超采样倍数（默认 1：不改动图片宽度）
COL_STEP = 2                 # 每 N 列合并采样一次（见文件头第 4 条）
FLOOR_JUNCTION_V = None      # 地面交界线在墙体贴图 v 上的位置；None=自动检测灰/黄交界
FLOOR_DEPTH_REPEAT = 3.0     # 地面纵深贴图重复次数：越大地面纹理环越密（1.0 仅 1 环）
FLOOR_SEAM_BAND = 10         # 地面贴图水平/垂直环绕接缝修复带宽（px）


def _smoothstep(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


class CylinderPanorama:
    """360° 环形全景渲染器（伪3D 圆柱投影，纯 2D 贴图 + 射线求交数学变换）。"""

    def __init__(self, texture_path, width, height,
                 fov=DEFAULT_FOV, speed=DEFAULT_SPEED, yaw=0.0,
                 v_top=0.0, v_bottom=1.0, x_upscale=X_UPSCALE,
                 seam_band=SEAM_BAND, cache_step=CACHE_STEP,
                 cache_max=CACHE_MAX, projection=DEFAULT_PROJECTION,
                 wall_h=None, bg_color=(5, 7, 14), col_step=COL_STEP,
                 floor_texture_path=None, floor_junction_v=FLOOR_JUNCTION_V,
                 floor_depth_repeat=FLOOR_DEPTH_REPEAT):
        self.w = int(width)
        self.h = int(height)
        self.fov = float(fov)
        self.projection = projection if projection in ("cylinder", "banner") else DEFAULT_PROJECTION
        self.speed = float(speed)          # 环绕速度（度/秒），可直接修改
        self.yaw = float(yaw) % 360.0      # 当前相机朝向（度），0~360 循环
        self.wall_h = wall_h               # 圆柱高/半径 H/R；None = 自动（中心列贴满屏高）
        self.texture_path = texture_path   # 墙体源图路径（地面交界线自动检测用）
        self.bg_color = bg_color
        self.col_step = max(1, int(col_step))
        self._cache_step = max(0.0, float(cache_step))
        self._cache_max = max(1, int(cache_max))
        self._frame = None                 # 静止缓存：上一帧渲染结果（仅 speed==0 时使用）
        self._frame_key = None
        self._frame_cache = {}

        # 地面层状态（floor_texture_path 提供时才启用）
        self._floor_src = None             # 静态地面贴图数组（tex_w x th x 3；None=无地面）
        self.floor_y0 = 0                  # 中心列地面顶边（交界线）的屏幕 y
        self.floor_h = 0                   # 中心列地面高度（px）

        # 速度平滑过渡（ramp_speed）
        self._ramp_from = self.speed
        self._ramp_target = self.speed
        self._ramp_t = 0.0
        self._ramp_dur = 0.0

        self._build_texture(texture_path, v_top, v_bottom, x_upscale, seam_band)
        self._build_lookup()
        if floor_texture_path and os.path.exists(floor_texture_path):
            self._build_floor(floor_texture_path, floor_junction_v, floor_depth_repeat)
        # 复用的帧表面：旋转时每帧重建（避免每帧分配 Surface）
        self._frame_surf = pygame.Surface((self.w, self.h))

    # --- 初始化 ---

    def _build_texture(self, texture_path, v_top, v_bottom, x_upscale, seam_band):
        """加载全景图 -> 首尾接缝修复 -> 垂直预缩放 -> 切成预缩放列缓存。"""
        img = pygame.image.load(texture_path)
        try:
            img = img.convert()
        except Exception:
            pass
        tw, th = img.get_size()

        # 垂直裁剪区间（可只取贴图的一部分映射到圆柱高度）
        v0 = int(round(v_top * th))
        v1 = int(round(v_bottom * th))
        if v1 > v0 and (v0 > 0 or v1 < th):
            img = img.subsurface((0, v0, tw, v1 - v0))
            th = v1 - v0

        # 首尾接缝修复：把右缘 band 像素逐渐融合到左缘内容，保证环绕无接缝
        if seam_band > 0 and tw > seam_band * 2:
            arr = pygame.surfarray.array3d(img).astype(np.float32)
            for j in range(int(seam_band)):
                wt = (j + 1) / float(seam_band)
                c = tw - int(seam_band) + j
                arr[c] = arr[c] * (1.0 - wt) + arr[0] * wt
            img = pygame.surfarray.make_surface(np.ascontiguousarray(arr, dtype=np.uint8))

        # 垂直一次缩放：源图整幅映射到圆柱高，供逐列采样（宽度保持不变）
        if x_upscale > 1 and x_upscale != 1:
            tw = max(1, int(round(tw * x_upscale)))
        try:
            img = pygame.transform.smoothscale(img, (tw, self.h))
        except Exception:
            img = pygame.transform.scale(img, (tw, self.h))
        self.tex_w = tw
        # 预缩放列缓存：每个源列一张 1px 宽的竖条（subsurface 视图，零拷贝）
        self._col_surfs = [img.subsurface((c, 0, 1, self.h)) for c in range(tw)]

    def _build_lookup(self):
        """预计算每屏幕列的投影参数（不随 yaw 变化），运行时只加 yaw 偏移。"""
        cx = (self.w - 1) / 2.0
        half = min(89.9, math.radians(self.fov) / 2.0)
        x = np.arange(self.w, dtype=np.float32) - cx
        if self.projection == "banner":
            # 外贴圆柱（旧模式，保留作对比）：arcsin 投影，中心放大两侧压缩
            self._radius = cx / math.sin(half)
            ang = np.arcsin(np.clip(x / self._radius, -1.0, 1.0))
            self._cos = np.cos(ang).astype(np.float32)
            self._need_fill = True
        else:
            # 圆柱内壁投影：射线 d=(tan(phi),*,1) 与 x^2+z^2=R^2 求交，
            # 交点方位角 phi = atan(dx/dz) = atan(x/f)
            self._focal = cx / math.tan(half)
            ang = np.arctan(x / self._focal)
            cos = np.cos(ang).astype(np.float32)
            self._cos = cos
            if self.wall_h is None:
                # 默认：中心列贴图 v∈[0,1] 恰好占满整屏高
                self.wall_h = self.h / self._focal
            wh = float(self.wall_h)
            # 屏幕 y -> 纹理 v：v = 0.5 + (y-cy)*cos(phi)/(f*wh)
            # 整幅贴图（v 0..1）在屏幕上的高度/起点（像素）：
            self._col_h = (self._focal * wh / cos).astype(np.int32)
            cy = (self.h - 1) / 2.0
            self._col_y0 = np.rint(cy - self._col_h / 2.0).astype(np.int32)
            # 是否可能有未覆盖区域（wall_h 设得较小时才需要填充底色）
            self._need_fill = bool((self._col_h < self.h).any())
        # float64：避免 yaw 偏移叠加时 float32 舍入导致环绕边界差一列（无缝循环）
        self._col_base = (ang / math.tau * self.tex_w).astype(np.float64)
        self._col_int = np.empty(self.w, dtype=np.int32)

    def _detect_junction_v(self):
        """自动检测墙体贴图灰/黄交界：取下 60% 内行亮度跳变最大处。"""
        try:
            img = pygame.image.load(self.texture_path).convert()
        except Exception:
            return 0.80
        w, h = img.get_size()
        arr = pygame.surfarray.array3d(img)
        rows = arr.mean(axis=(0, 2)).astype(np.float64)
        lo = int(h * 0.4)
        d = np.diff(rows[lo:])
        if len(d) == 0:
            return 0.80
        i = lo + int(np.argmax(d))
        return (i + 0.5) / h

    def _build_floor(self, floor_path, junction_v, depth_repeat):
        """构建水平地面层：与墙体同曲率、紧密贴合、同步旋转。

        地面与墙体共用同一方位角映射（u=(yaw+phi)/2pi），旋转完全同步；
        每屏幕列的径向透视 v = K/((cy-y)*cos(phi))，与墙体一样随 cos(phi)
        弯曲（环纹在两侧下弯），且每列交界线取墙体灰/黄交界点，使地面顶边
        恰好贴在墙体的交界曲线上（紧密贴合）。
        行映射表在初始化时预计算并缓存；渲染时只对静态贴图按表重采样，
        与墙体一致按 col_step 分组后写入复用的帧表面并逐组 blit（不逐帧新建贴图）。
        """
        if junction_v is None:
            junction_v = self._detect_junction_v()
        jv = float(junction_v)
        if depth_repeat is None:
            depth_repeat = FLOOR_DEPTH_REPEAT
        cy = (self.h - 1) / 2.0

        img = pygame.image.load(floor_path)
        try:
            img = img.convert()
        except Exception:
            pass
        tw, th = img.get_size()
        arr = pygame.surfarray.array3d(img).astype(np.float32)
        # 首尾接缝修复（水平+垂直），保证环绕无环缝/无竖缝
        band = max(4, min(FLOOR_SEAM_BAND, th // 4))
        # 右缘融向左缘（u 环绕）、底缘融向顶缘（v 环绕），保证无缝
        for j in range(band):
            wt = (j + 1) / float(band)
            arr[tw - band + j, :] = arr[tw - band + j, :] * (1.0 - wt) + arr[j, :] * wt
            arr[:, th - band + j] = arr[:, th - band + j] * (1.0 - wt) + arr[:, j] * wt
        # 水平平铺到 tex_w（通常为整数倍，环绕天然无缝）
        reps = int(math.ceil(self.tex_w / float(tw)))
        tiled = np.tile(arr, (reps, 1, 1))[:self.tex_w, :, :]   # (tex_w, th, 3)
        self._floor_src = np.ascontiguousarray(tiled)           # 静态源贴图（列=方位角）

        # 每屏幕列的交界线 y0[x]（= 墙体灰/黄交界点）：地面顶边贴墙
        if self.projection == "cylinder":
            col_h = self._col_h.astype(np.float64)
            col_y0 = self._col_y0.astype(np.float64)
        else:
            col_h = np.full(self.w, float(self.h))
            col_y0 = np.full(self.w, cy - self.h / 2.0)
        y0_arr = np.rint(col_y0 + jv * col_h).astype(np.int64)
        y0_arr = np.clip(y0_arr, 1, self.h - 2)
        floor_h_arr = (self.h - y0_arr).astype(np.int32)
        max_h = int(floor_h_arr.max())
        if max_h < 2:
            self._floor_src = None
            return

        # K 使交界圆处 v=1；cos 已由 _build_lookup 按列保存。
        # 与墙体一致按 col_step 合并采样：每组取组首列参数，渲染时组内列共享
        # （take_along_axis/blit 次数减半；fov<=约115° 时贴图中心放大>=1x，
        #  2px 组不损失可见细节）。
        step = self.col_step
        ns = int(math.ceil(self.w / float(step)))
        gx = np.minimum(np.arange(ns, dtype=np.int64) * step, self.w - 1)
        K = (0.5 - jv) * self.h
        cos = self._cos
        r0m = np.zeros((ns, max_h), dtype=np.int64)
        r1m = np.zeros((ns, max_h), dtype=np.int64)
        frm = np.zeros((ns, max_h), dtype=np.float32)
        for gi, x in enumerate(gx.tolist()):
            fh = int(floor_h_arr[x])
            if fh <= 0:
                continue
            yy = y0_arr[x] + np.arange(fh, dtype=np.float64)
            v = K / ((cy - yy) * float(cos[x]))
            vpx = np.clip(v, 0.0, None) * th * max(0.1, float(depth_repeat))
            r0 = np.floor(vpx).astype(np.int64) % th
            fr = (vpx - np.floor(vpx)).astype(np.float32)
            r0m[gi, :fh] = r0
            r1m[gi, :fh] = (r0 + 1) % th
            frm[gi, :fh] = fr
        self._floor_step = step
        self._floor_ns = ns
        self._floor_gx = gx.astype(np.int32)
        self._floor_r0 = r0m
        self._floor_r1 = r1m
        self._floor_fr = frm
        self._floor_y0 = y0_arr[gx].astype(np.int32)
        self._floor_len = floor_h_arr[gx]
        self.floor_y0 = int(y0_arr[self.w // 2])
        self.floor_h = int(floor_h_arr[self.w // 2])
        # 复用的地面帧表面：每帧用 numpy 写入像素后逐组 blit（不逐帧分配）
        self._floor_surf = pygame.surfarray.make_surface(
            np.zeros((self.w, max_h, 3), dtype=np.uint8))

    # --- 速度控制 ---

    def set_speed(self, speed):
        """立即设置环绕速度（度/秒，可为负表示反向）。"""
        self.speed = float(speed)
        self._ramp_dur = 0.0

    def ramp_speed(self, target, duration):
        """在 duration 秒内把环绕速度平滑过渡到 target（smoothstep）。"""
        self._ramp_from = self.speed
        self._ramp_target = float(target)
        self._ramp_t = 0.0
        self._ramp_dur = max(0.0, float(duration))

    def update(self, dt):
        """按帧推进环绕角；dt 为秒。"""
        if self._ramp_dur > 0:
            self._ramp_t = min(self._ramp_t + dt, self._ramp_dur)
            self.speed = (self._ramp_from
                          + (self._ramp_target - self._ramp_from)
                          * _smoothstep(self._ramp_t / self._ramp_dur))
            if self._ramp_t >= self._ramp_dur:
                self.speed = self._ramp_target
                self._ramp_dur = 0.0
        if dt > 0:
            self.yaw = (self.yaw + self.speed * dt) % 360.0

    # --- 渲染 ---

    def _blit_column(self, blit, scale, col_surfs, idx, x, width, h):
        ch = int(self._col_h[x])
        col = col_surfs[idx[x]]
        if ch == h and width == 1:
            blit(col, (x, int(self._col_y0[x])))
        else:
            blit(scale(col, (width, ch)), (x, int(self._col_y0[x])))

    def _render_floor(self, blit, idx):
        """渲染地面：静态贴图按列索引重采样（与墙体同一 idx -> 同步旋转）。

        行映射表在初始化时预计算（v=K/((cy-y)*cos(phi))，与墙体同曲率），
        按 col_step 分组采样，结果写入复用的帧表面后逐组 blit 到交界线下方。
        """
        step = self._floor_step
        src = self._floor_src[idx[self._floor_gx]]          # (ns, th, 3) 组首列取源贴图
        sub = np.transpose(src, (0, 2, 1))                  # (ns, 3, th)
        r0 = self._floor_r0
        r1 = self._floor_r1
        fr = self._floor_fr
        s0 = np.take_along_axis(sub, r0[:, None, :], axis=2)
        s1 = np.take_along_axis(sub, r1[:, None, :], axis=2)
        arr = np.ascontiguousarray(
            (s0 * (1.0 - fr)[:, None, :] + s1 * fr[:, None, :])
            .transpose(0, 2, 1)).astype(np.uint8)
        px = pygame.surfarray.pixels3d(self._floor_surf)
        px[:, :, :] = np.repeat(arr, step, axis=0)[:self.w]
        del px
        y0s = self._floor_y0
        lens = self._floor_len
        for k in range(self._floor_ns):
            fh = int(lens[k])
            if fh > 0:
                x0 = k * step
                w_run = min(step, self.w - x0)
                blit(self._floor_surf, (x0, int(y0s[k])), area=(x0, 0, w_run, fh))

    def _build_frame(self):
        """按当前 yaw 生成一帧圆柱投影画面（写入复用的帧表面）。"""
        yaw_px = (self.yaw % 360.0) / 360.0 * self.tex_w
        wrapped = (self._col_base + yaw_px) % self.tex_w
        self._col_int[:] = np.minimum(wrapped, self.tex_w - 1).astype(np.int32)
        idx = self._col_int.tolist()
        frame = self._frame_surf
        if self._need_fill:
            frame.fill(self.bg_color)
        blit = frame.blit
        scale = pygame.transform.scale
        col_surfs = self._col_surfs
        step = self.col_step
        w = self.w
        h = self.h
        if self.projection == "banner":
            # 外贴圆柱：整幅贴图垂直线性映射，合并连续相同源列后逐段 blit
            prev = -1
            start = 0
            for i, c in enumerate(idx):
                if c != prev:
                    if i > start:
                        w_run = i - start
                        col = col_surfs[idx[start]]
                        if w_run == 1:
                            blit(col, (start, 0))
                        else:
                            blit(scale(col, (w_run, h)), (start, 0))
                    start = i
                    prev = c
            w_run = w - start
            col = col_surfs[idx[start]]
            if w_run == 1:
                blit(col, (start, 0))
            else:
                blit(scale(col, (w_run, h)), (start, 0))
        else:
            # 圆柱内壁投影：每列按交点做垂直真实投影（v 随列变化），
            # 按 col_step 合并采样以减半 blit/scale 次数（fov<=约115° 时无损细节）
            for x in range(0, w - step + 1, step):
                self._blit_column(blit, scale, col_surfs, idx, x, step, h)
            for x in range(w - step + 1, w):
                self._blit_column(blit, scale, col_surfs, idx, x, 1, h)
        # 地面层：与墙体共用同一列索引（同步旋转），逐列按预计算行表渲染
        if self._floor_src is not None:
            self._render_floor(blit, self._col_int)
        return frame

    def draw(self, canvas, offset_x=0, offset_y=0):
        """把当前视角画面绘制到 canvas（offset 用于战斗区偏移）。

        旋转期间每帧重建，保证背景丝滑；仅在静止（speed==0）时复用缓存帧。
        """
        key = None
        if self.speed == 0.0 and self._cache_step > 0:
            key = int(self.yaw / self._cache_step)
            if key is not None and self._frame is not None and self._frame_key == key:
                canvas.blit(self._frame, (offset_x, offset_y))
                return
        frame = self._build_frame()
        if key is not None:
            # 缓存的是独立副本，避免复用帧表面被后续重建覆盖
            self._frame = frame.copy()
            self._frame_key = key
            if len(self._frame_cache) >= self._cache_max:
                self._frame_cache.clear()
            self._frame_cache[key] = self._frame
        canvas.blit(frame, (offset_x, offset_y))
