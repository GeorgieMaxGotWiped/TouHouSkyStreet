# -*- coding: utf-8 -*-
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, r"D:\pyz\my thingses\TouHou")
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
from src.engine.panorama3d import CylinderPanorama
from PIL import Image
import numpy as np
W, H = 576, 670
pan = CylinderPanorama(r"D:\pyz\my thingses\TouHou\assets\backgrounds\stage3\bg1.png", W, H,
                       fov=60.0, speed=28.0,
                       floor_texture_path=r"D:\pyz\my thingses\TouHou\assets\backgrounds\stage3\bossfloor1.png",
                       floor_depth_repeat=3.0)
OUT = r"C:/Users/admin/.codex/visualizations/2026/08/12/019ff64c-eedd-7723-a592-58d6beff830f"
frames = []
for i in range(36):
    pan.yaw = (i * 10.0) % 360.0
    f = pan._build_frame()
    frames.append(Image.fromarray(pygame.surfarray.array3d(f).astype(np.uint8)))
frames[0].save(OUT + "/real_floor_spin.gif", save_all=True, append_images=frames[1:], duration=60, loop=0)
print("gif saved:", OUT + "/real_floor_spin.gif")
