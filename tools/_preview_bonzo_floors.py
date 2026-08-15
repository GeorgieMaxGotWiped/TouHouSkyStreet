# -*- coding: utf-8 -*-
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, r"D:\pyz\my thingses\TouHou")
import pygame, numpy as np
pygame.init(); pygame.display.set_mode((8, 8))
from src.engine.spell_bg import SpellBackground
OUT = r"C:/Users/admin/.codex/visualizations/2026/08/12/019ff64c-eedd-7723-a592-58d6beff830f"
for name, style, tag in [("唤符「Undead Legion」", "undead", "undead"), ("球符「Balloon Barrage」", "bonzo", "bonzo")]:
    sb = SpellBackground(name, bg_style=style)
    sb.alpha = 1.0
    f = sb.panoramas[0]._build_frame()
    pygame.image.save(pygame.surfarray.make_surface(pygame.surfarray.array3d(f)), "%s/bonzo_floor_%s.png" % (OUT, tag))
    print("saved", tag)
