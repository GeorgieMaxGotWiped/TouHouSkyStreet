# -*- coding: utf-8 -*-
import os, sys, time
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, r"D:\pyz\my thingses\TouHou")
import numpy as np, pygame
pygame.init()
pygame.display.set_mode((8, 8))
from src.engine.panorama3d import CylinderPanorama

W, H = 576, 670
BG = r"D:\pyz\my thingses\TouHou\assets\backgrounds\stage3\bg1.png"
FL = r"D:\pyz\my thingses\TouHou\assets\backgrounds\stage3\bossfloor1.png"
OUT = r"C:/Users/admin/.codex/visualizations/2026/08/12/019ff64c-eedd-7723-a592-58d6beff830f"

pan = CylinderPanorama(BG, W, H, fov=60.0, speed=28.0,
                       floor_texture_path=FL, floor_depth_repeat=3.0)
print("floor enabled:", pan._floor_src is not None, "| floor_y0=%d h=%d" % (pan.floor_y0, pan.floor_h))

def grab(pan, yaw):
    pan.yaw = yaw % 360.0
    frame = pan._build_frame()
    return pygame.surfarray.array3d(frame)

a0 = grab(pan, 0.0)
a360 = grab(pan, 360.0)
print("seamless yaw0==yaw360:", bool(np.array_equal(a0, a360)))
a90 = grab(pan, 90.0)
pygame.image.save(pygame.surfarray.make_surface(a0), OUT + "/real_floor_yaw0.png")
pygame.image.save(pygame.surfarray.make_surface(a90), OUT + "/real_floor_yaw90.png")

# floor top edge vs wall junction: per-group y0 vs wall col_y0+jv*col_h
jv = pan._floor_y0  # group y0
gx = pan._floor_gx
wall_y0 = pan._col_y0[gx] + pan.floor_y0 / pan.h * 0  # placeholder
# recompute junction curve from stored values: junction v = (floor_y0 - col_y0)/col_h at center col
c = W // 2
jv_center = (pan.floor_y0 - pan._col_y0[c]) / float(pan._col_h[c])
junc = pan._col_y0 + jv_center * pan._col_h
err = np.abs(pan._floor_y0.astype(np.float64) - junc[pan._floor_gx])
print("junction v(center)=%.4f | floor-top-vs-wall max err=%s px (mean %.3f)" % (jv_center, err.max(), err.mean()))
print("center y0=%d edge y0=%d | col_step=%d groups=%d" % (pan.floor_y0, pan._floor_y0[0], pan.col_step, pan._floor_ns))

# per-frame timing (build_frame full: wall + floor + blits)
pan.yaw = 0.0
for _ in range(10): pan._build_frame()
t0 = time.perf_counter()
for i in range(60):
    pan.yaw = (i * 7.0) % 360.0
    pan._build_frame()
dt = (time.perf_counter() - t0) / 60 * 1000
print("full frame (wall+floor+blit): %.2f ms/frame" % dt)
