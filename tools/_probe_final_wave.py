# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
pygame.init(); pygame.display.set_mode((960, 720))
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

def clear_early_lords(stage):
    if stage.timer >= 95 * 60:
        return
    for e in stage.enemy_manager.get_active_enemies():
        if isinstance(e, s6.SkeletonLordEnemy):
            while e.alive:
                e.take_damage(9999)

for label, kill in (("开场两位 Lord 不算（实战）", True), ("空场全留", False)):
    stage = s6.Stage6_FinalApproach(); stage.setup_waves()
    bm = BulletManager()
    peak_n, peak_t, peak_b, comp = 0, 0, 0, {}
    bmax, bmax_t = 0, 0.0
    t = 0
    while stage.timer < 108 * 60:
        if kill:
            clear_early_lords(stage)
        stage.update(1 / 60.0, bm, 288.0, 560.0)
        bm.update(1 / 60.0, 288.0, 560.0)
        t += 1
        live = [e for e in stage.enemy_manager.get_active_enemies() if e.alive]
        alive_b = len([b for b in bm.enemy_bullets if b.alive])
        if t >= 100 * 60:
            if len(live) > peak_n:
                peak_n, peak_t, peak_b = len(live), t, alive_b
                comp = {}
                for e in live:
                    comp[type(e).__name__] = comp.get(type(e).__name__, 0) + 1
            if alive_b > bmax:
                bmax, bmax_t = alive_b, t
    print("[%s] 峰值 %d 只 @%.2fs（同屏敌弹 %d 发）；100s 后同屏敌弹峰值 %d 发 @%.2fs"
          % (label, peak_n, peak_t / 60.0, peak_b, bmax, bmax_t / 60.0))
    print("   编成", comp, " 108s 在场 %d 只"
          % len([e for e in stage.enemy_manager.get_active_enemies() if e.alive]))
print("PROBE_OK")
