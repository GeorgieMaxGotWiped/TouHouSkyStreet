# -*- coding: utf-8 -*-
"""冥符「Five Corrupted Relics」预览：驱动 Kaeman 第二符卡并渲染若干帧。"""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.entities.bullet import BulletManager
from src.engine.spell_bg import SpellBackground
from src.stages.stage6 import Stage6_FinalApproach, spell_kaeman_relics

OUT = os.path.join(os.getcwd(), "previews", "kaeman_relics")
os.makedirs(OUT, exist_ok=True)
pygame.init()
screen = pygame.display.set_mode((960, 720))

stage = Stage6_FinalApproach()
stage.setup_boss()
boss = stage.boss
stage.phase = "boss"
boss.phase = "spell"
boss.combat_enabled = True
boss.x = boss.target_x = 288.0
boss.y = boss.target_y = 112.0
boss.spell_bg = SpellBackground("冥符「Five Corrupted Relics」", "kaeman_relics")
bm = BulletManager()
px, py = 288.0, 560.0

targets = [90, 300, 600, 1200, 1800]
t = 0
for target in targets:
    while t < target:
        t += 1
        spell_kaeman_relics(boss, bm, t, 1.0 / 60, px, py)
        bm.update(1.0 / 60, px, py)
        boss.spell_bg.update(1.0 / 60)
    screen.fill((0, 0, 0))
    stage.draw(screen, 50, 25)
    bm.draw(screen, 50, 25)
    stage.draw_foreground(screen, 50, 25)
    path = os.path.join(OUT, "relics_t%04d.png" % t)
    pygame.image.save(screen, path)
    print("saved", path, "bullets", len(bm.enemy_bullets))
print("RENDER_OK")
