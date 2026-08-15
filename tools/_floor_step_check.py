# -*- coding: utf-8 -*-
import numpy as np, time
from PIL import Image

W, H = 576, 670
TEXW = 1152
TH = 128
STEP = 2
OUT = r"C:/Users/admin/.codex/visualizations/2026/08/12/019ff64c-eedd-7723-a592-58d6beff830f"

tex = np.asarray(Image.open(r"D:\pyz\my thingses\TouHou\assets\backgrounds\stage3\bg1.png").convert("RGB").resize((TEXW, H), Image.BILINEAR)).astype(np.float32)

cx = (W - 1) / 2.0
half = np.radians(60.0) / 2.0
focal = cx / np.tan(half)
x = np.arange(W) - cx
phi = np.arctan(x / focal)
col_base = phi / (2.0 * np.pi) * TEXW
cos = np.cos(phi).astype(np.float32)
col_h = (H / cos).astype(np.int32)
cy = (H - 1) / 2.0
col_y0 = np.rint(cy - col_h / 2.0).astype(np.int32)

jv = 0.8307
fimg = np.asarray(Image.open(r"D:\pyz\my thingses\TouHou\assets\backgrounds\stage3\bossfloor1.png").convert("RGB")).astype(np.float32)
arr = np.transpose(fimg, (1, 0, 2)).copy()
band = 10
for j in range(band):
    wt = (j + 1) / float(band)
    arr[TH - band + j, :] = arr[TH - band + j, :] * (1.0 - wt) + arr[j, :] * wt
    arr[:, TH - band + j] = arr[:, TH - band + j] * (1.0 - wt) + arr[:, j] * wt
reps = int(np.ceil(TEXW / float(TH)))
src_arr = np.ascontiguousarray(np.tile(arr, (reps, 1, 1))[:TEXW, :, :])

col_h_f = col_h.astype(np.float64)
col_y0_f = col_y0.astype(np.float64)
y0_arr = np.rint(col_y0_f + jv * col_h_f).astype(np.int64)
y0_arr = np.clip(y0_arr, 1, H - 2)
floor_h_arr = (H - y0_arr).astype(np.int32)
max_h = int(floor_h_arr.max())
K = (0.5 - jv) * H
depth_repeat = 3.0

# ---- group sampling (mirror patched _build_floor) ----
ns = int(np.ceil(W / float(STEP)))
gx = np.minimum(np.arange(ns) * STEP, W - 1)
r0m = np.zeros((ns, max_h), np.int64)
r1m = np.zeros((ns, max_h), np.int64)
frm = np.zeros((ns, max_h), np.float32)
for gi, xc in enumerate(gx.tolist()):
    fh = int(floor_h_arr[xc])
    if fh <= 0:
        continue
    yy = y0_arr[xc] + np.arange(fh, dtype=np.float64)
    v = K / ((cy - yy) * float(cos[xc]))
    vpx = np.clip(v, 0.0, None) * TH * depth_repeat
    r0 = np.floor(vpx).astype(np.int64) % TH
    fr = (vpx - np.floor(vpx)).astype(np.float32)
    r0m[gi, :fh] = r0
    r1m[gi, :fh] = (r0 + 1) % TH
    frm[gi, :fh] = fr
gy0 = y0_arr[gx].astype(np.int32)
glen = floor_h_arr[gx]

def render(yaw):
    yaw_px = (yaw % 360.0) / 360.0 * TEXW
    col_int = ((col_base + yaw_px) % TEXW).astype(np.int32)
    out = np.zeros((H, W, 3), np.float32)
    for xc in range(W):  # wall (per-column, exact)
        c = int(col_int[xc])
        ch = int(col_h[xc])
        yy0 = int(col_y0[xc])
        lo = max(0, yy0); hi = min(H, yy0 + ch)
        if hi > lo:
            n = hi - lo
            v0 = (lo - yy0) / float(ch); v1 = (hi - yy0) / float(ch)
            src = np.clip((np.linspace(v0, v1, n) * (H - 1)).astype(np.int32), 0, H - 1)
            out[lo:hi, xc] = tex[src, c]
    # floor (group sampling, mirror _render_floor)
    sub = np.transpose(src_arr[col_int[gx]], (0, 2, 1))
    s0 = np.take_along_axis(sub, r0m[:, None, :], axis=2)
    s1 = np.take_along_axis(sub, r1m[:, None, :], axis=2)
    arr2 = (s0 * (1.0 - frm)[:, None, :] + s1 * frm[:, None, :]).transpose(0, 2, 1)
    full = np.repeat(arr2, STEP, axis=0)[:W]           # (W, max_h, 3)
    for k in range(ns):
        fh = int(glen[k])
        if fh > 0:
            x0 = k * STEP
            out[gy0[k]:gy0[k] + fh, x0:x0 + min(STEP, W - x0)] = full[x0:x0 + min(STEP, W - x0), :fh].transpose(1, 0, 2)
    return out

f0 = render(0.0)
f360 = render(360.0)
print("loop seamless:", bool(np.array_equal(f0, f360)))

# compare vs per-column floor: columns in a group must equal representative column
col_int0 = ((col_base + 0.0) % TEXW).astype(np.int32)
c0 = col_int0[0]
sub_p = np.transpose(src_arr, (0, 2, 1))
r0p = np.zeros((W, max_h), np.int64); r1p = np.zeros((W, max_h), np.int64); frp = np.zeros((W, max_h), np.float32)
for xc in range(W):
    fh = int(floor_h_arr[xc])
    if fh <= 0: continue
    yy = y0_arr[xc] + np.arange(fh, dtype=np.float64)
    v = K / ((cy - yy) * float(cos[xc]))
    vpx = np.clip(v, 0.0, None) * TH * depth_repeat
    r0 = np.floor(vpx).astype(np.int64) % TH
    r0p[xc, :fh] = r0; r1p[xc, :fh] = (r0 + 1) % TH; frp[xc, :fh] = (vpx - np.floor(vpx)).astype(np.float32)
def render_floor_percol(yaw):
    col_int = ((col_base + yaw / 360.0 * TEXW) % TEXW).astype(np.int32)
    sub = np.transpose(src_arr[col_int], (0, 2, 1))
    s0 = np.take_along_axis(sub, r0p[:, None, :], axis=2)
    s1 = np.take_along_axis(sub, r1p[:, None, :], axis=2)
    return (s0 * (1.0 - frp)[:, None, :] + s1 * frp[:, None, :]).transpose(0, 2, 1)
fp = render_floor_percol(0.0)
fg = np.repeat(render_floor_percol(0.0)[gx], STEP, axis=0)[:W]
diff_cols = np.where(np.any(fg != fp, axis=(1, 2)))[0]
print("group-vs-percol diff columns:", len(diff_cols), "of", W, "(expect ~W/2 odd cols)")
print("odd cols all differ:", bool(np.array_equal(diff_cols, np.arange(1, W, 2))))

Image.fromarray(f0.astype(np.uint8)).save("%s/floor_step_yaw0.png" % OUT)
# benchmark vectorized floor (numpy only, no blit)
t0 = time.perf_counter()
for i in range(200):
    ci = ((col_base + (i * 3.7) % 360.0 / 360.0 * TEXW) % TEXW).astype(np.int32)
    s = np.transpose(src_arr[ci[gx]], (0, 2, 1))
    a = np.take_along_axis(s, r0m[:, None, :], axis=2)
    b = np.take_along_axis(s, r1m[:, None, :], axis=2)
    arr2 = (a * (1.0 - frm)[:, None, :] + b * frm[:, None, :]).transpose(0, 2, 1)
    full = np.repeat(arr2, STEP, axis=0)[:W]
    _ = full.astype(np.uint8)
print("vectorized floor (group): %.3f ms/frame" % ((time.perf_counter() - t0) / 200 * 1000))
print("center y0=%d h=%d edge y0=%d h=%d" % (gy0[W // 2 // STEP], glen[W // 2 // STEP], gy0[0], glen[0]))
