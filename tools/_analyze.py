
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import numpy as np
sys.path.insert(0, os.getcwd())
from src.engine.spell_bg import SpellBackground, EFFECT_CENTER

pygame.init()
screen = pygame.display.set_mode((576, 670))

for style in ("spool", "thread", "tornado", "soul"):
    bg = SpellBackground("test", bg_style=style)
    for i in range(100):
        bg.update(1/60)
        bg.draw(screen)
    arr = pygame.surfarray.array3d(screen).astype(np.float32)  # (w,h,3)
    cx, cy = int(EFFECT_CENTER[0]), int(EFFECT_CENTER[1])
    # 中心图标区域（比图标大一圈的方框）
    reg = arr[cx-110:cx+110, cy-110:cy+110]
    lum = reg.mean(axis=2)
    bright = lum > 70
    if bright.sum() > 50:
        cols = reg[bright]
        med = np.median(cols, axis=0)
        # 去重统计最亮簇
        print("%-8s center_region bright%%=%.1f median_rgb=(%d,%d,%d)  full_mean=%.1f" % (
            style, 100*bright.mean(), med[0], med[1], med[2], arr.mean()))
    else:
        print("%-8s center_region bright%%=%.1f (icon weak?)  full_mean=%.1f" % (
            style, 100*bright.mean(), arr.mean()))
pygame.quit()
