# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.entities.bullet import BulletManager
from src.stages.stage6 import Stage6_FinalApproach

OUT = r"C:\Users\admin\.codex\visualizations\2026\08\15\01a00596-d2da-7e22-af7a-2ba30a0704d6"
os.makedirs(OUT, exist_ok=True)
pygame.init()
screen = pygame.display.set_mode((960, 720))

def shot(stage, bm, path):
    screen.fill((0, 0, 0))
    stage.draw(screen, 50, 25)
    bm.draw(screen, 50, 25)
    stage.draw_foreground(screen, 50, 25)
    pygame.image.save(screen, path)
    print("saved", path)

stage = Stage6_FinalApproach()
stage.setup_waves()
bm = BulletManager()
px, py = 288.0, 560.0

def run_to(target, label):
    while stage.timer < target:
        stage.update(1.0 / 60.0, bm, px, py)
        bm.update(1.0 / 60.0, px, py)
    shot(stage, bm, os.path.join(OUT, label + ".png"))

run_to(22 * 60, "s6_march_22s")
run_to(52 * 60, "s6_interference_52s")
run_to(71 * 60, "s6_fortress_71s")
run_to(104 * 60, "s6_finalwave_104s")

# 跳过剩余敌人，进入 Wither King 战并渲染
for e in stage.enemy_manager.get_active_enemies():
    while e.alive:
        e.take_damage(9999)
run_to(104 * 60 + 3, "s6_dialogue")
stage.on_dialogue_end()
run_to(106 * 60, "s6_boss")
run_to(112 * 60, "s6_boss_6s")
print("RENDER_OK")
