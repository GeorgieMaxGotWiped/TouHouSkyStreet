# -*- coding: utf-8 -*-
# 临时脚本：整面扫一遍，找六面道中「同屏敌弹」的峰值时刻
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
peak, peak_t, t = 0, 0, 0
HI = int(sys.argv[1]) if len(sys.argv) > 1 else 105 * 60
while t <= HI:
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
    n = len(bm.enemy_bullets)
    if n > peak:
        peak, peak_t = n, t
    t += 1
print("道中同屏敌弹峰值 = %d 发 @ %.2fs" % (peak, peak_t / 60.0))
