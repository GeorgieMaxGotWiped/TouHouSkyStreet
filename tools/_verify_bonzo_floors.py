# -*- coding: utf-8 -*-
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, r"D:\pyz\my thingses\TouHou")
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
from src.engine.spell_bg import SpellBackground
cards = [
    ("唤符「Undead Legion」", "undead"),
    ("骸符「Skull Dreadlord」", "undead"),
    ("球符「Balloon Barrage」", "bonzo"),
]
for name, style in cards:
    sb = SpellBackground(name, bg_style=style)
    pan = sb.panoramas[0]
    ok = pan is not None and pan._floor_src is not None
    f = pan._build_frame() if pan else None
    print("%-28s style=%-8s floor=%-5s frame=%s" % (name, sb.style, ok, f.get_size() if f else None))
