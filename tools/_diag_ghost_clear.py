# -*- coding: utf-8 -*-
import os, sys, math
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

pygame.init(); pygame.display.set_mode((320, 240))
stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
while stage.timer < 86 * 60 - 3:
    stage.update(1 / 60.0, bm, 288.0, 560.0); bm.update(1 / 60.0, 288.0, 560.0)
sx, sy = s6.GHOST_POSITIONS["storm"]
R = s6.GHOST_CLEAR_RADIUS
before = [b for b in bm.enemy_bullets if math.hypot(b.x - sx, b.y - sy) <= R]
print("离场前半径内 %d 发：harmless %d / cancel>0 %d / alive %d"
      % (len(before), sum(b.harmless for b in before),
         sum(b.cancel_timer > 0 for b in before), sum(b.alive for b in before)))
for _ in range(12):
    stage.update(1 / 60.0, bm, 288.0, 560.0); bm.update(1 / 60.0, 288.0, 560.0)
miss = [b for b in before
        if b.cancel_timer <= 0 and math.hypot(b.x - sx, b.y - sy) <= R]
print("没被清的 %d 发：" % len(miss))
for b in miss[:12]:
    print("   harmless=%s cancel=%d alive=%d type=%s r=%.0f dist=%.0f"
          % (b.harmless, b.cancel_timer, b.alive, b.bullet_type,
             b.collision_radius, math.hypot(b.x - sx, b.y - sy)))
