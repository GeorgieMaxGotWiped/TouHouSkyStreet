# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
import importlib.util, sys
spec = importlib.util.spec_from_file_location("sim", r"D:\pyz\my thingses\TouHou\tools\_floor_sim_preview.py")
# instead of running, replicate key parts quickly by exec'ing up to render definition
src = open(r"D:\pyz\my thingses\TouHou\tools\_floor_sim_preview.py", encoding="utf-8").read()
# cut off the demo section at the bottom (f0 = render...)
cut = src.index("f0 = render(0.0)")
ns = {}
exec(compile(src[:cut], "sim", "exec"), ns)
render = ns["render"]

a0 = render(0.0).astype(np.uint8)
a10 = render(10.0).astype(np.uint8)
a20 = render(20.0).astype(np.uint8)

# junction horizontality: is row y=557 all floor and row 556 all wall?
row_floor = a0[557].mean(axis=1)
row_wall = a0[556].mean(axis=1)
print("row557 (floor) min/max/mean:", row_floor.min().round(1), row_floor.max().round(1), row_floor.mean().round(1))
print("row556 (wall)  min/max/mean:", row_wall.min().round(1), row_wall.max().round(1), row_wall.mean().round(1))

# floor texture visibility: std of rows in floor area
fl = a0[560:665]
print("floor region std:", fl.std(axis=(0,1)).round(1), " mean:", fl.mean(axis=(0,1)).round(1))

# rotation sync: horizontal shift of the junction-area pattern between yaw 0 and 10
# compare a column slice near the junction
s0 = a0[560:665].astype(np.float32)
s1 = a10[560:665].astype(np.float32)
# best integer shift via cross-correlation over the middle region
best = min(range(-40, 41), key=lambda d: np.abs(np.roll(s0, d, axis=1) - s1).mean())
print("floor pattern shift yaw0->10 (px):", best, "(expect ~32 = 10/360*1152)")

# wall shift check on a strip above junction
w0 = a0[300:500].astype(np.float32)
w1 = a10[300:500].astype(np.float32)
bestw = min(range(-40, 41), key=lambda d: np.abs(np.roll(w0, d, axis=1) - w1).mean())
print("wall pattern shift yaw0->10 (px):", bestw)

# floor at yaw 0 vs yaw 360
a360 = render(360.0).astype(np.uint8)
print("yaw0 == yaw360:", bool((a0 == a360).all()))

# save a few stills for user
for yaw, tag in [(0,"yaw0"), (90,"yaw90"), (180,"yaw180")]:
    im = Image.fromarray(render(yaw).astype(np.uint8))
    im.save(r"C:/Users/admin/.codex/visualizations/2026/08/12/019ff64c-eedd-7723-a592-58d6beff830f/floor_%s.png" % tag)
print("stills saved")
