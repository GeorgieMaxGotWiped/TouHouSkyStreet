# -*- coding: utf-8 -*-
# 临时脚本：量测 Skeleton Lord 波（首波）弹幕密度
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
rows = []
t = 0
HI = 14 * 60
while t <= HI:
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
    if t % 60 == 0 and t >= 2 * 60:
        lords = [e for e in stage.enemy_manager.active_enemies if isinstance(e, s6.SkeletonLordEnemy) and e.alive]
        rows.append((t / 60.0, len(bm.enemy_bullets), len([e for e in stage.enemy_manager.active_enemies if e.alive]), len(lords)))
    t += 1
for sec, nb, ne, nl in rows:
    print("  %5.1fs  bullets=%-4d enemies=%-3d lords=%d" % (sec, nb, ne, nl))
peak = max(r[1] for r in rows)
print("peak in 2~14s = %d" % peak)
