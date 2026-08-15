# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image

W, H = 576, 670
OUT = r"C:/Users/admin/.codex/visualizations/2026/08/12/019ff64c-eedd-7723-a592-58d6beff830f"

# ---- wall texture (simulate pygame.smoothscale to h) ----
tex = np.asarray(Image.open(r"D:\pyz\my thingses\TouHou\assets\backgrounds\stage3\bg1.png").convert("RGB").resize((1152, H), Image.BILINEAR)).astype(np.float32)  # (H, 1152, 3)

# ---- lookup (mirror of _build_lookup) ----
cx = (W - 1) / 2.0
half = np.radians(60.0) / 2.0
focal = cx / np.tan(half)
x = np.arange(W) - cx
phi = np.arctan(x / focal)
col_base = (phi / (2.0 * np.pi) * 1152.0)
cos = np.cos(phi).astype(np.float32)
col_h = (H / cos).astype(np.int32)
cy = (H - 1) / 2.0
col_y0 = np.rint(cy - col_h / 2.0).astype(np.int32)

# ---- floor (mirror of _build_floor, per-column curvature) ----
jv = 0.8307
fimg = np.asarray(Image.open(r"D:\pyz\my thingses\TouHou\assets\backgrounds\stage3\bossfloor1.png").convert("RGB")).astype(np.float32)  # (h,w,3)
arr = np.transpose(fimg, (1, 0, 2)).copy()   # surfarray convention (w,h,3)
tw, th = 128, 128
band = 10
for j in range(band):
    wt = (j + 1) / float(band)
    arr[tw - band + j, :] = arr[tw - band + j, :] * (1.0 - wt) + arr[j, :] * wt
    arr[:, th - band + j] = arr[:, th - band + j] * (1.0 - wt) + arr[:, j] * wt
reps = int(np.ceil(1152.0 / tw))
src_arr = np.ascontiguousarray(np.tile(arr, (reps, 1, 1))[:1152, :, :])  # (tex_w, th, 3)

col_h_f = col_h.astype(np.float64)
col_y0_f = col_y0.astype(np.float64)
y0_arr = np.rint(col_y0_f + jv * col_h_f).astype(np.int64)
y0_arr = np.clip(y0_arr, 1, H - 2)
floor_h_arr = (H - y0_arr).astype(np.int32)
max_h = int(floor_h_arr.max())
K = (0.5 - jv) * H
depth_repeat = 3.0
r0m = np.zeros((W, max_h), np.int64)
r1m = np.zeros((W, max_h), np.int64)
frm = np.zeros((W, max_h), np.float32)
for xc in range(W):
    fh = int(floor_h_arr[xc])
    if fh <= 0:
        continue
    yy = y0_arr[xc] + np.arange(fh, dtype=np.float64)
    v = K / ((cy - yy) * float(cos[xc]))
    vpx = np.clip(v, 0.0, None) * th * depth_repeat
    r0 = np.floor(vpx).astype(np.int64) % th
    fr = (vpx - np.floor(vpx)).astype(np.float32)
    r0m[xc, :fh] = r0
    r1m[xc, :fh] = (r0 + 1) % th
    frm[xc, :fh] = fr

def render(yaw):
    yaw_px = (yaw % 360.0) / 360.0 * 1152.0
    col_int = ((col_base + yaw_px) % 1152.0).astype(np.int32)
    out = np.zeros((H, W, 3), np.float32)
    for xc in range(W):
        c = int(col_int[xc])
        ch = int(col_h[xc])
        yy0 = int(col_y0[xc])
        lo = max(0, yy0)
        hi = min(H, yy0 + ch)
        if hi > lo:
            n = hi - lo
            v0 = (lo - yy0) / float(ch)
            v1 = (hi - yy0) / float(ch)
            src = np.clip((np.linspace(v0, v1, n) * (H - 1)).astype(np.int32), 0, H - 1)
            out[lo:hi, xc] = tex[src, c]
        fh = int(floor_h_arr[xc])
        if fh > 0:
            col = src_arr[c]                         # (th, 3)
            r0 = r0m[xc, :fh]; r1 = r1m[xc, :fh]; fr = frm[xc, :fh]
            strip = col[r0] * (1.0 - fr)[:, None] + col[r1] * fr[:, None]
            out[y0_arr[xc]:y0_arr[xc] + fh, xc] = strip
    return out

f0 = render(0.0)
f360 = render(360.0)
print("loop seamless:", bool(np.array_equal(f0, f360)))
Image.fromarray(f0.astype(np.uint8)).save("%s/floor_cyl_curve_yaw0.png" % OUT)

frames = []
for i in range(31):
    yaw = (i * 12.0) % 360.0
    frames.append(Image.fromarray(render(yaw).astype(np.uint8)))
frames[0].save("%s/floor_cyl_curve_spin.gif" % OUT, save_all=True, append_images=frames[1:], duration=50, loop=0)
print("gif saved; center y0=%d h=%d; edge y0=%d h=%d" % (y0_arr[W//2], floor_h_arr[W//2], y0_arr[0], floor_h_arr[0]))

import time
t0 = time.perf_counter()
for i in range(20):
    render((i * 7.0) % 360.0)
print("sim render: %.2f ms/frame" % ((time.perf_counter() - t0) / 20 * 1000))
