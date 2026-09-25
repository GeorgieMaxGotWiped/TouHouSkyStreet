# -*- coding: utf-8 -*-
"""打印立绘顶部 45% 的逐行墨迹范围（原图像素），用来看「头」到底在哪一列。"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.getcwd())
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import pygame
from src.engine import boss_art, settings as cfg
if len(sys.argv) > 1:
    cfg.set_boss_art(sys.argv[1])
import _portrait_harmony_check as check

pygame.init()
pygame.display.set_mode((16, 16))

targets = {
    "wither_king(Kaeman)": "wither_king",
    "arachne": "arachne",
    "sadan": "sadan",
    "bonzo": "bonzo",
    "necron": "necron",
    "watcher": "watcher",
    "ender_dragon": "ender_dragon",
}
for label, key in targets.items():
    path = cfg.boss_art_path(key)
    img = boss_art.load_sprite(path)
    w, h = img.get_size()
    mask = pygame.mask.from_surface(img)
    rects = mask.get_bounding_rects()
    cr = rects[0]
    for r in rects[1:]:
        cr = cr.union(r)
    ratio = cfg.dialogue_portrait_head_ratio(path)
    print("\n%s  贴图 %dx%d  内容 %dx%d @ (%d,%d)  头占比 %s" % (
        label, w, h, cr.width, cr.height, cr.left, cr.top, ratio))
    step = max(1, cr.height // 18)
    for y in range(cr.top, cr.top + int(cr.height * 0.45), step):
        cols = [x for x in range(cr.left, cr.left + cr.width) if mask.get_at((x, y))]
        if not cols:
            print("   y=%4d (%.2f)  空" % (y, (y - cr.top) / cr.height))
            continue
        print("   y=%4d (%.2f)  x %4d..%4d  宽%4d  中心 %4d (占内容宽 %.2f)" % (
            y, (y - cr.top) / cr.height, min(cols), max(cols), max(cols) - min(cols) + 1,
            (min(cols) + max(cols)) // 2, ((min(cols) + max(cols)) / 2 - cr.left) / cr.width))
pygame.quit()
