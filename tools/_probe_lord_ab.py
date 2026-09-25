# -*- coding: utf-8 -*-
# 临时脚本：Skeleton Lord 改动前后的同屏敌弹 A/B（把常量改回旧值再扫一遍整面）
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

pygame.init(); pygame.display.set_mode((320, 240))
L = s6.SkeletonLordEnemy


def scan(hi=105 * 60):
    stage = s6.Stage6_FinalApproach(); stage.setup_waves()
    bm = BulletManager()
    peak, peak_t, lord_peak, lord_peak_t = 0, 0, 0, 0
    t = 0
    while t <= hi:
        stage.update(1.0 / 60.0, bm, 288.0, 560.0)
        bm.update(1.0 / 60.0, 288.0, 560.0)
        n = len(bm.enemy_bullets)
        if 300 <= t <= 900:   # 首波附近的稳态
            lord = len([b for b in bm.enemy_bullets if b.bullet_type == "scale"])
            if lord > lord_peak:
                lord_peak, lord_peak_t = lord, t
        if n > peak:
            peak, peak_t = n, t
        t += 1
    return peak, peak_t / 60.0, lord_peak, lord_peak_t / 60.0


now = scan()
L.VOLLEY_FRAMES, L.SPIN_STEP = 12, 0.55
before = scan()
print("改动前：整面同屏敌弹峰值 %d @ %.2fs；首波 5~15s 鳞弹稳态峰值 %d @ %.2fs" % (
    before[0], before[1], before[2], before[3]))
print("改动后：整面同屏敌弹峰值 %d @ %.2fs；首波 5~15s 鳞弹稳态峰值 %d @ %.2fs" % (
    now[0], now[1], now[2], now[3]))
