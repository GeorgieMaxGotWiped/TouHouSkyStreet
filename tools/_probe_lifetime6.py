# -*- coding: utf-8 -*-
# 临时脚本：量六面道中各小怪的实际在场时间（从生成到离场/被击破，空场无自机输出）
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

pygame.init(); pygame.display.set_mode((320, 240))
stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
first, last = {}, {}
t = 0
HI = 110 * 60
while t <= HI:
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
    for e in stage.enemy_manager.active_enemies:
        k = id(e)
        if e.alive:
            if k not in first:
                first[k] = (type(e).__name__, t, e.y)
            last[k] = t
    t += 1

by_class = {}
for k, (name, birth, y0) in first.items():
    by_class.setdefault(name, []).append(((last[k] - birth) + 1) / 60.0)
print("（空场，敌机不被击破，只看「自然离场」用时）")
for name in sorted(by_class):
    vals = sorted(by_class[name])
    print("%-26s n=%-3d 在场时间 %.1f~%.1fs（中位 %.1f）" % (
        name, len(vals), vals[0], vals[-1], vals[len(vals) // 2]))
