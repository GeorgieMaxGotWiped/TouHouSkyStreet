# -*- coding: utf-8 -*-
import sys
path = r"D:\pyz\my thingses\TouHou\src\engine\panorama3d.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

edits = []

# 1) default depth repeat
edits.append((
"""FLOOR_DEPTH_REPEAT = 1.0     # 地面纵深贴图重复次数：越大地面纹理环越密""",
"""FLOOR_DEPTH_REPEAT = 3.0     # 地面纵深贴图重复次数：越大地面纹理环越密（1.0 仅 1 环）"""))

# 2) floor state marker
edits.append((
"""        # 地面层状态（floor_texture_path 提供时才启用）
        self._floor_surfs = None           # 预扭曲地面贴图的逐列缓存（None=无地面）
        self.floor_y0 = 0                  # 地面顶边（交界线）的屏幕 y
        self.floor_h = 0                   # 地面高度（px）""",
"""        # 地面层状态（floor_texture_path 提供时才启用）
        self._floor_src = None             # 静态地面贴图数组（tex_w x th x 3；None=无地面）
        self.floor_y0 = 0                  # 中心列地面顶边（交界线）的屏幕 y
        self.floor_h = 0                   # 中心列地面高度（px）"""))

# 3) store cos per column in _build_lookup (both projections)
edits.append((
"""            self._radius = cx / math.sin(half)
            ang = np.arcsin(np.clip(x / self._radius, -1.0, 1.0))
            self._need_fill = True""",
"""            self._radius = cx / math.sin(half)
            ang = np.arcsin(np.clip(x / self._radius, -1.0, 1.0))
            self._cos = np.cos(ang).astype(np.float32)
            self._need_fill = True"""))

edits.append((
"""            self._focal = cx / math.tan(half)
            ang = np.arctan(x / self._focal)
            cos = np.cos(ang).astype(np.float32)
            if self.wall_h is None:""",
"""            self._focal = cx / math.tan(half)
            ang = np.arctan(x / self._focal)
            cos = np.cos(ang).astype(np.float32)
            self._cos = cos
            if self.wall_h is None:"""))

# 4) rewrite _build_floor (anchor matches the ACTUAL current file content)
old_floor = """    def _build_floor(self, floor_path, junction_v, depth_repeat):
        \"\"\"构建水平地面层（一次性预计算并缓存，不逐帧生成贴图）。

        地面与墙体共用同一方位角映射（u=(yaw+phi)/2pi），所以渲染时直接复用
        墙体的逐列索引，旋转完全同步；垂直方向按 1/(y-地平线) 径向透视预扭曲：
        交界线（远）纹理压缩、屏幕底部（近）纹理放大，看起来像水平地面。
        \"\"\"
        if junction_v is None:
            junction_v = self._detect_junction_v()
        # 交界线在屏幕上的 y（用中心列的墙体垂直投影参数）
        if self.projection == "cylinder":
            wh = float(self.wall_h) if self.wall_h else self.h / self._focal
            col_h_c = float(self._focal * wh)
        else:
            col_h_c = float(self.h)
        cy = (self.h - 1) / 2.0
        y0 = int(round(cy - col_h_c / 2.0 + junction_v * col_h_c))
        y0 = max(1, min(self.h - 2, y0))
        floor_h = self.h - y0
        if floor_h < 2:
            return

        img = pygame.image.load(floor_path)
        try:
            img = img.convert()
        except Exception:
            pass
        tw, th = img.get_size()
        arr = pygame.surfarray.array3d(img).astype(np.float32)
        # 首尾接缝修复（水平+垂直），保证环绕无环缝/无竖缝
        band = max(4, min(FLOOR_SEAM_BAND, th // 4))
        # 右缘/底缘融向左缘/顶缘：u=0<->u=tw、v=0<->v=th 环绕处无缝
        for j in range(band):
            wt = (j + 1) / float(band)
            arr[:, tw - band + j] = arr[:, tw - band + j] * (1.0 - wt) + arr[:, j] * wt
            arr[th - band + j, :] = arr[th - band + j, :] * (1.0 - wt) + arr[j, :] * wt
        # 水平平铺到 tex_w（通常为整数倍，环绕天然无缝）
        reps = int(math.ceil(self.tex_w / float(tw)))
        tiled = np.tile(arr, (reps, 1, 1))[:self.tex_w, :, :]   # (tex_w, th, 3)
        # 径向透视：v=0 在交界线（远），v=1 在屏底（近），1/(y-地平线) 压缩
        y_arr = y0 + np.arange(floor_h, dtype=np.float64)
        a = 1.0 / (y0 - cy)
        b = 1.0 / (self.h - 1 - cy)
        vn = (a - 1.0 / (y_arr - cy)) / (a - b)
        vpx = np.clip(vn, 0.0, 1.0) * th * max(0.1, float(depth_repeat))
        r0 = np.floor(vpx).astype(np.int64) % th
        fr = (vpx - np.floor(vpx)).astype(np.float32)
        r1 = (r0 + 1) % th
        # warped[x][j] = 纹理 (x, vpx(j))：列=方位角、行=径向透视
        warped = (tiled[:, r0] * (1.0 - fr)[None, :, None]
                  + tiled[:, r1] * fr[None, :, None])   # (tex_w, floor_h, 3)
        surf = pygame.surfarray.make_surface(
            np.ascontiguousarray(warped.astype(np.uint8)))
        self._floor_surfs = [surf.subsurface((c, 0, 1, floor_h))
                             for c in range(self.tex_w)]
        self.floor_y0 = y0
        self.floor_h = floor_h"""

new_floor = """    def _build_floor(self, floor_path, junction_v, depth_repeat):
        \"\"\"构建水平地面层：与墙体同曲率、紧密贴合、同步旋转。

        地面与墙体共用同一方位角映射（u=(yaw+phi)/2pi），旋转完全同步；
        每屏幕列的径向透视 v = K/((cy-y)*cos(phi))，与墙体一样随 cos(phi)
        弯曲（环纹在两侧下弯），且每列交界线取墙体灰/黄交界点，使地面顶边
        恰好贴在墙体的交界曲线上（紧密贴合）。
        行映射表在初始化时预计算并缓存；渲染时只对静态贴图按表重采样，
        写入复用的帧表面后逐列 blit（不逐帧新建贴图）。
        \"\"\"
        if junction_v is None:
            junction_v = self._detect_junction_v()
        jv = float(junction_v)
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

        # K 使交界圆处 v=1；cos 已由 _build_lookup 按列保存
        K = (0.5 - jv) * self.h
        cos = self._cos
        r0m = np.zeros((self.w, max_h), dtype=np.int64)
        r1m = np.zeros((self.w, max_h), dtype=np.int64)
        frm = np.zeros((self.w, max_h), dtype=np.float32)
        for x in range(self.w):
            fh = int(floor_h_arr[x])
            if fh <= 0:
                continue
            yy = y0_arr[x] + np.arange(fh, dtype=np.float64)
            v = K / ((cy - yy) * float(cos[x]))
            vpx = np.clip(v, 0.0, None) * th * max(0.1, float(depth_repeat))
            r0 = np.floor(vpx).astype(np.int64) % th
            fr = (vpx - np.floor(vpx)).astype(np.float32)
            r0m[x, :fh] = r0
            r1m[x, :fh] = (r0 + 1) % th
            frm[x, :fh] = fr
        self._floor_r0 = r0m
        self._floor_r1 = r1m
        self._floor_fr = frm
        self._floor_y0 = y0_arr.astype(np.int32)
        self._floor_len = floor_h_arr
        self.floor_y0 = int(y0_arr[self.w // 2])
        self.floor_h = int(floor_h_arr[self.w // 2])
        # 复用的地面帧表面：每帧用 numpy 写入像素后逐列 blit（不逐帧分配）
        self._floor_surf = pygame.surfarray.make_surface(
            np.zeros((self.w, max_h, 3), dtype=np.uint8))"""

edits.append((old_floor, new_floor))

# 5) replace _blit_floor_column with _render_floor
old_blit = """    def _blit_floor_column(self, blit, scale, floor_surfs, idx, x, width):
        \"\"\"绘制一列地面：列索引与墙体共用（同步旋转），垂直高度已预扭曲。\"\"\"
        col = floor_surfs[idx[x]]
        if width == 1:
            blit(col, (x, self.floor_y0))
        else:
            blit(scale(col, (width, self.floor_h)), (x, self.floor_y0))"""

new_blit = """    def _render_floor(self, blit, idx):
        \"\"\"渲染地面：静态贴图按列索引重采样（与墙体同一 idx -> 同步旋转）。

        每列行映射表在初始化时预计算（v=K/((cy-y)*cos(phi))，与墙体同曲率），
        结果写入复用的帧表面后逐列 blit 到该列交界线下方。
        \"\"\"
        src = self._floor_src[idx]                          # (w, th, 3) 按列取源贴图
        sub = np.transpose(src, (0, 2, 1))                  # (w, 3, th)
        r0 = self._floor_r0
        r1 = self._floor_r1
        fr = self._floor_fr
        s0 = np.take_along_axis(sub, r0[:, None, :], axis=2)
        s1 = np.take_along_axis(sub, r1[:, None, :], axis=2)
        px = pygame.surfarray.pixels3d(self._floor_surf)
        px[:, :, :] = np.ascontiguousarray(
            (s0 * (1.0 - fr)[:, None, :] + s1 * fr[:, None, :])
            .transpose(0, 2, 1)).astype(np.uint8)
        del px
        y0s = self._floor_y0
        lens = self._floor_len
        for x in range(self.w):
            fh = int(lens[x])
            if fh > 0:
                blit(self._floor_surf, (x, int(y0s[x])), area=(x, 0, 1, fh))"""

edits.append((old_blit, new_blit))

# 6) update _build_frame floor section
old_frame = """        # 地面层：与墙体共用逐列索引（同一方位角 -> 同步旋转），只多一次逐列 blit
        if self._floor_surfs is not None:
            for x in range(0, w - step + 1, step):
                self._blit_floor_column(blit, scale, self._floor_surfs, idx, x, step)
            for x in range(w - step + 1, w):
                self._blit_floor_column(blit, scale, self._floor_surfs, idx, x, 1)
        return frame"""
new_frame = """        # 地面层：与墙体共用同一列索引（同步旋转），逐列按预计算行表渲染
        if self._floor_src is not None:
            self._render_floor(blit, self._col_int)
        return frame"""
edits.append((old_frame, new_frame))

for old, new in edits:
    n = src.count(old)
    if n != 1:
        print("FAIL (count=%d): %r" % (n, old[:70]))
        sys.exit(1)
    src = src.replace(old, new, 1)

with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(src)
print("all %d edits applied" % len(edits))
