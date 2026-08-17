# -*- coding: utf-8 -*-
"""验证终仪期间 Kaeman 全程不动。"""
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.entities.bullet import BulletManager
from src.stages.stage6 import Stage6_FinalApproach

pygame.init()
pygame.display.set_mode((960, 720))
stage = Stage6_FinalApproach()
stage.setup_boss()
boss = stage.boss
stage.phase = "boss"
bm = BulletManager()
boss.current_spell_idx = len(boss.spell_cards)
boss.arm_combat(0)
boss.entering = False
boss.entry_timer = 0
boss._start_spell(boss.last_spell)

# 等开符站稳后再记录位置
for _ in range(240):
    bm.update(1.0 / 60.0, 288.0, 560.0)
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
x0, y0 = boss.x, boss.y
print("start pos: %.2f, %.2f phase=%s" % (x0, y0, boss.kaeman_slumber["phase"]))
pos = set()
for _ in range(60 * 25):
    bm.update(1.0 / 60.0, 288.0, 560.0)
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    pos.add((round(boss.x, 3), round(boss.y, 3)))
print("distinct positions over 25s:", len(pos))
assert len(pos) == 1, "boss should not move during the spell"
print("FROZEN_OK")
