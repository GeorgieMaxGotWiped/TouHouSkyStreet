# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
pygame.init(); pygame.display.set_mode((960, 720))
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
marks = {29 * 60: "29s Guard Wall", 34 * 60: "34s Last March", 100 * 60: "100s Final Defense"}
t = 0
while stage.timer < 110 * 60:
    stage.update(1 / 60.0, bm, 288.0, 560.0)
    bm.update(1 / 60.0, 288.0, 560.0)
    t += 1
    if t in marks:
        live = [e for e in stage.enemy_manager.get_active_enemies() if e.alive]
        comp = {}
        for e in live:
            comp[type(e).__name__] = comp.get(type(e).__name__, 0) + 1
        print("%-18s 在场 %2d 只  同屏敌弹 %3d 发  %s"
              % (marks[t], len(live),
                 len([b for b in bm.enemy_bullets if b.alive]), comp))
print("PROBE_OK")
