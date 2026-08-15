# -*- coding: utf-8 -*-
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, r"D:\pyz\my thingses\TouHou")
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
from src.engine.spell_bg import SpellBackground
sb = SpellBackground("球符「Balloon Barrage」")
print("style:", sb.style)
print("panoramas:", [(p is not None) and getattr(p, "_floor_src", None) is not None for p in sb.panoramas])
pan = sb.panoramas[0]
print("floor enabled:", pan._floor_src is not None, "| floor_y0=%d h=%d | depth_repeat default used" % (pan.floor_y0, pan.floor_h))
# render one frame through the real path
pan.yaw = 0.0
f = pan._build_frame()
print("frame:", f.get_size())
