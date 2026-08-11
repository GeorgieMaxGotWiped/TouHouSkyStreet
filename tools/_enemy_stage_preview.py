# -*- coding: utf-8 -*-
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import sys
sys.path.insert(0, os.getcwd())
from src.engine import settings as cfg
from src.entities.enemy import EnemyWave, FairyEnemy, SpiritEnemy, GuardEnemy
from src.stages.stage1 import Stage1_SkyblockHub

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))

stage = Stage1_SkyblockHub()

def make_enemies(age):
    fairies = [FairyEnemy(120, 200), FairyEnemy(cfg.BATTLE_AREA_WIDTH - 120, 240)]
    spirits = [SpiritEnemy(200, 160), SpiritEnemy(cfg.BATTLE_AREA_WIDTH - 200, 320)]
    guards = [GuardEnemy(cfg.BATTLE_AREA_WIDTH / 2, 150)]
    en = fairies + spirits + guards
    for e in en:
        e.entry_done = True
        e.age = age
        e.shoot_timer = 99999
    fairies[0].hp = 15
    spirits[0].hp = 40
    guards[0].hp = 120
    return en

def render(age, out):
    wave = EnemyWave(make_enemies(age), name="Preview")
    wave.spawned = True
    stage.enemy_manager.timed_waves = [(0, wave)]
    stage.enemy_manager.waves = []
    stage.timer = 0
    stage.phase = "intro"
    stage.enemy_manager.update(1, None, 0, 0, stage_time=1)
    stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    pygame.image.save(screen, out)
    print("saved", out)

render(0, "_enemy_stage_preview_a.png")
render(20, "_enemy_stage_preview_b.png")
print("ok")
