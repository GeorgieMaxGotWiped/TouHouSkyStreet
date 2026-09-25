# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
pygame.init(); pygame.display.set_mode((64, 64))
from src.entities import bullet_atlas as ba
for name, col in [("yellow(225,190,30)", (225, 190, 30)),
                  ("amber(230,170,20)", (230, 170, 20)),
                  ("green(60,205,70)", (60, 205, 70)),
                  ("green2(40,190,60)", (40, 190, 60)),
                  ("purple(178,128,236)", (178, 128, 236))]:
    slot = ba.pick_color_slot("g01_00", col)
    print("%-22s -> %s  sig=%s" % (name, slot, ba._slot_color_signature(slot)))
print("--- row g01 signatures ---")
for i in range(16):
    s = "g01_%02d" % i
    print("  %s %s" % (s, ba._slot_color_signature(s)))
