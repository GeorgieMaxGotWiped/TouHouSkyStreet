# -*- coding: utf-8 -*-
import io
path = r"D:\pyz\my thingses\TouHou\src\engine\panorama3d.py"
src = io.open(path, encoding="utf-8").read()

old_build = """        # K 使交界圆处 v=1；cos 已由 _build_lookup 按列保存
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

new_build = """        # K 使交界圆处 v=1；cos 已由 _build_lookup 按列保存。
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
            np.zeros((self.w, max_h, 3), dtype=np.uint8))"""

old_render = """        src = self._floor_src[idx]                          # (w, th, 3) 按列取源贴图
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

new_render = """        step = self._floor_step
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
                blit(self._floor_surf, (x0, int(y0s[k])), area=(x0, 0, w_run, fh))"""

assert src.count(old_build) == 1, "build anchor: %d" % src.count(old_build)
assert src.count(old_render) == 1, "render anchor: %d" % src.count(old_render)
src = src.replace(old_build, new_build).replace(old_render, new_render)
io.open(path, "w", encoding="utf-8", newline="\n").write(src)
print("patched OK")
